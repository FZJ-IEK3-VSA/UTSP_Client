import json
import time
from typing import Dict, List, Optional, Set, Union
import zlib

import requests
from pandas import DataFrame  # type: ignore
from utspclient.datastructures import (
    CalculationStatus,
    RestReply,
    ResultDelivery,
    TimeSeriesRequest,
)


def decompress_result_data(data: bytes) -> ResultDelivery:
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
    Raises an exception when the calculation failed

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
        print("Waiting for the results. This might take a while.")
    while status not in [
        CalculationStatus.INDATABASE,
        CalculationStatus.CALCULATIONFAILED,
    ]:
        reply = send_request(url, request, api_key)
        status = reply.status
        if status != CalculationStatus.INDATABASE:
            time.sleep(1)
    ts = get_result(reply)
    assert ts is not None, "No time series was delivered"
    return ts
