"""Requests a load profile that is generated using the Load Profile Generator (LPG)"""

# %% imports
import utspclient
from utspclient.helpers.lpgdata import LoadTypes, Households, HouseTypes, CalcOption


def main():
    # %% Create a simulation configuration for the LPG
    simulation_config = utspclient.helpers.lpg_helper.create_basic_lpg_config(
        Households.CHR01_Couple_both_at_Work,
        HouseTypes.HT06_Normal_house_with_15_000_kWh_Heating_Continuous_Flow_Gas_Heating,
        "2020-01-01",
        "2020-01-03",
        "00:15:00",
        calc_options=[CalcOption.SumProfileExternalIndividualHouseholdsAsJson],
    )

    simulation_config_json = simulation_config.to_json(indent=4)  # type: ignore

    # %% Define connection parameters
    ADDRESS = "134.94.131.167:443"
    API_KEY = "OrjpZY93BcNWw8lKaMp0BEchbCc"

    # %% Prepare the time series request
    result_file = utspclient.result_file_filters.LPGFilters.sum_hh1_ext_res(
        LoadTypes.Electricity, 900, json=True
    )
    request = utspclient.datastructures.TimeSeriesRequest(
        simulation_config_json,
        "LPG",
        required_result_files=dict.fromkeys([result_file]),
    )

    # %% Request the time series
    result = utspclient.request_time_series_and_wait_for_delivery(
        ADDRESS, request, api_key=API_KEY
    )

    # %% Decode result data
    file_content = result.data[result_file].decode()
    print(file_content)


if __name__ == "__main__":
    main()
