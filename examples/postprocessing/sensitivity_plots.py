from dataclasses import dataclass
import json
from os import listdir
import os
from typing import Dict, Iterable, List
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

    parameter_values_absolute: List[float]
    parameter_values_relative: List[float]
    kpi_values_absolute: List[float]
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
    example_folder = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(example_folder, config_path)
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
    system_config_ = config_dict["system_config_"]
    base_values = {}
    for name in relevant_parameters:
        assert (
            name in system_config_
        ), f"Parameter '{name} is not contained in the hisim configuration"
        base_values[name] = system_config_[name]
    return base_values


def read_sensitivity_results(path: str) -> Dict[str, Dict[float, Dict[str, float]]]:
    all_result_folders = listdir(path)
    all_kpis: Dict[str, Dict[float, Dict[str, float]]] = {}
    for folder in all_result_folders:
        parameter_name, parameter_value = folder.split("-")
        if parameter_name not in all_kpis:
            all_kpis[parameter_name] = {}
        kpi_file = os.path.join(path, folder, "kpi_config.json")
        with open(kpi_file, "r", encoding="utf-8") as file:
            all_kpis[parameter_name][float(parameter_value)] = json.load(file)
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


def plot_sensitivity_results(
    all_kpis: Dict[str, Dict[float, Dict[str, float]]], base_config_path: str
):
    # define base values for each parameter that will be varied
    base_values = read_base_config_values(base_config_path, all_kpis.keys())

    # initialize empty figure
    host = host_subplot(111, axes_class=AA.Axes)
    plt.subplots_adjust(right=0.75, top=0.75)

    offset = 0
    for parameter_name, kpis in all_kpis.items():
        # select a KPI or combine multiple KPI into a new KPI
        kpi_name = "autarky_rate"
        parameter_values = [value for value in kpis.keys()]
        kpi_values = [kpi[kpi_name] for kpi in kpis.values()]

        # find the index of the base value for norming
        base_value = base_values[parameter_name]
        base_index = parameter_values.index(base_value)

        # calculate relative parameter and KPI values and store them in a curve object
        curve = calculate_relative_values(parameter_values, kpi_values, base_index)

        pary = host.twinx()
        parx = host.twiny()

        new_fixed_axis = pary.get_grid_helper().new_fixed_axis
        pary.axis["right"] = new_fixed_axis(loc="right", axes=pary, offset=(offset, 0))
        pary.axis["right"].toggle(all=True)
        pary.set_ylabel(parameter_name)

        new_fixed_axis = parx.get_grid_helper().new_fixed_axis
        parx.axis["top"] = new_fixed_axis(loc="top", axes=parx, offset=(0, offset * 0.75))
        parx.axis["top"].toggle(all=True)
        parx.set_xlabel(parameter_name)

        pary.set_yticks(ticks=curve.kpi_values_relative, labels=[str(round(elem, 1)) for elem in curve.kpi_values_absolute])
        parx.set_xticks(ticks=curve.parameter_values_relative, labels=[str(round(elem, 1)) for elem in curve.parameter_values_absolute])

        line = pary.plot(
            curve.parameter_values_relative,
            curve.kpi_values_relative,
            label=parameter_name,
        )
        pary.axis["right"].label.set_color(line[0].get_color())
        parx.axis["top"].label.set_color(line[0].get_color())
        offset += 60

    host.legend()
    plt.show()
    pass


def main():
    # path = r"D:\Git-Repositories\utsp-client\hisim_sensitivity_analysis"
    path = r"C:\Users\Johanna\Desktop\UTSP_Client\hisim_sensitivity_analysis"
    base_config_path = "..\\input data\\hisim_config.json"
    all_kpis = read_sensitivity_results(path)
    plot_sensitivity_results(all_kpis, base_config_path)


if __name__ == "__main__":
    main()
