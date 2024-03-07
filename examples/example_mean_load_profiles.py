"""
This example shows how to send multiple long requests to the UTSP. At first, the example finishes without collecting results.
After all requests have been calculated, the example can be run again to collect the results and calculate average profiles
from them.
This avoids having to keep the example running during the lenghty calculations of the requests.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd
from utspclient import datastructures
from utspclient.helpers import lpg_helper
from utspclient import result_file_filters
from utspclient.client import get_result, send_request
from utspclient.datastructures import (
    CalculationStatus,
    ResultDelivery,
    TimeSeriesRequest,
)
from utspclient.helpers.lpgdata import HouseTypes
from utspclient.helpers.lpgpythonbindings import EnergyIntensityType
from utspclient.helpers.lpgpythonbindings import CalcOption

API_KEY = ""

# TODO: this example works with specifying different endpoints; this does not work anymore


def get_hh_id(hh_name: str) -> str:
    """helper function to get the ID of a household (e.g. CHR01) from its full name"""
    return hh_name.split("_")[0]


def request_all_profiles(
    server_address: str, households, repetitions_per_household: int, retrieve_data: bool
) -> Tuple[bool, Dict[str, Dict[str, ResultDelivery]]]:
    base_url = f"http://{server_address}/api/v1/"
    new_request_url = base_url + "profilerequest"
    status_url = base_url + "requeststatus"
    request_statuses = {}
    results: Dict[str, Dict[str, ResultDelivery]] = {}
    new_requests = 0
    start_time = time.time()
    for hh_name, hh_ref in households.items():
        hh_id = get_hh_id(hh_name)

        # create the request for this household
        lpg_request = lpg_helper.create_basic_lpg_config(
            hh_ref,
            HouseTypes.HT06_Normal_house_with_15_000_kWh_Heating_Continuous_Flow_Gas_Heating,
            "2021-01-04",
            "2022-01-09",
            "01:00:00",
            energy_intensity=EnergyIntensityType.EnergySaving,
            calc_options=[CalcOption.SumProfileExternalIndividualHouseholdsAsJson],
        )
        lpg_request_str = lpg_request.to_json()  # type: ignore

        # create multiple identical request for each household with different guids
        results[hh_name] = {}
        for i in range(repetitions_per_household):
            # check time and print a progress report
            if time.time() - start_time > 10:
                start_time = time.time()
                print(f"Sending requests for household {hh_id}, repetition {i}")
            guid = str(i)
            request = TimeSeriesRequest(
                lpg_request_str,
                "lpg",
                guid,
                {
                    result_file_filters.LPGFilters.sum_hh1_ext_res(
                        "Electricity", 3600, True
                    ): datastructures.ResultFileRequirement.REQUIRED
                },
            )
            url = new_request_url if retrieve_data else status_url
            # check the status of this request
            reply = send_request(url, request, API_KEY)
            if reply.status == CalculationStatus.UNKNOWN:
                # The request was not sent before, so it is sent now. Only when a request
                # is sent to this url it can be added to the calculation queue
                reply = send_request(new_request_url, request, API_KEY)
                assert reply.status == CalculationStatus.CALCULATIONSTARTED
                new_requests += 1

            # check if the request calculation failed
            request_statuses[(hh_id, guid)] = reply.status
            if reply.status == CalculationStatus.CALCULATIONFAILED:
                print(
                    f"{hh_id}, {guid} failed: {reply.info}",
                )
            # retrieve the result data
            if reply.status == CalculationStatus.INDATABASE and reply.result_delivery:
                result = get_result(reply)
                assert result is not None, "Delivered time series was None"
                results[hh_name][guid] = result

    # calculate the number of completed and failed requests
    completed_requests = sum(
        1
        for _, status in request_statuses.items()
        if status == CalculationStatus.INDATABASE
    )
    failed_requests = sum(
        1
        for _, status in request_statuses.items()
        if status == CalculationStatus.CALCULATIONFAILED
    )
    if not retrieve_data:
        # print an overview of the request statuses
        print(f"Sent {new_requests or 'no'} new requests.")
        print(
            f"Completion: {100 * completed_requests // len(request_statuses)} %  ({completed_requests} of {len(request_statuses)})"
        )
        print(f"Failed requests: {failed_requests} of {len(request_statuses)}")
    # determine whether all requests have been calculated already
    all_finished = completed_requests == len(request_statuses)
    return all_finished, results


def calc_and_save_mean_series(
    results: Dict[str, Dict[str, ResultDelivery]], result_file: str
):
    # take unit, start date and resolution from the first time series
    first_result = list(list(results.values())[0].values())[0]
    file_content = first_result.data[
        result_file_filters.LPGFilters.sum_hh1_ext_res("Electricity", 3600, True)
    ].decode()
    first_ts = json.loads(file_content)
    assert isinstance(first_ts, list), "Unexpected json format"
    start = datetime(2021, 1, 4)
    resolution = timedelta(hours=1)
    length = len(first_ts)
    unit = "kWh"
    # calculate the mean profiles
    means = {}
    for hh_name, results_of_one_hh in results.items():
        mean_series = mean_time_series(results_of_one_hh.values())
        means[hh_name + f" [{unit}]"] = mean_series
    index = pd.date_range(name="Time", start=start, freq=resolution, periods=length)  # type: ignore
    data = pd.DataFrame(means, index=index)
    data.to_csv(result_file)
    print(f"Saved mean time series to '{result_file}'")


def mean_time_series(results: Iterable[ResultDelivery]):
    values = []
    for result in results:
        file_content = result.data[
            result_file_filters.LPGFilters.sum_hh1_ext_res("Electricity", 3600, True)
        ].decode()
        ts = json.loads(file_content)
        values.append(ts)
    return np.mean(values, axis=0)  # type: ignore


def main():
    """
    This function is meant to be run multiple times manually.
    It requests multiple electricity load profiles for all predefined lpg households to ultimately calculate a mean profile
    for each household.
    The function checks if all results have been created by the UTSP already, and only then retrieves the result data and
    calculates the mean profiles.
    """
    server_address = "134.94.131.167:443"
    repetitions_per_household = 100
    households = lpg_helper.collect_lpg_households()

    # to reduce the number of households for testing
    # households = {k: v for i, (k, v) in enumerate(households.items()) if i < 2}

    print(
        f"Requesting {repetitions_per_household} profiles from {len(households)} households. Starting at {datetime.now()}"
    )
    # at first check request statuses without retrieving data to save time and network traffic
    all_finished, _ = request_all_profiles(
        server_address, households, repetitions_per_household, False
    )
    if all_finished:
        print("All calculations are finished - retrieving time series data")
        _, time_series = request_all_profiles(
            server_address, households, repetitions_per_household, True
        )
        calc_and_save_mean_series(time_series, "./lpg_mean_profiles_electricity.csv")


if __name__ == "__main__":
    main()
