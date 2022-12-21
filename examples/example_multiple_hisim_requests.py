"""Sends multiple requests to HiSim and collects all results."""

from dataclasses import dataclass
import json
import os
from typing import Dict, Iterable, List, Optional, Tuple

from utspclient.client import request_time_series_and_wait_for_delivery, send_request
from utspclient.datastructures import CalculationStatus, TimeSeriesRequest

import numpy as np
from matplotlib import pyplot as plt


# Define UTSP connection parameters
URL = "http://134.94.131.167:443/api/v1/profilerequest"
API_KEY = "OrjpZY93BcNWw8lKaMp0BEchbCc"


@dataclass
class SensitivityAnalysisCurve:
    """
    Class that represents one curve in the Sensitivity Analysis Star Plot. This can be
    a curve for one KPI or for one parameter.
    Contains relative parameter and kpi values that can directly be plotted.
    """

    parameter_values: List[float]
    kpi_values: List[float]


def load_hisim_config(config_path: str) -> Dict:
    """
    Loads a hisim configuration from file.

    :param config_path: path of the configuration file
    :type config_path: str
    :return: configuration dict
    :rtype: Dict
    """
    # load a HiSim system configuration
    example_folder = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(example_folder, config_path)
    with open(config_path, "r") as config_file:
        config_dict = json.load(config_file)
    return config_dict


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


def plot_sensitivity(curves: Dict[str, SensitivityAnalysisCurve]):
    """
    Creates a sensitivity star plot.

    :param curves: curves to plot
    :type curves: Dict[str, SensitivityAnalysisCurve]
    """
    # create a new figure
    fig = plt.figure()
    ax: plt.Axes = fig.add_subplot(1, 1, 1)
    ax.set_title("HiSim Sensitivity Analysis")
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
    system_config_ = config_dict["system_config_"]
    assert parameter_name in system_config_, f"Invalid parameter name: {parameter_name}"
    all_hisim_configs = []
    for value in parameter_values:
        # set the respective value
        system_config_[parameter_name] = value
        # append the config string to the list
        all_hisim_configs.append(json.dumps(config_dict))
    return all_hisim_configs


def get_kpi_lists_from_results(results: List[str]) -> Dict[str, List[float]]:
    """
    Extracts the relevant KPIs from the list of result strings and produces one
    list for each KPI.

    :param results: list of result strings from the HiSim requests
    :type results: List[str]
    :return: dict containing one list for each KPI
    :rtype: Dict[str, List[float]]
    """
    # create lists of the relevant KPIs
    relevant_kpis = ["self_consumption_rate", "autarky_rate"]
    kpis: Dict[str, List[float]] = {}
    for result in results:
        # parse the results from a single request
        result_dict = json.loads(result)
        for key, value in result_dict.items():
            if key in relevant_kpis:
                if key not in kpis:
                    kpis[key] = []
                # add the kpi to the respective list
                kpis[key].append(value)
    return kpis


def calculate_relative_values(
    parameter_values: List[float], kpi_values: List[float], base_index: int
) -> SensitivityAnalysisCurve:
    """
    Turns the absolute parameter values and KPI values into relative values, using
    the base value specified through base_index.

    :param parameter_values: absolute parameter values for one curve
    :type parameter_values: List[float]
    :param kpi_values: absolute KPI values for one curve
    :type kpi_values: List[float]
    :param base_index: index of the base value within the lists
    :type base_index: int
    :return: a curve object for plotting
    :rtype: SensitivityAnalysisCurve
    """
    # determine the norming factors for calculating the relative parameter/KPI values (in percent)
    norm_factor_parameter = parameter_values[base_index] / 100
    norm_factor_kpi = kpi_values[base_index] / 100

    # calculate the parameter and KPI values relative to the base scenario values
    parameter_values_relative = [
        value / norm_factor_parameter for value in parameter_values
    ]
    kpi_relative = [val / norm_factor_kpi for val in kpi_values]
    return SensitivityAnalysisCurve(parameter_values_relative, kpi_relative)


