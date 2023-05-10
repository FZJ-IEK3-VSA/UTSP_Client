"""Creates sensitivity plots for the validation of components
and buildings in HiSIM."""

from dataclasses import dataclass
import json
from os import listdir
import os
from typing import Dict, Iterable, List, Union, Tuple
from mpl_toolkits.axes_grid1 import host_subplot  # type: ignore
import mpl_toolkits.axisartist as AA  # type: ignore
import matplotlib.pyplot as plt


@dataclass
class SensitivityAnalysisCurve:
    """
    Class that represents one curve in the Sensitivity Analysis Star Plot. This can be
    a curve for one KPI or for one parameter.
    Contains relative and absolute parameter and kpi values.
    """

    #: capacities of the involved technology in absolut numbers
    parameter_values_absolute: List[float]
    #: capacities of the involved technology in relative numbers (compared to the reference size)
    parameter_values_relative: List[float]
    #: key performance indicator (e. g. self consumption rate or autarky rate) in absolut numbers
    kpi_values_absolute: List[float]
    #: key performance indicator in relative numbers (compared to reference size)
    kpi_values_relative: List[float]


def load_hisim_config(config_path: str) -> Dict:
    """
    Loads a hisim configuration from file.

    :param config_path: path of the configuration file
    :type config_path: str
    :return: configuration dict
    :rtype: Dict
    """
    # load a HiSim system configuration
    config_path = os.path.join(config_path)
    with open(config_path, "r") as config_file:
        config_dict = json.load(config_file)
    return config_dict


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
    base_values = {}
    for parameter_name in relevant_parameters:
        config = config_dict["system_config_"]
        if parameter_name not in config:
            # if the parameter is not in the system_config, look in the archetype_config instead
            config = config_dict["archetype_config_"]
        assert parameter_name in config, f"Invalid parameter name: {parameter_name}"
        base_values[parameter_name] = config[parameter_name]
    return base_values


def read_sensitivity_results(
    path: str, float_values: bool = True
) -> Dict[str, Dict[Union[float, str], Dict[str, float]]]:
    """Combines results of all calculations in a structured Dictionary.

    :param path: directory of the results from HiSIM calculations of the UTSP
    :type path: str
    :param float_values: indicates if technologies of considered technologies are
                         containedin the filname as float, defaults to True
    :type float_values: bool, optional
    :return: Dictionary containing all KPI's in the right structure for plotting.
    :rtype: Dict[str, Dict[Union[float, str], Dict[str, float]]]
    """    

    all_result_folders = listdir(path)
    all_kpis: Dict[str, Dict[Union[float, str], Dict[str, float]]] = {}
    for folder in all_result_folders:
        parameter_name, parameter_value = folder.split("-")
        if parameter_name not in all_kpis:
            all_kpis[parameter_name] = {}
        kpi_file = os.path.join(path, folder, "kpi_config.json")
        with open(kpi_file, "r", encoding="utf-8") as file:
            if float_values:
                all_kpis[parameter_name][float(parameter_value)] = json.load(file)
            else:
                all_kpis[parameter_name][parameter_value] = json.load(file)
    return all_kpis


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
    parameter_values = [float(elem) for elem in parameter_values]
    norm_factor_parameter = parameter_values[base_index] / 100
    norm_factor_kpi = kpi_values[base_index] / 100

    # calculate the parameter and KPI values relative to the base scenario values
    parameter_values_relative = [
        value / norm_factor_parameter for value in parameter_values
    ]
    kpi_relative = [val / norm_factor_kpi for val in kpi_values]
    return SensitivityAnalysisCurve(
        parameter_values, parameter_values_relative, kpi_values, kpi_relative
    )


def calculate_absolute_values(
    relative_parameter_values: List[float],
    relative_kpi_values: List[float],
    parameter_values: List[float],
    kpi_values: List[float],
    base_index: int,
) -> Tuple[List[float], List[float]]:
    """
    Turns the relative parameter axis values back into absolute values, using
    the base value specified through base_index.

    :param relative_parameter_values: relative parameter values (ticks of x-axis)
    :type parameter_values: List[float]
    :param relative_kpi_values: relative KPI values (ticks of y-axis)
    :type kpi_values: List[float]
    :param base_index: index of the base value within the lists
    :type base_index: int
    :return: two lists: absolute parameter values and absolute kpi values as ticks for new axis
    :rtype: Tuple[List[float],List[float]]

    """

    # determine the norming factors for calculating the relative parameter/KPI values (in percent)
    norm_factor_parameter = parameter_values[base_index] / 100
    norm_factor_kpi = kpi_values[base_index] / 100

    absolute_parameter_values = [
        value * norm_factor_parameter for value in relative_parameter_values
    ]
    absolute_kpi_values = [value * norm_factor_kpi for value in relative_kpi_values]
    return absolute_parameter_values, absolute_kpi_values


