"""Sends multiple requests to HiSim and collects all results."""

from typing import List, Union

import tqdm

from utspclient.client import request_time_series_and_wait_for_delivery, send_request
from utspclient.datastructures import ResultDelivery, TimeSeriesRequest

# Define UTSP connection parameters
URL = "http://134.94.131.167:443/api/v1/profilerequest"
API_KEY = ""


def calculate_multiple_hisim_requests(
    hisim_configs: List[str],
    return_exceptions: bool = False,
    result_files=None,
) -> List[Union[ResultDelivery, Exception]]:
    """
    Sends multiple hisim requests for parallel calculation and collects
    their results.

    :param hisim_configs: the hisim configurations to calculate
    :type hisim_configs: List[str]
    :param return_exceptions: whether exceptions should be caught and returned in the result list, defaults to False
    :type return_exceptions: bool, optional
    :return: a list containing the content of the result KPI file for each request
    :rtype: List[str]
    """
    # Create all request objects
    all_requests = [
        TimeSeriesRequest(
            config,
            "hisim",
            required_result_files=result_files or {},
        )
        for config in hisim_configs
    ]

    print(f"Sending {len(all_requests)} requests")
    # Send all requests to the UTSP
    for request in tqdm.tqdm(all_requests):
        # This function just sends the request and immediately returns so the other requests don't have to wait
        send_request(URL, request, API_KEY)

    print("Collecting results.")
    # Collect the results
    results: List[Union[ResultDelivery, Exception]] = []
    for request in tqdm.tqdm(all_requests):
        try:
            # This function waits until the request has been processed and the results are available
            result = request_time_series_and_wait_for_delivery(
                URL, request, API_KEY, quiet=True
            )
            results.append(result)
        except Exception as e:
            if return_exceptions:
                # return the exception as result
                results.append(e)
            else:
                raise
    return results
