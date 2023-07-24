"""
Functions for sending calculation requests to the UTSP and retrieving results.
"""

from datetime import datetime
import time
from typing import Dict, Iterable, List, Optional, Set, Union
import zlib

import requests
from pandas import DataFrame
import tqdm  # type: ignore
from utspclient.datastructures import (
    CalculationStatus,
    RestReply,
    ResultDelivery,
    TimeSeriesRequest,
)


def decompress_result_data(data: bytes) -> ResultDelivery:
    """
    Decompresses the result data returned by the UTSP in the field result_delivery
    of RestReply objects.

    :param data: compressed result data
    :type data: bytes
    :return: decompressed result data
    :rtype: ResultDelivery
    """
    json_data = zlib.decompress(data).decode()
    return ResultDelivery.from_json(json_data)  # type: ignore


def send_request(
    url: str, request: Union[str, TimeSeriesRequest], api_key: str = ""
) -> RestReply:
    """
    Sends the request to the utsp and returns the reply

    :param url: URL of the utsp server
    :type url: str
    :param request: the request to send
    :type request: Union[str, TimeSeriesRequest]
    :param api_key: the api key to use, defaults to ""
    :type api_key: str, optional
    :raises Exception: if the server reported an error
    :return: the reply from the utsp server
    :rtype: RestReply
    """
    if isinstance(request, TimeSeriesRequest):
        request = request.to_json()  # type: ignore
    response = requests.post(url, json=request, headers={"Authorization": api_key})
    if not response.ok:
        raise Exception(f"Received error code: {str(response)}")
    response_dict = response.json()
    # don't use dataclasses_json here, it has bug regarding bytes
    reply = RestReply(**response_dict)  # type: ignore
    return reply


def get_result(reply: RestReply) -> Optional[ResultDelivery]:
    """
    Helper function for getting a time series out of a rest reply if it was delivered.
    Raises an exception if the calculation failed

    :param reply: the reply from the utsp server to check for a time series
    :type reply: RestReply
    :raises Exception: if the calculation failed
    :return: the delivered time series, or None
    :rtype: Optional[TimeSeriesDelivery]
    """
    status = reply.status
    # parse and return the time series if it was delivered
    if status == CalculationStatus.INDATABASE:
        return decompress_result_data(reply.result_delivery)  # type: ignore
    # if the time series is still in calculation, return None
    if status in [
        CalculationStatus.CALCULATIONSTARTED,
        CalculationStatus.INCALCULATION,
    ]:
        return None
    # the calculation failed: raise an error
    if status == CalculationStatus.CALCULATIONFAILED:
        raise Exception("Calculation failed: " + (reply.info or ""))
    raise Exception("Unknown status")


def is_finished(status: CalculationStatus) -> bool:
    """
    Checks whether the request with the specified status
    is finished (successful or failed) or whether it is
    still in calculation.

    :param status: the status of the request
    :type status: CalculationStatus
    :return: _description_
    :rtype: bool
    """
    return status not in [
        CalculationStatus.INDATABASE,
        CalculationStatus.CALCULATIONFAILED,
    ]


def request_time_series_and_wait_for_delivery(
    url: str,
    request: Union[str, TimeSeriesRequest],
    api_key: str = "",
    quiet: bool = False,
) -> ResultDelivery:
    """
    Requests a single time series from the UTSP server from the specified time series provider

    :param url: URL of the UTSP server
    :type url: str
    :param request: The request object defining the requested time series
    :type request: Union[str, TimeSeriesRequest]
    :param api_key: API key for accessing the UTSP, defaults to ""
    :type api_key: str, optional
    :param quiet: whether no console outputs should be produced, defaults to False
    :type quiet: bool, optional
    :return: The requested result data
    :rtype: ResultDelivery
    """
    if isinstance(request, TimeSeriesRequest):
        request = request.to_json()  # type: ignore
    status = CalculationStatus.UNKNOWN
    if not quiet:
        print(f"Sending a request to the UTSP at {datetime.now()}")
        print("Waiting for the results. This might take a while.")
    while True:
        reply = send_request(url, request, api_key)
        status = reply.status
        if is_finished(status):
            break
        time.sleep(1)

    ts = get_result(reply)
    assert ts is not None, "No time series was delivered"
    return ts


def calculate_multiple_requests(
    url: str,
    requests: Iterable[Union[str, TimeSeriesRequest]],
    api_key: str = "",
    raise_exceptions: bool = True,
    quiet: bool = False,
) -> List[Union[ResultDelivery, Exception]]:
    """
    Sends multiple calculation requests to the UTSP and collects the results. The
    requests can be calculated in parallel.

    :param url: URL of the UTSP server
    :type url: str
    :param requests: The request objects to send
    :type requests: Iterable[Union[str, TimeSeriesRequest]]
    :param api_key: API key for accessing the UTSP, defaults to ""
    :type api_key: str, optional
    :param raise_exceptions: if True, failed requests raise exceptions, otherwhise the
                             exception object is added to the result list; defaults to True
    :type raise_exceptions: bool, optional
    :param quiet: whether no console outputs should be produced, defaults to False
    :type quiet: bool, optional
    :return: a list containing the requested result objects; if raise_exceptions was
             set to False, this list can also contain exceptions
    :rtype: List[Union[ResultDelivery, Exception]]
    """
    request_iterable = requests
    if not quiet:
        print(f"Sending {len(requests)} requests")
        # add a progress bar
        request_iterable = tqdm.tqdm(requests)
    # Send all requests to the UTSP
    for request in request_iterable:
        # This function just sends the request and immediately returns so the other requests don't have to wait
        send_request(url, request, api_key)

    if not quiet:
        print("All requests sent. Starting to collect results.")
        # reset the progress bar
        request_iterable = tqdm.tqdm(requests)
    # Collect the results
    results: List[Union[ResultDelivery, Exception]] = []
    error_count = 0
    for request in request_iterable:
        try:
            # This function waits until the request has been processed and the results are available
            result = request_time_series_and_wait_for_delivery(
                url, request, api_key, quiet=True
            )
            results.append(result)
        except Exception as e:
            if raise_exceptions:
                raise
            else:
                # return the exception as result
                results.append(e)
                error_count += 1
    if not quiet:
        print(f"Retrieved all results. Number of failed requests: {error_count}")
    return results


def shutdown(url: str, api_key: str = ""):
    """
    Shuts down all UTSP workers connected to the server.

    :param url: URL of the UTSP server
    :type url: str
    :param api_key: API key for accessing the UTSP, defaults to ""
    :type api_key: str, optional
    """
    requests.post(url, headers={"Authorization": api_key})