def plot_sensitivity_results(
    all_kpis: Dict[str, Dict[float, Dict[str, float]]],
    base_config_path: str,
    kpi_name: str,
):
    """Creates a sensitivity star plot for various technologies.

    :param all_kpis: Results of the sensitivity analysis combined in a dictionary.
                     Output of function read_sensitivity_results()
    :type all_kpis: Dict[str, Dict[float, Dict[str, float]]]
    :param base_config_path: Directory to the configuration of the reference calculation.
    :type base_config_path: str
    :param kpi_name: Selection of the KPI to be plotted (e. g. "autarky_rate" or "self_consumption_rate"s)
    :type kpi_name: str
    """    
    # define base values for each parameter that will be varied
    base_values = read_base_config_values(base_config_path, all_kpis.keys())

    # initialize empty figure
    host = host_subplot(111, axes_class=AA.Axes)
    plt.subplots_adjust(right=0.75, top=0.75)
    host.set_xlabel("relative capacity [%]")
    host.set_ylabel("relative devitaion [%]")

    host.set_xlabel(f"Relative parameter value [%]")
    host.set_ylabel(f"Relative {kpi_name} value [%]")

    lines = []
    curves = []
    base_indices = []
    for parameter_name, kpis in all_kpis.items():
        # select a KPI or combine multiple KPI into a new KPI
        parameter_values = [float(value) for value in kpis.keys()]
        kpi_values = [kpi[kpi_name] for kpi in kpis.values()]

        # sort by parameter value
        parameter_values, kpi_values = [
            list(x) for x in zip(*sorted(zip(parameter_values, kpi_values)))
        ]

        # find the index of the base value for norming
        base_value = base_values[parameter_name]
        base_index = parameter_values.index(base_value)

        # calculate relative parameter and KPI values and store them in a curve object
        curve = calculate_relative_values(parameter_values, kpi_values, base_index)

        lines.append(
            host.plot(
                curve.parameter_values_relative,
                curve.kpi_values_relative,
                label=parameter_name,
            )
        )
        curves.append(curve)
        base_indices.append(base_index)

    line_index: int = 0
    for parameter_name, kpis in all_kpis.items():
        # new y axis
        pary = host.twinx()
        new_fixed_axis = pary.get_grid_helper().new_fixed_axis
        pary.axis["right"] = new_fixed_axis(
            loc="right", axes=pary, offset=(line_index * 60, 0)
        )
        pary.axis["right"].toggle(all=True)
        pary.set_ylabel(f"{kpi_name} ({parameter_name}) [%]")
        y_original = host.get_yticks()
        pary.set_yticks(y_original)
        pary.set_ybound(host.get_ybound())

        parx = host.twiny()
        new_fixed_axis = parx.get_grid_helper().new_fixed_axis
        parx.axis["top"] = new_fixed_axis(
            loc="top", axes=parx, offset=(0, line_index * 45)
        )
        parx.axis["top"].toggle(all=True)
        unit = ""
        if parameter_name == 'battery_capacity':
            unit = " [kWh]"
        elif parameter_name == 'pv_peak_power':
            unit = " [kWp]"
        parx.set_xlabel(parameter_name + unit)
        x_original = host.get_xticks()
        parx.set_xticks(x_original)
        parx.set_xbound(host.get_xbound())

        # reset labels
        x_tick_values, y_tick_values = calculate_absolute_values(
            relative_parameter_values=x_original,
            relative_kpi_values=y_original,
            parameter_values=curves[line_index].parameter_values_absolute,
            kpi_values=curves[line_index].kpi_values_absolute,
            base_index=base_indices[line_index],
        )

        if unit == " [kWp]":
            x_tick_values = [elem*1e-3 for elem in x_tick_values]

        parx.set_xticklabels([str(round(value, 1)) for value in x_tick_values])
        pary.set_yticklabels([str(round(value, 1)) for value in y_tick_values])
        pary.axis["right"].label.set_color(lines[line_index][0].get_color())
        parx.axis["top"].label.set_color(lines[line_index][0].get_color())
        line_index += 1

    host.legend()
    plt.show()


def plot_building_codes_results(
    all_kpis: Dict[str, Dict[float, Dict[str, float]]], kpi_name: str
) -> None:
    """Creates a sensitivity star plot for various building types.

    :param all_kpis: Results of the sensitivity analysis combined in a dictionary.
                     Output of function read_sensitivity_results()
    :type all_kpis: Dict[str, Dict[float, Dict[str, float]]]
    :param base_config_path: Directory to the configuration of the reference calculation.
    :type base_config_path: str
    :param kpi_name: Selection of the KPI to be plotted (e. g. "autarky_rate" or "self_consumption_rate"s)
    :type kpi_name: str
    """

    assert (
        "building_code" in all_kpis and len(all_kpis) == 1
    ), "Invalid configuartion for this plotting function"

    building_code_results = all_kpis["building_code"]
    parameter_values = [value for value in building_code_results.keys()]
    kpi_values = [kpi[kpi_name] for kpi in building_code_results.values()]

    # create a new figure
    fig = plt.figure()
    ax: plt.Axes = fig.add_subplot(1, 1, 1)

    fig.suptitle("HiSim Sensitivity Analysis - 1 year")
    # description = "smart_devices_included=false, ev_included=false\nKPI=autarky_rate"
    # ax.set_title(description, fontdict={"fontsize": 9})  # type: ignore

    ax.set_xlabel(f"Tabula Building Code")
    ax.set_ylabel(kpi_name)

    # plot each curve
    ax.plot(parameter_values, kpi_values, marker="x")

    plt.xticks(rotation=65, ha="right")  # type: ignore
    fig.tight_layout()

    # add a legend and show the figure
    ax.legend()
    plt.show()


def main():
    """Main execution function."""
    # path = r"D:\Git-Repositories\utsp-client\results\hisim_sensitivity_analysis"
    # base_config_path = "examples\\input data\\hisim_config.json"
    base_config_path = r"C:\Users\Johanna\Desktop\UTSP_Client\examples\input data\hisim_config.json"
    path = r"C:\Users\Johanna\Desktop\HiSIM\examples\results\sensitivity_analysis"

    all_kpis = read_sensitivity_results(path, False)

    plot_sensitivity_results(all_kpis, base_config_path, "autarky_rate")

    # plot_building_codes_results(all_kpis, "self_consumption_rate")


if __name__ == "__main__":
    main()
