"""Sends multiple requests to HiSim and collects all results."""

import json
import os
from typing import Dict, List, Optional

from utspclient.client import request_time_series_and_wait_for_delivery, send_request
from utspclient.datastructures import CalculationStatus, TimeSeriesRequest

from matplotlib import pyplot as plt


# Define UTSP connection parameters
URL = "http://134.94.131.167:443/api/v1/profilerequest"
API_KEY = ""


def calculate_multiple_hisim_requests(hisim_configs: List[str]) -> List[str]:
    """
    Sends multiple hisim requests for parallel calculation and collects
    their results.

    :param hisim_configs: the hisim configurations to calculate
    :type hisim_configs: List[str]
    :return: a list containing the content of the result KPI file for each request
    :rtype: List[str]
    """
    # Create all request objects
    all_requests = [
        TimeSeriesRequest(
            config,
            "hisim",
            required_result_files=dict.fromkeys(["kpi_config.json"]),
        )
        for config in hisim_configs
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
    return results


def plot_sensitivity(
    parameter_values: List,
    parameter_name: str,
    kpis: Dict[str, List[float]],
    base_scenario_index: Optional[int] = None,
):
    # determine the scenario which is used as base scenario for calculating value changes
    if base_scenario_index is None:
        # if not specified, use the value in the middle
        base_scenario_index = len(parameter_values) // 2 - 1

    # determine the norming factors for calculating the relative parameter/KPI values (in percent)
    norm_factor_parameter = parameter_values[base_scenario_index] / 100
    norm_factors_kpis = {
        name: values[base_scenario_index] / 100 for name, values in kpis.items()
    }

    # calculate the parameter and KPI values relative to the base scenario values
    parameter_values_relative = [
        value / norm_factor_parameter for value in parameter_values
    ]
    kpis_relative = {
        name: [val / norm_factors_kpis[name] for val in values]
        for name, values in kpis.items()
    }

    fig = plt.figure()
    ax: plt.Axes = fig.add_subplot(1, 1, 1)
    ax.set_xlabel(f"Relative {parameter_name} [%]")
    ax.set_ylabel("Relative KPI value [%]")
    for kpi_name, kpi_values in kpis_relative.items():
        ax.plot(parameter_values_relative, kpi_values, label=kpi_name, marker="x")
    ax.set_title("HiSim Sensitivity Analysis")

    ax.legend()
    plt.show()
    pass


def main():
    # load a HiSim system configuration
    example_folder = os.path.dirname(os.path.abspath(__file__))
    system_config_path = os.path.join(
        example_folder, "input data\\hisim_config_param.json"
    )
    with open(system_config_path, "r") as config_file:
        example_system_config = config_file.read()

    # Placeholder in the HiSim configuration to mark the parameter that should be varied
    TEMPLATE_PLACEHOLDER = "<<PARAMETER>>"
    assert (
        TEMPLATE_PLACEHOLDER in example_system_config
    ), f"'{TEMPLATE_PLACEHOLDER}' is missing in the config."

    # Define all hisim system configurations here
    # parameter_name = "pv peak power [500 - 15e3]"
    # parameter_values = [500, 1000, 2000, 4000, 6000, 8000, 10000, 15000]

    # parameter_name = "chp power [2-15]"
    # parameter_values = [2, 4, 6, 8, 10, 12, 15]

    # parameter_name = "battery capacity"
    # parameter_values = [0.5, 1.5, 4, 8, 10, 15, 20]

    parameter_name = "buffer_volume [500 - 4000]"
    parameter_values = [500, 600, 800, 1000, 1200, 1500, 1800, 2000, 2500, 3000, 4000]

    # parameter_values = ["false", "true"]

    # insert all values and thus create different HiSim configurations
    all_hisim_configs = [
        example_system_config.replace(TEMPLATE_PLACEHOLDER, str(v))
        for v in parameter_values
    ]

    # process all requests and retrieve the results
    results = calculate_multiple_hisim_requests(all_hisim_configs)
    print(f"Retrieved results from {len(results)} HiSim requests")

    # create lists of the relevant KPIs
    relevant_kpis = ["self_consumption_rate", "autarky_rate"]
    kpis = {}
    for result in results:
        # parse the results from a single request
        result_dict = json.loads(result)
        for key, value in result_dict.items():
            if key in relevant_kpis:
                if key not in kpis:
                    kpis[key] = []
                # add the kpi to the respective list
                kpis[key].append(value)

    # print parameter values and kpis
    print(f"parameter_values: {parameter_values}")
    for key, value in kpis.items():
        print(f"{key}: {value}")

    plot_sensitivity(parameter_values, parameter_name, kpis)


if __name__ == "__main__":
    main()
