"""Sends multiple requests to HiSim and collects all results."""

from typing import List, Union

from utspclient.client import calculate_multiple_requests
from utspclient.datastructures import ResultDelivery, TimeSeriesRequest

# Define UTSP connection parameters
URL = "134.94.131.167:443"
API_KEY = ""


def calculate_multiple_hisim_requests(
    hisim_configs: List[str],
    raise_exceptions: bool = False,
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
    results = calculate_multiple_requests(URL, all_requests, API_KEY, raise_exceptions)
    return results
