import os
import pandas as pd
import tqdm

import sensitivity_plots

def modify_dataframe(results: pd.DataFrame) -> pd.DataFrame:
    
    # extract header
    headerlist = results.columns

    # extract relevant information for Multi-Index
    tabulaname = ["TabulaName", "str"] + headerlist[3:]
    climatezones = ["ClimateZone", "str"] + [elem.split(".")[0] for elem in headerlist[3:] ]
    housetypes = ["House Type", "str"] + [elem.split(".")[2] for elem in headerlist[3:] ]
    constructionyears = ["Construction Year", "str"] + [elem.split(".")[3] for elem in headerlist[3:]]
    rennovationdegrees = ["Rennovation Degree", "str"] + [elem.split(".")[7][:3] for elem in headerlist[3:] ]

    # make multiindex
    results.columns = pd.MultiIndex.from_tuples([(b, c, d, e) for (b, c, d, e) in zip(climatezones, housetypes, constructionyears, rennovationdegrees)],
                                            names=["ClimateZones", "HouseTypes", "ConstructionYear", "RennovationDegree"])

    # convert from l to kWh
    

    # return only relevant data for ESM guys
    return results.loc[[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 21]]


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
            result_folder, all_result_directories[0], "csv_for_housing_data_base.csv"
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

        result_file_path = os.path.join(result_path, "csv_for_housing_data_base.csv")
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
        f"{folders_without_results} folders did not contain the csv_for_housing_data_base.csv file."
    )

    # concatenate all columns to a single dataframe and save it as a file
    results = pd.concat(columns, axis=1)
    results.to_csv(os.path.join(result_folder, "database_for_ESM.csv"))


def main():
    result_folder = f"./results/hisim_sensitivity_analysis"
    combine_building_code_results(result_folder)


if __name__ == "__main__":
    main()
