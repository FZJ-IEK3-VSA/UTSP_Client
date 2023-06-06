"""Combines single output files 'csv_for_housing_database.csv' of all HiSIM 
evaluations in a directory to one common csv file in the format
suitable for ESM modellers."""

import os
import pandas as pd
import tqdm

from examples.postprocessing import sensitivity_plots


def modify_dataframe(results: pd.DataFrame) -> pd.DataFrame:
    """Splits header to multiple lines for better understanding of building code.

    Also converts oil and diesel consumption from l to kWh. Therfore a value of
    10 kWh/l is used. This corresponds to the corresponding heat value (not the calorific value).
    In addition it cuts the values not relevant for ESM modellers.

    :param results: Dataframe containing all results
    :type results: pd.DataFrame
    :return: DataFrame with new header and right conversions with all the results.
    :rtype: pd.DataFrame
    """

    # extract header
    headerlist = results.columns.to_list()

    # extract relevant information for Multi-Index
    tabulaname = ["TabulaName", "str"] + headerlist[2:]
    climatezones = ["ClimateZone", "str"] + [
        elem.split(".")[0] for elem in headerlist[2:]
    ]
    housetypes = ["House Type", "str"] + [elem.split(".")[2] for elem in headerlist[2:]]
    constructionyears = ["Construction Year", "str"] + [
        elem.split(".")[3] for elem in headerlist[2:]
    ]
    rennovationdegrees = ["Rennovation Degree", "str"] + [
        elem.split(".")[7][:3] for elem in headerlist[2:]
    ]

    # make multiindex
    results.columns = pd.MultiIndex.from_tuples(
        [
            (b, c, d, e)
            for (b, c, d, e) in zip(
                climatezones, housetypes, constructionyears, rennovationdegrees
            )
        ],
        names=["ClimateZones", "HouseTypes", "ConstructionYear", "RennovationDegree"],
    )

    # convert from l to kWh
    for i in [0, 6, 15]:
        results.loc[i, results.columns[2:]] *= 10

    # return only relevant data for ESM guys - skip building validation data from row 18 - 20
    return results.loc[
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 21]
    ]


def combine_building_code_results(result_folder: str):
    """
    Combines all csv_for_housing_data_base.csv files from the result folders
    in the specified location into a single csv file

    :param result_folder: the parent directory of the result folders
    :type result_folder: str
    """
    all_result_directories = os.listdir(result_folder)
    columns = {}
    # initialize empty data frame
    first_result = pd.read_csv(
        os.path.join(
            result_folder, all_result_directories[0], "csv_for_housing_data_base_annual.csv"
        ),
        usecols=[0, 1],
    )
    # add label columns
    columns["Category"] = first_result["Category"]
    columns["Fuel"] = first_result["Fuel"]

    # extract the relevant data column out of each result folder
    folders_without_results = 0
    for result_directory in tqdm.tqdm(all_result_directories):
        result_path = os.path.join(result_folder, result_directory)
        if not os.path.isdir(result_path):
            # not a folder - skip
            continue
        config_file_path = os.path.join(result_path, "hisim_config.json")
        config = sensitivity_plots.load_hisim_config(config_file_path)

        result_file_path = os.path.join(result_path, "csv_for_housing_data_base_annual.csv")
        if not os.path.isfile(result_file_path):
            # skip this folder if the result file is missing
            folders_without_results += 1
            continue

        result_data = pd.read_csv(result_file_path)
        result_data_column = result_data["0"]
        rowname = (
            config["archetype_config_"]["building_code"]
            + "-"
            + config["archetype_config_"]["heating_system_installed"]
        )
        columns[rowname] = result_data_column
    print(
        f"{folders_without_results} folders did not contain the csv_for_housing_data_base_annual.csv file."
    )

    # concatenate all columns to a single dataframe and save it as a file
    results = pd.concat(columns, axis=1)
    results = modify_dataframe(results=results)
    results.to_csv(os.path.join(result_folder, "database_for_ESM.csv"), sep=";", decimal=",")


def main():
    """Main execution function."""
    result_folder = f"./results/hisim_building_code_calculations/HeatPump"
    combine_building_code_results(result_folder)


if __name__ == "__main__":
    main()
