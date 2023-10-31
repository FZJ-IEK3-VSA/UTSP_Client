"""Requests a file containing KPIs generated from HiSim"""

import os
import time

from utspclient.client import request_time_series_and_wait_for_delivery
from utspclient.datastructures import TimeSeriesRequest


def main():
    # load a HiSim system configuration
    example_folder = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(example_folder, "input data\\scenario_config.json")
    with open(config_path, "r") as config_file:
        hisim_config = config_file.read()

    # Define URL to time Series request
    URL = "http://134.94.131.167:443/api/v1/profilerequest"
    API_KEY = ""

    # Save start time for run time calculation
    start_time = time.time()

    # Call time series request function
    result_file_name = "kpi_config.json"
    request = TimeSeriesRequest(
        hisim_config,
        "hisim",
        required_result_files=dict.fromkeys([result_file_name]),
    )
    result = request_time_series_and_wait_for_delivery(URL, request, API_KEY)

    kpi = result.data[result_file_name].decode()

    print("Calculation took %s seconds" % (time.time() - start_time))
    # Print all results from the request
    print("Example HiSim request")
    print(f"Retrieved data: {kpi}")


if __name__ == "__main__":
    main()
