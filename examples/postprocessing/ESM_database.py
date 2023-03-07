import os
import pandas as pd

import sensitivity_plots

def combine_building_code_results(result_folder: str):
    all_result_directories = os.listdir(result_folder)
    frames, rownames = [], []
    # initialize empty data frame
    results = pd.read_csv(os.path.join(result_folder, all_result_directories[0], "csv_for_housing_data_base.csv"), usecols=[0,1])

    for result_directory in all_result_directories:
        result_path = os.path.join(result_folder, result_directory)
        config_file_path = os.path.join(result_path, "hisim_config.json")
        config = sensitivity_plots.load_hisim_config(config_file_path)
        
        result_file_path = os.path.join(result_path, "csv_for_housing_data_base.csv")
        result_data = pd.read_csv(result_file_path)
        result_data_column = result_data['0']
        rowname = config["archetype_config_"]["building_code"] + "-" + config["archetype_config_"]["heating_system_installed"]
        results[rowname] = result_data_column
        frames.append(result_data)
    results.to_csv(os.path.join(result_folder,"database_for_ESM.csv"))
    

def main():
    result_folder = f"./results/hisim_building_code_calculations"
    combine_building_code_results(result_folder)


if __name__ == "__main__":
    main()