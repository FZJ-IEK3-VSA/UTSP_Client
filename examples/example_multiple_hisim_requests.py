"""Sends multiple requests to HiSim and collects all results."""

import os
from typing import List

from utspclient.client import request_time_series_and_wait_for_delivery, send_request
from utspclient.datastructures import CalculationStatus, TimeSeriesRequest

# load a HiSim system configuration
example_folder = os.path.dirname(os.path.abspath(__file__))
system_config_path = os.path.join(example_folder, "input data\\hisim_config.json")
with open(system_config_path, "r") as config_file:
    example_system_config = config_file.read()

# Define URL to time Series request
URL = "http://134.94.131.167:443/api/v1/profilerequest"
API_KEY = ""


# Define all hisim system configurations here (in this case 10 identical configs)
all_hisim_configs = [example_system_config] * 10

# Create all request objects
all_requests = [
    TimeSeriesRequest(
        config,
        "hisim",
        required_result_files=dict.fromkeys(["kpi_config.json"]),
    )
    for config in all_hisim_configs
]

# Send all requests to the UTSP
for request in all_requests:
    # This function just sends the request and immediately returns so the other requests don't have to wait
    reply = send_request(URL, request, API_KEY)

# Collect the results
results: List[str] = []
for request in all_requests:
    # This function waits until the request has been processed and the results are available
    result = request_time_series_and_wait_for_delivery(URL, request, API_KEY)
    assert (
        reply.status != CalculationStatus.CALCULATIONFAILED
    ), f"The calculation failed: {reply.info}"
    kpi = result.data["kpi_config.json"].decode()
    results.append(kpi)


print(f"Retrieved results from {len(results)} HiSim requests")
