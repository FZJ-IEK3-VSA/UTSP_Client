"""Sends multiple requests to HiSim and collects all results."""

import copy
import errno
import itertools
import json
import os
from typing import Dict, List, Optional, Union

import pandas as pd

from postprocessing.sensitivity_plots import (  # type: ignore
    load_hisim_config, read_base_config_values)
from utspclient.client import (request_time_series_and_wait_for_delivery,
                               send_request)
from utspclient.datastructures import ResultDelivery, TimeSeriesRequest

# Define UTSP connection parameters
URL = "http://134.94.131.167:443/api/v1/profilerequest"
API_KEY = "OrjpZY93BcNWw8lKaMp0BEchbCc"


def calculate_multiple_hisim_requests(
    hisim_configs: List[str], return_exceptions: bool = False, result_files = None,
) -> List[Union[ResultDelivery, Exception]]:
    """
    Sends multiple hisim requests for parallel calculation and collects
    their results.

    :param hisim_configs: the hisim configurations to calculate
    :type hisim_configs: List[str]
    :param return_exceptions: whether exceptions should be caught and returned in the result list, defaults to False
    :type return_exceptions: bool, optional
    :return: a list containing the content of the result KPI file for each request
    :rtype: List[str]
    """
    # Create all request objects
    all_requests = [
        TimeSeriesRequest(
            config,
            "hisim",
            guid="1",
            required_result_files=result_files or {},
        )
        for config in hisim_configs
    ]

    # Send all requests to the UTSP
    for request in all_requests:
        # This function just sends the request and immediately returns so the other requests don't have to wait
        send_request(URL, request, API_KEY)

    # Collect the results
    results: List[Union[ResultDelivery, Exception]] = []
    for request in all_requests:
        # This function waits until the request has been processed and the results are available
        try:
            result = request_time_series_and_wait_for_delivery(URL, request, API_KEY)
            results.append(result)
        except Exception as e:
            if return_exceptions:
                # return the exception as result
                results.append(e)
            else:
                raise
    return results


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


def create_dir_if_not_exists(result_folder_name: str):
    # Create the directory if it does not exist
    try:
        os.makedirs(result_folder_name)
    except OSError as exc:
        if exc.errno != errno.EEXIST or not os.path.isdir(result_folder_name):
            raise


def save_single_result(result_folder_name: str, result: ResultDelivery):
    create_dir_if_not_exists(result_folder_name)
    # save all result files in the folder
    for filename, content in result.data.items():
        filepath = os.path.join(result_folder_name, filename)
        with open(filepath, "wb") as file:
            file.write(content)


def save_all_results(
    parameter_name: str, parameter_values: List[float], results: List[ResultDelivery]
):
    for i, value in enumerate(parameter_values):
        # save result files
        result_folder_name = (
            f"./results/hisim_sensitivity_analysis/{parameter_name}-{value}"
        )
        save_single_result(result_folder_name, results[i])


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
    all_results = calculate_multiple_hisim_requests(hisim_config_strings, result_files=dict.fromkeys(["kpi_config.json"]))
    print(f"Retrieved results from {len(all_results)} HiSim requests")
    assert all(
        isinstance(r, ResultDelivery) for r in all_results
    ), "Found an invalid result object"

    index = 0
    for parameter_name, parameter_values in parameter_value_ranges.items():
        # for each parameter value, there is one result object
        num_results = len(parameter_values)
        results_for_one_param = all_results[index : index + num_results]
        index += num_results
        print(f"Retrieved {num_results} results for parameter {parameter_name}")
        # process all requests and retrieve the results

        save_all_results(parameter_name, parameter_values, results_for_one_param)  # type: ignore


def building_code_and_heating_system_calculations(building_codes: List[str], heating_systems: List[str]):
    
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
        all_hisim_configs, return_exceptions=True
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


def boolean_parameter_test():
    base_config_path = "examples\\input data\\hisim_config.json"
    # parameter ranges for full boolean parameter test
    parameters = [
        "pv_included",
        "smart_devices_included",
        "buffer_included",
        "battery_included",
        # "heatpump_included",
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
        all_hisim_configs, return_exceptions=True
    )

    base_folder = f"./results/hisim_boolean_parameter_test"
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


def main():
    codes = pd.read_csv("examples\\tabula_codes.csv", sep=";", comment="#") # skiprows=[0]
    building_codes = list(codes["Code_BuildingVariant"])
    building_codes = building_codes[:3]

    heating_systems = ["HeatPump", "DistrictHeating"]

    building_code_and_heating_system_calculations(building_codes=building_codes, heating_systems=heating_systems)

    # --- Sensitivity Analysis
    base_config_path = "examples\\input data\\hisim_config.json"
    # Define value ranges for the parameter to investigate
    parameter_value_ranges = {
        # "pv_peak_power": [1e3, 2e3, 5e3, 10e3],
        # "battery_capacity": [1, 2, 5, 10],
        # "buffer_volume": [0, 80, 100, 150, 200, 500, 1000],
        "building_code": [
            "DE.N.SFH.01.Gen.ReEx.001.002",
            "DE.N.SFH.05.Gen.ReEx.001.002",
            "DE.N.SFH.10.Gen.ReEx.001.002",
        ]
    }

    # additional boolean attributes that must be set depending on
    # the value of the continuous parameter
    boolean_attributes = {
        "battery_capacity": ["battery_included"],
        "buffer_volume": ["buffer_included"],
    }

    # multiple_parameter_sensitivity_analysis(
    #     base_config_path, parameter_value_ranges, boolean_attributes
    # )


if __name__ == "__main__":
    # boolean_parameter_test()
    main()
