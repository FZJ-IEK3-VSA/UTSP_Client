"""Combines single output files 'csv_for_housing_database.csv' of all HiSIM 
evaluations in a directory to one common csv file in the format
suitable for ESM modellers."""

import os
from typing import Dict, List, Optional, Tuple
import pandas as pd
import tqdm

from examples.postprocessing import sensitivity_plots

# separators for the result files
DECIMAL_SEP = "."
COLUMN_SEP = ";"


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
    climatezones = [elem.split(".")[0] for elem in headerlist]
    housetypes = [elem.split(".")[2] for elem in headerlist]
    constructionyears = [elem.split(".")[3] for elem in headerlist]
    rennovationdegrees = [elem.split(".")[7][:3] for elem in headerlist]
    if "_" in headerlist[0]:
        season_and_day = [elem.split("_")[1] for elem in headerlist]
    else:
        season_and_day = ["annual" for _ in headerlist]

    # make multiindex
    results.columns = pd.MultiIndex.from_tuples(
        [
            (b, c, d, e, f)
            for (b, c, d, e, f) in zip(
                climatezones, housetypes, constructionyears, rennovationdegrees,
                season_and_day
            )
        ],
        names=["ClimateZones", "HouseTypes", "ConstructionYear", "RennovationDegree", "SeasonAndDay"],
    )

    # convert from l to kWh
    for index in results.index:
        if index[1] in ["Oil [l]", "Diesel [l]"]:
            results.loc[index, :] *= 10
    # rename [l] to [kWh]
    old_index_level = results.index
    new_index_level = [
        (index[0], index[1].replace("[l]", "[kWh]")) for index in old_index_level
    ]
    results.index = pd.MultiIndex.from_tuples(
        tuples=new_index_level, names=results.index.names
    )

    # return only relevant data for ESM guys - skip building validation data from row 18 - 20
    relevant_rows = list(range(20))
    if len(results.index) > 20:
        # also keep the row for building area if it is included in the data
        relevant_rows += [23, 24, 25]
    return results.loc[results.index[relevant_rows]]


def collect_dataframes(result_folder: str, filename: str) -> List[Tuple[pd.DataFrame, Dict]]:
    all_result_directories = os.listdir(result_folder)
    results: List[Tuple[pd.DataFrame, Dict]] = []
    # load the dataframe from each subdirectory
    folders_without_results = 0
    for result_directory in tqdm.tqdm(all_result_directories):
        result_path = os.path.join(result_folder, result_directory)
        if not os.path.isdir(result_path):
            # not a folder - skip
            continue
        config_file_path = os.path.join(result_path, "hisim_config.json")
        config = sensitivity_plots.load_hisim_config(config_file_path)

        result_file_path = os.path.join(
            result_path, f"{filename}.csv"
        )
        if not os.path.isfile(result_file_path):
            # skip this folder if the result file is missing
            folders_without_results += 1
            continue
        result_data = pd.read_csv(result_file_path, index_col=[0, 1], header=[0])
        results.append((result_data, config))
    print(
        f"{folders_without_results} folders did not contain the csv_for_housing_data_base_annual.csv file."
    )
    return results


def combine_building_code_primes(result_folder: str):
    """
    Combines all csv_for_housing_data_base.csv files from the result folders
    in the specified location into a single csv file, in the format needed for
    the ESM primes

    :param result_folder: the parent directory of the result folders
    :type result_folder: str
    """
    results = collect_dataframes(result_folder, "csv_for_housing_data_base_annual")
    columns = {}
    for result_data, config in results:
        result_data_column = result_data.iloc[:, 0]
        column_name = (
            config["archetype_config_"]["building_code"]
        )
        columns[column_name] = result_data_column

    # concatenate all columns to a single dataframe and save it as a file
    combined_results = pd.concat(columns, axis=1)
    combined_results = modify_dataframe(results=combined_results)
    combined_results.to_csv(
        os.path.join(result_folder, "database_for_PRIMES.csv"), sep=COLUMN_SEP, decimal=DECIMAL_SEP
    )


