"""Requests a load profile that is generated using the small and medium-sized
enterprise load profile generator (sme-lpg)"""

import base64
import os
import random
import string
import time

from utspclient.client import request_time_series_and_wait_for_delivery
from utspclient.datastructures import TimeSeriesRequest


def main():
    # load an enterprise definition for the sme-lpg
    example_folder = os.path.dirname(os.path.abspath(__file__))
    example_enterprise_path = os.path.join(
        example_folder, "input data\\smelpg_enterprise.json"
    )
    with open(example_enterprise_path, "r") as enterprise_file:
        enterprise_definition = enterprise_file.read()

    # load an additional input file
    input_file_path = os.path.join(example_folder, "input data\\smelpg_input.csv")
    with open(input_file_path, "rb") as input_file:
        input_file_data = input_file.read()
        # Workaround due to bug in dataclasses_json: store data as base64 encoded string
        input_file_str = base64.b64encode(input_file_data).decode()
    # Add the input file to a dict. This file is referenced in 'smelpg_enterprise.json', so
    # the same file name as in 'smelpg_enterprise.json' has to be used.
    input_files = {"input_data.csv": input_file_str}

    REQUEST_URL = "134.94.131.167:443"
    API_KEY = ""

    # Save start time for run time calculation
    start_time = time.time()

    # Create a random id to enforce recalculation for each request
    guid = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

    # Call time series request function

    request = TimeSeriesRequest(
        enterprise_definition,
        "smelpg",
        guid,
        input_files=input_files,
    )
    result = request_time_series_and_wait_for_delivery(REQUEST_URL, request, API_KEY)
    ts = result.data["results.csv"].decode()

    print("Calculation took %s seconds" % (time.time() - start_time))
    # Print all results from the request
    print("Example sme-lpg request")
    print(f"Retrieved data: {ts.split(os.linesep)[0]}")


if __name__ == "__main__":
    main()
