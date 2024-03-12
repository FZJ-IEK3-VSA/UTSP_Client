"""
Functions for sending calculation requests to the UTSP and retrieving results.
"""

from datetime import datetime
import time
from typing import Iterable, List, Optional, Sized, Union

import requests
import tqdm  # type: ignore
from utspclient.datastructures import (
    CalculationStatus,
    EncodedResultDelivery,
    RestReply,
    ResultDelivery,
    TimeSeriesRequest,
)

BASE_URL = "/api/v1/"
REQUEST_URL = BASE_URL + "profilerequest"
REQUEST_URL_NO_RESULTS = REQUEST_URL + "/noresult"
STATUS_URL = BASE_URL + "requeststatus"
UPLOAD_URL = BASE_URL + "buildimage"
SHUTDOWN_URL = BASE_URL + "shutdown"


def build_url(address: str, route: str) -> str:
    """
    Helper function to build a URL

    :param address: server address
    :param route: URL route
    :return: the full URL
    """
    if not address.startswith("http"):
        address = f"http://{address}"
    if "/" in address[len("http://") :]:
        # backwards compatibility: if the address contains a route, remove it
        address = address[:7] + address[len("http://") :].split("/")[0]
    return address + route


def decompress_result_data(result: EncodedResultDelivery) -> ResultDelivery:
    """
    Decodes and decompresses the result data returned from the UTSP.

    :param data: encoded and compressed result data
    :return: usable result data
    """
    decoded = result.decode_data()
    decoded.decompress_data()
    return decoded


def send_request(
    url: str, request: Union[str, TimeSeriesRequest], api_key: str = ""
) -> RestReply:
    """
    Sends the request to the utsp and returns the reply

    :param url: URL of the utsp server endpoint
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
    reply = RestReply.from_dict(response_dict)  # type: ignore
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
    return status in [
        CalculationStatus.INDATABASE,
        CalculationStatus.CALCULATIONFAILED,
    ]


def request_time_series_and_wait_for_delivery(
    address: str,
    request: Union[str, TimeSeriesRequest],
    api_key: str = "",
    quiet: bool = False,
    timeout: float = 10,
) -> ResultDelivery:
    """
    Requests a single time series from the UTSP server from the specified
    time series provider.

    :param address: address of the UTSP server
    :param request: The request object defining the requested time series
    :param api_key: API key for accessing the UTSP, defaults to ""
    :param quiet: whether no console outputs should be produced, defaults to False
    :param timeout: the time in seconds to wait between repeated requests to
                    check the calculation status
    :return: The requested result data
    """
    if isinstance(request, TimeSeriesRequest):
        request = request.to_json()  # type: ignore
    status = CalculationStatus.UNKNOWN
    if not quiet:
        print(f"Sending a request to the UTSP at {datetime.now()}")
        print("Waiting for the results. This might take a while.")
    url = build_url(address, REQUEST_URL)
    while True:
        reply = send_request(url, request, api_key)
        status = reply.status
        if is_finished(status):
            break
        time.sleep(timeout)

    result = get_result(reply)
    assert result is not None, "No result was delivered"
    return result


def calculate_multiple_requests(
    address: str,
    requests: Iterable[Union[str, TimeSeriesRequest]],
    api_key: str = "",
    raise_exceptions: bool = True,
    quiet: bool = False,
    timeout: float = 10,
) -> List[Union[ResultDelivery, Exception]]:
    """
    Sends multiple calculation requests to the UTSP and collects the results. The
    requests can be calculated in parallel.

    :param address: address of the UTSP server
    :param requests: The request objects to send
    :param api_key: API key for accessing the UTSP, defaults to ""
    :param raise_exceptions: if True, failed requests raise exceptions, otherwhise the
                             exception object is added to the result list; defaults to True
    :param quiet: whether no console outputs should be produced, defaults to False
    :param timeout: the time in seconds to wait between repeated requests to
                    check the calculation status
    :return: a list containing the requested result objects; if raise_exceptions was
             set to False, this list can also contain exceptions
    """
    request_iterable = requests
    if not quiet:
        if isinstance(requests, Sized):
            number = str(len(requests))
        else:
            number = "an unknown number of"
        print(f"Sending {number} requests")
        # add a progress bar
        request_iterable = tqdm.tqdm(requests)
    # Send all requests to the UTSP
    # Don't retrieve results yet to send all requests as fast as possible
    no_results_url = build_url(address, REQUEST_URL_NO_RESULTS)
    for request in request_iterable:
        # This function just sends the request and immediately returns so the other requests don't have to wait
        send_request(no_results_url, request, api_key)

    if not quiet:
        print("All requests sent. Starting to collect results.")
        # reset the progress bar
        request_iterable = tqdm.tqdm(requests)
    # Collect the results
    results_url = build_url(address, REQUEST_URL)
    results: List[Union[ResultDelivery, Exception]] = []
    error_count = 0
    for request in request_iterable:
        try:
            # This function waits until the request has been processed and the results are available
            result = request_time_series_and_wait_for_delivery(
                results_url, request, api_key, quiet=True, timeout=timeout
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


def upload_provider_build_context(
    address: str, api_key: str, path: str, versioned_name: str
):
    """
    Uploads an image build context for a provider.
    A build context is a .tar or .tar.gz file containing
    everything that is necessary for building the provider
    image. The image will then be built by the UTSP server.

    :param address: address of the UTSP server to add the provider to
    :param api_key: API key for accessing the UTSP server
    :param path: path of the build context file
    :param versioned_name: versioned name of the provider
    """
    assert (
        versioned_name.count("-") == 1
    ), f"Invalid provider name '{versioned_name}': must contain exactly one dash"
    files = {versioned_name: open(path, "rb")}
    print(f"Starting upload of {versioned_name}")
    url = build_url(address, UPLOAD_URL)
    reply = requests.post(url, files=files, headers={"Authorization": api_key})
    print(reply.text)


def shutdown(address: str, api_key: str = ""):
    """
    Shuts down all UTSP workers connected to the server.

    :param address: address of the UTSP server
    :type url: str
    :param api_key: API key for accessing the UTSP, defaults to ""
    :type api_key: str, optional
    """
    url = build_url(address, SHUTDOWN_URL)
    requests.post(url, headers={"Authorization": api_key})
