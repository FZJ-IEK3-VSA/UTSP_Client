"""
Sends multiple requests to perform a scenario analysis for HiSim.
Stores the results locally for postprocessing.
Multiple parameters are varied at the same time based on an input csv file.
"""

import copy
import json
from typing import Dict, List

from dataclasses import field

import pandas as pd
from utspclient.datastructures import ResultDelivery, ResultFileRequirement

from postprocessing.sensitivity_plots import (  # type: ignore
    load_hisim_config,
)

from example_multiple_hisim_requests import calculate_multiple_hisim_requests
from example_hisim_sensitivity_analysis import save_single_result

from utspclient.helpers.lpgdata import (Households, TransportationDeviceSets,)


def create_hisim_configs_from_parameter_tuples(
    parameter_names: List[str],
    parameter_values: List[List[float]],
    base_config: Dict,
) -> List[Dict]:
    """
    Creates a list of HiSim configurations.
    Reads a base configuration from file and inserts a number of
    different values for specific parameters. Each parameter value combination
    results in one hisim configuration.

    :param parameter_names: the names of the parameters
    :type parameter_name: List[str]
    :param parameter_values: the list of values for the parameters
    :type parameter_values: List[List[float]]
    :param base_config_path: the path to the base configuration file
    :type base_config_path: str
    :return: a list of hisim configurations
    :rtype: List[str]
    """

    # insert all values for the parameter and thus create different HiSim configurations
    all_hisim_configs = []
    
    for values in parameter_values:
        for (parameter_number, parameter_name) in enumerate(parameter_names):
            # clone the config dict
            new_config = copy.deepcopy(base_config)
            if parameter_name in base_config["system_config_"]:
                config_key = "system_config_"
            elif parameter_name in base_config["archetype_config_"]:
                # if the parameter is not in the system_config, look in the archetype_config instead
                config_key = "archetype_config_"
            else:
                assert False, f"Invalid parameter name: {parameter_name}"
            config = new_config[config_key]

            # set the respective value
            config[parameter_name] = values[parameter_number]
        # append the config string to the list
        all_hisim_configs.append(new_config)
    return all_hisim_configs

def multiple_parameter_scenario_analysis(
    base_config_path: str,
    parameter_names: List[str],
    parameter_values: List[List[str]],
    result_files: Dict = None,
):
    """
    Executes a scenario analysis for multiple parameters. For each parameter combination, one
    hisim request is prepared.
    All parameters use the same base configuration specified in a file. Then, only the
    value for the specified parameter combination is changed.

    :param base_config_path: path to the base configuration file
    :type base_config_path: str
    :param parameter_value_ranges: value ranges for all parameters to investigate
    :type parameter_value_ranges: Dict[List[str], List[List[str]]]
    """
    # read the base config from file
    config_dict = load_hisim_config(base_config_path)

    all_hisim_configs: List[str] = []

    # get the hisim configs with the respective values
    hisim_configs = create_hisim_configs_from_parameter_tuples(
        parameter_names,
        parameter_values,
        config_dict,
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

    assert len(all_results) == len(
        hisim_configs
    ), "Number of results does not match number of configs"
    for i, value in enumerate(parameter_values):
        # save result files
        result_folder_name = (
            f"./results/hisim_scenario_analysis/{i}-{value[0]}-{value[1]}"
        )
        save_single_result(result_folder_name, all_results[i], hisim_configs[i])

def read_parameter_values(path: str) -> List[List[str]]:
    """Reads in - and converts parameter values for scenario from csv file."""
    parameters = pd.read_csv(path, encoding="utf-8", sep=";")

    ev_translator = {
        0: None,
        1: TransportationDeviceSets.Bus_and_one_30_km_h_Car.to_dict(),
        2: TransportationDeviceSets.Bus_and_two_30_km_h_Cars.to_dict(),
    }

    lpg_classifier = parameters["LPG-Template"].to_list()
    lpg_classifier = [elem[:5] for elem in lpg_classifier]
    """TODO: translate modular household classifier to {"Name": ..., "Guid":{"StrVal":...}}"""
    ev_classifier = parameters["Anzahl E-Autos"].to_list()
    ev_classifier = [ev_translator[elem] for elem in ev_classifier]

    parameter_values = [[lpg, ev] for (lpg, ev) in zip(lpg_classifier, ev_classifier)]
    return parameter_values


if __name__ == "__main__":
    parameter_values = read_parameter_values(path= "examples\\input data\\Mainthal.csv")
    result_files = {"UTSP_connector.ElectricityOutput.csv": ResultFileRequirement.REQUIRED,
                    "UTSP_connector.InnerDeviceHeatGains.csv": ResultFileRequirement.REQUIRED,
                    "UTSP_connector.HeatingByResidents.csv": ResultFilesRequirement.REQUIRED,
                    }
    """TODO: Add car battery charge of both Car batteries if available."""
    """Main execution function."""
    hisim_configs = multiple_parameter_scenario_analysis(
        base_config_path="examples\\input data\\scenario_config.json",
        parameter_names=["occupancy_profile_utsp", "mobility_set"],
        parameter_values=parameter_values,
        result_files=result_files
    )