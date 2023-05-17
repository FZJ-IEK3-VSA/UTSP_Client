"""
Sends multiple requests to perform a sensitivity analysis for HiSim.
Stores the results locally for postprocessing.
"""

import copy
import errno
import itertools
import json
import os
from typing import Dict, List, Optional

import pandas as pd
from utspclient.datastructures import ResultDelivery, ResultFileRequirement

from postprocessing.sensitivity_plots import (  # type: ignore
    load_hisim_config,
    read_base_config_values,
)

from example_multiple_hisim_requests import calculate_multiple_hisim_requests


def create_hisim_configs_from_parameter_value_list(
    parameter_name: str,
    parameter_values: List[float],
    base_config: Dict,
    boolean_attributes: Optional[List[str]] = None,
) -> List[Dict]:
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

    if parameter_name in base_config["system_config_"]:
        config_key = "system_config_"
    elif parameter_name in base_config["archetype_config_"]:
        # if the parameter is not in the system_config, look in the archetype_config instead
        config_key = "archetype_config_"
    else:
        assert False, f"Invalid parameter name: {parameter_name}"

    # insert all values for the parameter and thus create different HiSim configurations
    all_hisim_configs = []
    for value in parameter_values:
        # clone the config dict
        new_config = copy.deepcopy(base_config)
        config = new_config[config_key]

        # set the respective value
        config[parameter_name] = value
        # optionally set boolean flags for this parameter if the value is not 0
        if boolean_attributes:
            for attribute in boolean_attributes:
                config[attribute] = value != 0
        # append the config string to the list
        all_hisim_configs.append(new_config)
    return all_hisim_configs


def create_dir_if_not_exists(result_folder_name: str) -> None:
    """Creates the result directory if it does not exist already.

    :param result_folder_name: Directory where the results of the HiSIM
                               calculations are stored.
    :type result_folder_name: str
    """

    try:
        os.makedirs(result_folder_name)
    except OSError as exc:
        if exc.errno != errno.EEXIST or not os.path.isdir(result_folder_name):
            raise


def save_single_result(
    result_folder_name: str,
    result: ResultDelivery | Exception,
    config: Optional[Dict] = None,
    mark_error_folder: bool = True,
):
    """
    Saves the result files of a single calculation in the specified folder,
    along with the input file that was used. If the calculation failed, the
    error message is saved in a file.

    :param result_folder_name: path of the result folder
    :type result_folder_name: str
    :param result: result object from the UTSP, or an exception
    :type result: ResultDelivery | Exception
    :param config: the config dict that was used as input, defaults to None
    :type config: Optional[Dict], optional
    :param mark_error_folder: if True, the name of the folder will be changed
        for failed calculations to facilitate finding them; defaults to True
    :type mark_error_folder: bool, optional
    """
    error_occurred = isinstance(result, Exception)
    if error_occurred and mark_error_folder:
        result_folder_name += " - error"
    create_dir_if_not_exists(result_folder_name)
    if error_occurred:
        # the calculation failed: save the error message
        error_message_file = os.path.join(result_folder_name, "exception.txt")
        with open(error_message_file, "w", encoding="utf-8") as error_file:
            error_file.write(str(result))
    else:
        # save all result files in the folder
        for filename, content in result.data.items():
            filepath = os.path.join(result_folder_name, filename)
            with open(filepath, "wb") as file:
                file.write(content)
    if config:
        # additionally save the config
        config_file_path = os.path.join(result_folder_name, "hisim_config.json")
        with open(config_file_path, "w", encoding="utf-8") as config_file:
            config_file.write(config)


def save_all_results(
    parameter_name: str,
    parameter_values: List[float],
    results: List[ResultDelivery],
    configs: List[Dict],
):
    assert len(results) == len(
        configs
    ), "Number of results does not match number of configs"
    for i, value in enumerate(parameter_values):
        # save result files
        result_folder_name = (
            f"./results/hisim_sensitivity_analysis/{parameter_name}-{value}"
        )
        save_single_result(result_folder_name, results[i], configs[i])