def single_parameter_sensitivity_analysis(
    parameter_name: str,
    parameter_values: List[float],
    base_config_path: str,
    base_index: int = None,
):
    """
    Executes a sensitivity analysis for a single parameter. Plots one curve for each
    KPI (currently autarky rate and self consumption rate).

    :param parameter_name: name of the parameter to investigate
    :type parameter_name: str
    :param parameter_values: values for the parameter
    :type parameter_values: List[float]
    :param base_config_path: path to the base config file
    :type base_config_path: str
    :param base_scenario_index: base index to use for calculating relative values,
                                defaults to middle value of the lists
    :type base_scenario_index: int, optional
    """
    # determine the index of the value which is used as base value for calculating relative value
    if base_index is None:
        # if not specified, use the value in the middle
        base_index = len(parameter_values) // 2 - 1

    # get the hisim configs with the respective values
    hisim_configs = create_hisim_configs_from_parameter_value_list(
        parameter_name, parameter_values, base_config_path
    )

    # process all requests and retrieve the results
    results = calculate_multiple_hisim_requests(hisim_configs)
    print(f"Retrieved results from {len(results)} HiSim requests")

    kpis = get_kpi_lists_from_results(results)

    # print parameter values and kpis
    print(f"parameter_values: {parameter_values}")
    for kpi_name, kpi_values in kpis.items():
        print(f"{kpi_name}: {kpi_values}")

    curves: Dict[str, SensitivityAnalysisCurve] = {}
    for kpi_name, kpi_values in kpis.items():
        curve = calculate_relative_values(parameter_values, kpi_values, base_index)
        curves[kpi_name] = curve

    plot_sensitivity(curves)


def read_base_config_values(
    base_config_path: str, relevant_parameters: Iterable[str]
) -> Dict[str, float]:
    """
    Reads the base configuration parameters from the configuration file.

    :param base_config_path: path to the configuration file
    :type base_config_path: str
    :param relevant_parameters: a list of parameter names that will be investigated
    :type relevant_parameters: Iterable[str]
    :return: a dict containing the relevant parameters and their respective base values
    :rtype: Dict[str, float]
    """
    config_dict = load_hisim_config(base_config_path)
    system_config_ = config_dict["system_config_"]
    base_values = {}
    for name in relevant_parameters:
        assert (
            name in system_config_
        ), f"Parameter '{name} is not contained in the hisim configuration"
        base_values[name] = system_config_[name]
    return base_values


def multiple_parameter_sensitivity_analysis(
    base_config_path: str, parameter_value_ranges: Dict[str, List[float]]
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
    curves: Dict[str, SensitivityAnalysisCurve] = {}
    for parameter_name, parameter_values in parameter_value_ranges.items():
        # get the hisim configs with the respective values
        hisim_configs = create_hisim_configs_from_parameter_value_list(
            parameter_name, parameter_values, base_config_path
        )
        # process all requests and retrieve the results
        results = calculate_multiple_hisim_requests(hisim_configs)
        print(f"Retrieved results from {len(results)} HiSim requests")

        # get a list for each KPI
        kpis = get_kpi_lists_from_results(results)

        # select a KPI or combine multiple KPI into a new KPI
        # TODO: which KPI(s) should be used here?
        # kpi_sum = np.sum([kpis["autarky_rate"], kpis["self_consumption_rate"]], axis=0)
        result_kpi = kpis["autarky_rate"]

        # find the index of the base value for norming
        base_value = base_values[parameter_name]
        base_index = parameter_values.index(base_value)

        # calculate relative parameter and KPI values and store them in a curve object
        curve = calculate_relative_values(parameter_values, result_kpi, base_index)

        # store the curve object in the dict
        curves[parameter_name] = curve

    plot_sensitivity(curves)


def main():
    base_config_path = "input data\\hisim_config.json"
    # Define value ranges for the parameter to investigate
    parameter_value_ranges = {
        "pv_peak_power": [500, 1000, 2000, 4000],
        "battery_capacity": [0.5, 1.5, 4, 8, 12],
        "buffer_volume": [50, 100, 500, 800, 1000, 1200, 1500],
        # "chp_power": [2, 4, 6, 12],
    }

    # Same relative points for all parameters
    # relative_parameter_values = [0.5, 0.75, 1, 1.25, 1.5]
    # parameter_value_ranges = {
    #     key: [value * factor for factor in relative_parameter_values]
    #     for key, value in base_values.items()
    # }

    multiple_parameter_sensitivity_analysis(base_config_path, parameter_value_ranges)

    # single_parameter_sensitivity_analysis(
    #     parameter_name, parameter_values, base_config_path
    # )


if __name__ == "__main__":
    main()
