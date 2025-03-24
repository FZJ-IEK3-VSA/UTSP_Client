"""
Helper functions for creating requests for the LPG
"""

import inspect
import random
from typing import Dict, List, Optional
from utspclient.helpers import lpgdata
from utspclient.helpers.lpgpythonbindings import (
    CalcOption,
    EnergyIntensityType,
    HouseCreationAndCalculationJob,
    HouseData,
    HouseholdData,
    HouseholdDataSpecificationType,
    HouseholdNameSpecification,
    HouseholdTemplateSpecification,
    JsonReference,
)


def collect_lpg_households() -> Dict[str, JsonReference]:
    """
    Collects the JsonReferences of all predefined LPG household
    """
    members = inspect.getmembers(lpgdata.Households)
    predefined_households = {
        name: value for name, value in members if isinstance(value, JsonReference)
    }
    return predefined_households


def create_default_house_data() -> HouseData:
    """
    Creates a HouseData object with default values

    :return: a HouseData object that can be inserted into an LPG simulation config
    :rtype: HouseData
    """
    house_data = lpgdata.HouseData()
    house_data.Name = "House"
    house_data.HouseGuid = lpgdata.StrGuid("houseguid")
    house_data.HouseTypeCode = (
        lpgdata.HouseTypes.HT01_House_with_a_10kWh_Battery_and_a_fuel_cell_battery_charger_5_MWh_yearly_space_heating_gas_heating
    )
    house_data.TargetCoolingDemand = 10000
    house_data.TargetHeatDemand = 0
    house_data.Households = []
    return house_data


def create_hh_data_from_number_and_size(
    number_of_households: int, people_per_household: int
) -> List[HouseholdData]:
    """
    Creates a list of HouseholdData objects that can be added to a HouseData object in an LPG simulation config

    :param number_of_households: the number of households to create
    :type number_of_households: int
    :param people_per_household: the number of people per household
    :type people_per_household: int
    :return: the list of HouseholdsData objects
    :rtype: List[HouseholdData]
    """
    households = []
    for _ in range(number_of_households):
        hh_data: lpgdata.HouseholdData = lpgdata.HouseholdData()
        hh_data.HouseholdDataSpecification = (
            lpgdata.HouseholdDataSpecificationType.ByPersons
        )
        hh_data.HouseholdDataPersonSpec = lpgdata.HouseholdDataPersonSpecification()
        hh_data.HouseholdDataPersonSpec.Persons = []
        hh_data.ChargingStationSet = (
            lpgdata.ChargingStationSets.Charging_At_Home_with_03_7_kW_output_results_to_Car_Electricity
        )
        hh_data.TravelRouteSet = (
            lpgdata.TravelRouteSets.Travel_Route_Set_for_30km_Commuting_Distance
        )
        hh_data.TransportationDeviceSet = (
            lpgdata.TransportationDeviceSets.Bus_and_two_30_km_h_Cars
        )
        for person_idx in range(people_per_household):
            if person_idx % 2 == 0:
                gender = lpgdata.Gender.Male
            else:
                gender = lpgdata.Gender.Female
            age = 100 * random.random()

            persondata = lpgdata.PersonData(int(age), gender)
            hh_data.HouseholdDataPersonSpec.Persons.append(persondata)
            households.append(hh_data)
    return households


def create_empty_calcspec(
    housetype: str,
    startdate: Optional[str] = None,
    enddate: Optional[str] = None,
    external_resolution: Optional[str] = None,
    geographic_location: Optional[JsonReference] = None,
    energy_intensity: EnergyIntensityType = EnergyIntensityType.Random,
    calc_options: Optional[List[CalcOption]] = None,
) -> HouseCreationAndCalculationJob:
    """
    Creates a basic LPG calculation specification from the most relevant parameters,
    using a default configuration for everything else.
    Does not include any households yet
    """
    config = HouseCreationAndCalculationJob()

    # Set house data
    config.House = create_default_house_data()
    config.House.HouseTypeCode = housetype

    # Set general calculation parameters
    config.CalcSpec = lpgdata.JsonCalcSpecification()
    config.CalcSpec.LoadTypePriority = lpgdata.LoadTypePriority.All
    config.CalcSpec.RandomSeed = -1
    config.CalcSpec.EnergyIntensityType = energy_intensity
    config.CalcSpec.StartDate = startdate
    config.CalcSpec.EndDate = enddate
    config.CalcSpec.ExternalTimeResolution = external_resolution
    config.CalcSpec.GeographicLocation = geographic_location
    if calc_options:
        config.CalcSpec.DefaultForOutputFiles = lpgdata.OutputFileDefault.NoFiles
        config.CalcSpec.CalcOptions = calc_options
    else:
        config.CalcSpec.DefaultForOutputFiles = lpgdata.OutputFileDefault.Reasonable
    return config


def create_hhdata_from_name(
    householdref: JsonReference,
    transportation_device_set: Optional[JsonReference] = None,
    travel_route_set: Optional[JsonReference] = None,
    charging_station_set: Optional[JsonReference] = None,
) -> HouseholdData:
    """
    Creates a basic HouseholdData object from a household reference.
    This object can then be added to a LPG CalcSpec.
    """
    hhnamespec = HouseholdNameSpecification(householdref)
    hhdata = HouseholdData(
        None,
        None,
        hhnamespec,
        "hhid",
        "hhname",
        HouseholdDataSpecification=HouseholdDataSpecificationType.ByHouseholdName,
        TransportationDeviceSet=transportation_device_set,
        TravelRouteSet=travel_route_set,
        ChargingStationSet=charging_station_set,
    )
    return hhdata


def create_hhdata_from_template(
    hh_template: str,
    transportation_device_set: Optional[JsonReference] = None,
    travel_route_set: Optional[JsonReference] = None,
    charging_station_set: Optional[JsonReference] = None,
) -> HouseholdData:
    """
    Creates a basic HouseholdData object from a household template name.
    This object can then be added to a LPG CalcSpec.
    """
    template_spec = HouseholdTemplateSpecification(HouseholdTemplateName=hh_template)
    hhdata = HouseholdData(
        None,
        template_spec,
        None,
        "hhid",
        "hhname",
        HouseholdDataSpecification=HouseholdDataSpecificationType.ByTemplateName,
        TransportationDeviceSet=transportation_device_set,
        TravelRouteSet=travel_route_set,
        ChargingStationSet=charging_station_set,
    )
    return hhdata


def create_basic_lpg_config(
    householdref: JsonReference,
    housetype: str,
    startdate: Optional[str] = None,
    enddate: Optional[str] = None,
    external_resolution: Optional[str] = None,
    geographic_location: Optional[JsonReference] = None,
    energy_intensity: EnergyIntensityType = EnergyIntensityType.Random,
    transportation_device_set: Optional[JsonReference] = None,
    travel_route_set: Optional[JsonReference] = None,
    charging_station_set: Optional[JsonReference] = None,
    calc_options: Optional[List[CalcOption]] = None,
) -> HouseCreationAndCalculationJob:
    """
    Creates a basic LPG request for a single household from the most relevant parameters, using a default
    configuration for everything else.
    """
    config = create_empty_calcspec(
        housetype,
        startdate,
        enddate,
        external_resolution,
        geographic_location,
        energy_intensity,
        calc_options,
    )
    hhdata = create_hhdata_from_name(
        householdref, transportation_device_set, travel_route_set, charging_station_set
    )
    if transportation_device_set or travel_route_set or charging_station_set:
        config.CalcSpec.EnableTransportation = True  # type: ignore
    assert config.House is not None
    config.House.Households.append(hhdata)
    return config