def multiple_parameter_sensitivity_analysis(
    base_config_path: str,
    parameter_value_ranges: Dict[str, List[float]],
    boolean_attributes: Optional[Dict[str, List[str]]] = None,
    result_files: Dict = None,
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

    # read the base config from file
    config_dict = load_hisim_config(base_config_path)

    all_hisim_configs: List[str] = []
    for parameter_name, parameter_values in parameter_value_ranges.items():
        # get the hisim configs with the respective values
        hisim_configs = create_hisim_configs_from_parameter_value_list(
            parameter_name,
            parameter_values,
            config_dict,
            boolean_attributes.get(parameter_name, None),
        )
        # put all hisim configs in a single list to calculate them all in parallel
        all_hisim_configs.extend(hisim_configs)

    hisim_config_strings = [json.dumps(config) for config in all_hisim_configs]
    all_results = calculate_multiple_hisim_requests(
        hisim_config_strings,
        raise_exceptions=False,
        result_files=result_files,
    )
    print(f"Retrieved results from {len(all_results)} HiSim requests")
    assert all(
        isinstance(r, (ResultDelivery, Exception)) for r in all_results
    ), "Found an invalid result object"

    index = 0
    for parameter_name, parameter_values in parameter_value_ranges.items():
        # for each parameter value, there is one result object
        num_results = len(parameter_values)
        results_for_one_param = all_results[index : index + num_results]
        configs_for_one_param = hisim_config_strings[index : index + num_results]
        index += num_results
        print(f"Retrieved {num_results} results for parameter {parameter_name}")
        # process all requests and retrieve the results

        save_all_results(parameter_name, parameter_values, results_for_one_param, configs_for_one_param)  # type: ignore


def building_code_and_heating_system_calculations(
    building_codes: List[str], heating_systems: List[str]
) -> None:
    """
    Creates HiSIM requests for various buildings with
    different heating systems.

    :param building_codes: Contains all building types to be calculated by HiSIM.
    :type building_codes: List[str]
    :param heating_systems: Contains all heating systems to be calculated in combination
                            with the indicated building types.
    :type heating_systems: List[str]
    """

    base_config_path = "examples\\input data\\hisim_config.json"
    config_dict = load_hisim_config(base_config_path)

    num_requests = len(building_codes) * len(heating_systems)
    print(f"Creating {num_requests} HiSim requests")

    # insert all values for the parameter and thus create different HiSim configurations
    config = config_dict["archetype_config_"]

    all_hisim_configs = []
    for building_code in building_codes:
        config["building_code"] = building_code
        for heating_system in heating_systems:
            config["heating_system_installed"] = heating_system
            config["water_heating_system_installed"] = heating_system
            # append the config string to the list
            all_hisim_configs.append(json.dumps(config_dict))

    all_results = calculate_multiple_hisim_requests(
        all_hisim_configs, raise_exceptions=False
    )

    base_folder = f"./results/hisim_building_code_calculations"
    digits = len(str(num_requests))
    for i, result in enumerate(all_results):
        folder_name = str(i).zfill(digits)
        result_folder_path = os.path.join(base_folder, folder_name)
        create_dir_if_not_exists(result_folder_path)
        if isinstance(result, Exception):
            # the calculation failed: save the error message
            error_message_file = os.path.join(result_folder_path, "exception.txt")
            with open(error_message_file, "w", encoding="utf-8") as error_file:
                error_file.write(str(result))
        else:
            # save all result files
            save_single_result(result_folder_path, result)
        # additionally save the config
        config_file_path = os.path.join(result_folder_path, "hisim_config.json")
        with open(config_file_path, "w", encoding="utf-8") as config_file:
            config_file.write(all_hisim_configs[i])


def boolean_parameter_test() -> None:
    """Varies all indicated boolean Parameters of the system configuration,
    simulates it by sending HiSIM requests to the UTSP and saves the results.
    
    The HiSIM configuration of the reference technology/building should be lacated in 
    examples/input data/"""    
    base_config_path = "examples\\input data\\hisim_config.json"
    # parameter ranges for full boolean parameter test
    parameters = [
        "pv_included",
        "smart_devices_included",
        "buffer_included",
        "battery_included",
        "heatpump_included",
        # "chp_included",
        # "h2_storage_included",
        # "electrolyzer_included",
        # "ev_included",
    ]

    num_requests = 2 ** len(parameters)
    print(f"Creating {num_requests} HiSim requests")

    config_dict = load_hisim_config(base_config_path)

    # insert all values for the parameter and thus create different HiSim configurations
    config = config_dict["system_config_"]

    # get powerset of boolean parameters (all possible combinations of arbitrary lenght)
    combinations = itertools.chain.from_iterable(
        itertools.combinations(parameters, r) for r in range(len(parameters) + 1)
    )

    all_hisim_configs = []
    for combination in combinations:
        # set all boolean parameters
        for parameter in parameters:
            config[parameter] = parameter in combination
        # append the config string to the list
        all_hisim_configs.append(json.dumps(config_dict))

    all_results = calculate_multiple_hisim_requests(
        all_hisim_configs, raise_exceptions=False
    )

    # save all result files and error messages
    base_folder = f"./results/hisim_boolean_parameter_test"
    digits = len(str(num_requests))
    for i, result in enumerate(all_results):
        folder_name = str(i).zfill(digits)
        result_folder_path = os.path.join(base_folder, folder_name)
        save_single_result(result_folder_path, result, all_hisim_configs[i])


def sensitivity_analysis():
    """Varies all indicated discrete Parameters of the system configuration,
    simulates it by sending HiSIM requests to the UTSP and saves the results.
    
    The HiSIM configuration of the reference technology/building should be lacated in 
    examples/input data/""" 
    # heating_systems = ["HeatPump", "DistrictHeating"]

    # building_code_and_heating_system_calculations(
    #     building_codes=building_codes, heating_systems=heating_systems
    # )

    building_codes = pd.read_csv(
        os.path.join("examples", "input data", "tabula_buildings.csv"),
        encoding="utf-8",
    )["Number"].to_list()

    # determine the base config to be used
    base_config_path = "examples\\input data\\hisim_config.json"

    # Define value ranges for the parameter to investigate
    parameter_value_ranges = {
        "building_code": building_codes,
    }

    # additional boolean attributes that must be set depending on
    # the value of the continuous parameter
    boolean_attributes = {
        # "battery_capacity": ["battery_included"],
        # "buffer_volume": ["buffer_included"],
    }

    result_files = {"csv_for_housing_data_base.csv": ResultFileRequirement.REQUIRED}

    multiple_parameter_sensitivity_analysis(
        base_config_path, parameter_value_ranges, boolean_attributes, result_files
    )


if __name__ == "__main__":
    """Main execution function."""
    # boolean_parameter_test()
    sensitivity_analysis()