def combine_building_code_TIAM_ECN(result_folder:str) -> None:
    """" Merges tables with values for Day/Night Summer/Winter/Intermediate to one single file."""
    results = collect_dataframes(result_folder, "csv_for_housing_data_base_seasonal")
    columns = {}
    for result_data, config in results:
        for column in result_data.columns:
            result_data_column = result_data[column]
            rowname = (
                config["archetype_config_"]["building_code"]
                + "_" + column
            )
            columns[rowname] = result_data_column

    # concatenate all columns to a single dataframe and save it as a file
    combined_results = pd.concat(columns, axis=1)
    combined_results = modify_dataframe(results=combined_results)
    combined_results.to_csv(
        os.path.join(result_folder, "database_for_TIAM.csv"), sep=COLUMN_SEP, decimal=DECIMAL_SEP
    ) 


def combine_ESM_databases(result_folder: str, filename: str, decimals: int = -1):
    """
    Merges the ESM tables created by the function combine_building_code_results
    for each heating system into a single table

    :param result_folder: the result folder containing the individual tables, each in
                          a separate subdirectory with the name of the heating system
    :type result_folder: str
    :param filename: the name of the files to combine
    :type filename: str
    :param decimals: if > 0, all values are rounded to the specified number of decimal
                     digits; defaults to -1
    :type decimals: int, optional
    """
    # extract only the child directories (no files)
    subdirectories = next(os.walk(result_folder))[1]

    # map the heating systems to the respective row names in the tables
    heating_system_row_mapping = {
        "HeatPump": "Electricity - HeatPump [kWh]",
        "ElectricHeating": "Electricity [kWh]",
        "OilHeating": "Oil [kWh]",
        "GasHeating": "Gas [kWh]",
        "DistrictHeating": "Distributed Stream [kWh]",
    }

    merged_tables: Optional[pd.DataFrame] = None
    for i, heating_system in enumerate(subdirectories):
        if heating_system not in heating_system_row_mapping:
            print(f"Skipped the following subdirectory: '{heating_system}'")
            continue
        filepath = os.path.join(result_folder, heating_system, f"{filename}.csv")
        assert os.path.isfile(
            filepath
        ), f"The file for heating system '{heating_system}' was not found: {filepath}"
        if i == 0:
            # read the first table
            merged_tables = pd.read_csv(
                filepath, header=[0, 1, 2, 3, 4], index_col=[0, 1], sep=COLUMN_SEP, decimal=DECIMAL_SEP
            )
        else:
            # read the next table and replace the rows in the merged dataframe
            assert merged_tables is not None
            new_table = pd.read_csv(
                filepath, header=[0, 1, 2, 3, 4], index_col=[0, 1], sep=COLUMN_SEP, decimal=DECIMAL_SEP
            )
            assert (
                heating_system in heating_system_row_mapping
            ), f"Invalid subdirectory name: {heating_system}"
            row_name = heating_system_row_mapping[heating_system]
            merged_tables.loc[("WaterHeating", row_name)] = new_table.loc[  # type: ignore
                ("WaterHeating", row_name)
            ]
            merged_tables.loc[("SpaceHeating", row_name)] = new_table.loc[  # type: ignore
                ("SpaceHeating", row_name)
            ]
    assert merged_tables is not None
    path = os.path.join(result_folder, f"{filename}_merged.csv")
    merged_tables = merged_tables.loc[:, ~merged_tables.columns.duplicated()]  # type: ignore
    if decimals > 0:
        merged_tables = merged_tables.round(decimals)
    merged_tables.to_csv(path, sep=COLUMN_SEP, decimal=DECIMAL_SEP)


def main():
    """Main execution function."""
    heating_systems = [
        "HeatPump",
        "ElectricHeating",
        "OilHeating",
        "GasHeating",
        "DistrictHeating",
    ]
    result_base_folder = "./results/hisim_building_code_calculations/"
    # calculate the database_for_ESM table for each heating system
    for heating_system in heating_systems:
        print(f"Creating ESM tables for {heating_system}")

        result_folder = os.path.join(result_base_folder, heating_system)
        combine_building_code_primes(result_folder)
        combine_building_code_TIAM_ECN(result_folder)

    # combine the tables into a single table
    combine_ESM_databases(result_base_folder, "database_for_PRIMES", decimals=3)
    combine_ESM_databases(result_base_folder, "database_for_TIAM", decimals=3)


if __name__ == "__main__":
    main()
