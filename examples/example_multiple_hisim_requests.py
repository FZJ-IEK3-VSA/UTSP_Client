"""Sends multiple requests to HiSim and collects all results."""

import errno
import json
import os
from typing import Dict, List, Optional, Tuple
from examples.postprocessing.sensitivity_plots import (  # type: ignore
    load_hisim_config,
    read_base_config_values,
    SensitivityAnalysisCurve,
)

from utspclient.client import request_time_series_and_wait_for_delivery, send_request
from utspclient.datastructures import (
    CalculationStatus,
    ResultDelivery,
    TimeSeriesRequest,
)

from matplotlib import pyplot as plt


# Define UTSP connection parameters
URL = "http://134.94.131.167:443/api/v1/profilerequest"
API_KEY = "OrjpZY93BcNWw8lKaMp0BEchbCc"


def calculate_multiple_hisim_requests(hisim_configs: List[str]) -> List[ResultDelivery]:
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
            # required_result_files=dict.fromkeys(["kpi_config.json"]),
        )
        for config in hisim_configs
    ]

    # Send all requests to the UTSP
    for request in all_requests:
        # This function just sends the request and immediately returns so the other requests don't have to wait
        reply = send_request(URL, request, API_KEY)

    # Collect the results
    results: List[ResultDelivery] = []
    for request in all_requests:
        # This function waits until the request has been processed and the results are available
        result = request_time_series_and_wait_for_delivery(URL, request, API_KEY)
        assert (
            reply.status != CalculationStatus.CALCULATIONFAILED
        ), f"The calculation failed: {reply.info}"
        results.append(result)
    return results


def plot_sensitivity(curves: Dict[str, SensitivityAnalysisCurve]):
    """
    Creates a sensitivity star plot.

    :param curves: curves to plot
    :type curves: Dict[str, SensitivityAnalysisCurve]
    """
    # create a new figure
    fig = plt.figure()
    ax: plt.Axes = fig.add_subplot(1, 1, 1)
    fig.suptitle("HiSim Sensitivity Analysis - 1 year")

    description = "smart_devices_included=false, ev_included=false\nKPI=autarky_rate"

    ax.set_title(description, fontdict={"fontsize": 9})  # type: ignore
    ax.set_xlabel(f"Relative parameter value [%]")
    ax.set_ylabel("Relative KPI value [%]")

    # plot each curve
    for curve_name, curve in curves.items():
        ax.plot(curve.parameter_values, curve.kpi_values, label=curve_name, marker="x")

    # add a legend and show the figure
    ax.legend()
    plt.show()


def create_hisim_configs_from_parameter_value_list(
    parameter_name: str,
    parameter_values: List[float],
    base_config_path: str,
    boolean_attributes: Optional[List[str]] = None,
) -> List[str]:
    """
    Creates a list of HiSim configurations.
    Reads a base configuration from file and inserts a number of
    different values for a specific parameter. Each parameter value
    results in one hisim configuration.

    :param parameter_name: the name of the parameter
    :type parameter_name: str
    :param parameter_values: the list of values for the parameter
    :type parameter_values: List[float]
    :param base_config_path: the path to the base configuration file
    :type base_config_path: str
    :return: a list of hisim configurations
    :rtype: List[str]
    """
    config_dict = load_hisim_config(base_config_path)

    # insert all values for the parameter and thus create different HiSim configurations
    config = config_dict["system_config_"]
    if parameter_name not in config:
        # if the parameter is not in the system_config, look in the archetype_config instead
        config = config_dict["archetype_config_"]
    assert parameter_name in config, f"Invalid parameter name: {parameter_name}"

    all_hisim_configs = []
    for value in parameter_values:
        # set the respective value
        config[parameter_name] = value
        # optionally set boolean flags for this parameter if the value is not 0
        if boolean_attributes:
            for attribute in boolean_attributes:
                config[attribute] = value != 0
        # append the config string to the list
        all_hisim_configs.append(json.dumps(config_dict))
    return all_hisim_configs


def save_all_results(
    parameter_name: str, parameter_values: List[float], results: List[ResultDelivery]
):
    for i, value in enumerate(parameter_values):
        # save result files
        result_folder_name = f"./hisim_sensitivity_analysis/{parameter_name}-{value}"
        # Create the directory if it does not exist
        try:
            os.makedirs(result_folder_name)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(result_folder_name):
                pass
            else:
                raise
        for filename, content in results[i].data.items():
            filepath = os.path.join(result_folder_name, filename)
            with open(filepath, "wb") as file:
                file.write(content)


def multiple_parameter_sensitivity_analysis(
    base_config_path: str,
    parameter_value_ranges: Dict[str, List[float]],
    boolean_attributes: Optional[Dict[str, List[str]]] = None,
):
    """
    Executes a sensitivity analysis for multiple parameters. For each parameter, one
    curve is shown (a single KPI for multiple parameter values). This results in a
    'Star Plot'.
    All parameters use the same base configuration specified in a file. Then, only the
    value for one parameter at at time is changed.

    :param base_config_path: path to the base configuration file
    :type base_config_path: str
    :param parameter_value_ranges: value ranges for all parameters to investigate
    :type parameter_value_ranges: Dict[str, List[float]]
    """
    # define base values for each parameter that will be varied
    base_values = read_base_config_values(
        base_config_path, parameter_value_ranges.keys()
    )
    for name, base_value in base_values.items():
        if base_value not in parameter_value_ranges[name]:
            print(
                f"Added missing base value '{base_value}' to the value list of parameter '{name}'."
            )
            parameter_value_ranges[name].append(base_value)
            parameter_value_ranges[name].sort()

    # if parameter is not specified, no special boolean attributes need to
    # be changed. Assign an empty dict.
    if boolean_attributes is None:
        boolean_attributes = {}

    all_hisim_configs: List[str] = []
    for parameter_name, parameter_values in parameter_value_ranges.items():
        # get the hisim configs with the respective values
        hisim_configs = create_hisim_configs_from_parameter_value_list(
            parameter_name,
            parameter_values,
            base_config_path,
            boolean_attributes.get(parameter_name, None),
        )
        # put all hisim configs in a single list to calculate them all in parallel
        all_hisim_configs.extend(hisim_configs)

    all_results = calculate_multiple_hisim_requests(all_hisim_configs)
    print(f"Retrieved results from {len(all_results)} HiSim requests")

    index = 0
    for parameter_name, parameter_values in parameter_value_ranges.items():
        # for each parameter value, there is one result object
        num_results = len(parameter_values)
        results_for_one_param = all_results[index : index + num_results]
        index += num_results
        print(f"Retrieved {num_results} results for parameter {parameter_name}")
        # process all requests and retrieve the results

        save_all_results(parameter_name, parameter_values, results_for_one_param)


def main():
    base_config_path = "examples\\input data\\hisim_config.json"
    # Define value ranges for the parameter to investigate
    parameter_value_ranges = {
        # "pv_peak_power": [1e3, 2e3, 5e3, 10e3],
        # "battery_capacity": [1, 2, 5, 10]
        # "buffer_volume": [0, 80, 100, 150, 200, 500, 1000],
        "building_code": ["DE.N.SFH.01.Gen.ReEx.001.002", "DE.N.SFH.05.Gen.ReEx.001.002", "DE.N.SFH.10.Gen.ReEx.001.002"]
    }
    boolean_attributes = {
        "battery_capacity": ["battery_included"],
        "buffer_volume": ["buffer_included"],
    }

    multiple_parameter_sensitivity_analysis(
        base_config_path, parameter_value_ranges, boolean_attributes
    )


if __name__ == "__main__":
    main()
