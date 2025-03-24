"""
This module defines relevant output files for typical use cases to avoid transmitting
and storing unneeded files
"""

from typing import Dict
from utspclient.datastructures import ResultFileRequirement
from utspclient.helpers.lpgpythonbindings import JsonReference
from utspclient.helpers import lpgdata


class LPGFilters:
    """
    Provides result file names for the LPG
    """

    @staticmethod
    def sum_hh1(load_type: str, json: bool = False, no_flex: bool = False) -> str:
        """Returns the file name of the sum load profile for the first simulated household, for the
        specified load type"""
        if json:
            flex = ".NoFlexDevices" if no_flex else ""
            return "Results/Sum{flex}.{load_type}.HH1.json".format(
                load_type=load_type, flex=flex
            )
        else:
            flex = ".NoFlex" if no_flex else ""
            return "Results/SumProfiles{flex}.HH1.{load_type}.csv".format(
                load_type=load_type, flex=flex
            )

    @staticmethod
    def sum_hh1_ext_res(
        load_type: str, resolution_in_s: int, json: bool = False
    ) -> str:
        """Returns the file name of the sum load profile for the first simulated household, for the
        specified load type, in the external resolution. The resolution specified here must match the
        external resolution specified in the LPG request."""
        assert resolution_in_s != 60, (
            "The external resolution must not be 60s when using this file name, ",
            "because that is the internal resolution of the LPG and extra files for external resolution are not created. ",
            "Use the filename for the internal resolution files instead.",
        )
        ext = "json" if json else "csv"
        return "Results/SumProfiles_{resolution_in_s}s.HH1.{load_type}.{ext}".format(
            load_type=load_type, resolution_in_s=resolution_in_s, ext=ext
        )

    @staticmethod
    def _get_all_transport_devices() -> list[JsonReference]:
        """Returns a list of all transportation devices in the LPG"""
        return [
            getattr(lpgdata.TransportationDevices, d)
            for d in dir(lpgdata.TransportationDevices)
            if not d.startswith("__")
        ]

    @staticmethod
    def _get_all_car_names() -> list[str]:
        """Returns a list of all cars in the LPG"""
        return [
            LPGFilters._get_car_name_for_file(d)
            for d in LPGFilters._get_all_transport_devices()
            if d.Name and d.Name.startswith("Car ")
        ]

    @staticmethod
    def _get_car_name_for_file(car: JsonReference | str) -> str:
        """Returns the name of the car as used for the result file name"""
        if isinstance(car, JsonReference):
            assert car.Name, "Invalid car reference"
            name = car.Name
        else:
            name = car
        return name.replace("/", " ")

    @staticmethod
    def car_state(car: JsonReference | str) -> str:
        """Result file names for car states"""
        name = LPGFilters._get_car_name_for_file(car)
        return f"Results/Carstate.{name}.HH1.json"

    @staticmethod
    def all_car_states_optional() -> Dict[str, ResultFileRequirement]:
        """Helper function to get any created car state file."""
        return {
            LPGFilters.car_state(c): ResultFileRequirement.OPTIONAL
            for c in LPGFilters._get_all_car_names()
        }

    @staticmethod
    def car_location(car: JsonReference | str) -> str:
        """Result file names for car locations"""
        name = LPGFilters._get_car_name_for_file(car)
        return f"Results/CarLocation.{name}.HH1.json"

    @staticmethod
    def all_car_locations_optional() -> Dict[str, ResultFileRequirement]:
        """Helper function to get any created car location file."""
        return {
            LPGFilters.car_location(c): ResultFileRequirement.OPTIONAL
            for c in LPGFilters._get_all_car_names()
        }

    @staticmethod
    def driving_distance(car: JsonReference | str) -> str:
        """Result file names for driving distances"""
        name = LPGFilters._get_car_name_for_file(car)
        return f"Results/DrivingDistance.{name}.HH1.json"

    @staticmethod
    def all_driving_distances_optional() -> Dict[str, ResultFileRequirement]:
        """Helper function to get any created driving distance file."""
        return {
            LPGFilters.driving_distance(c): ResultFileRequirement.OPTIONAL
            for c in LPGFilters._get_all_car_names()
        }

    class BodilyActivity:
        """Result file names for bodily activity"""

        _template = "Results/BodilyActivityLevel.{level}.HH1.json"
        HIGH = _template.format(level="High")
        LOW = _template.format(level="Low")
        OUTSIDE = _template.format(level="Outside")
        UNKNOWN = _template.format(level="Unknown")

    FLEXIBILITY_EVENTS = "Reports/FlexibilityEvents.HH1.json"


class HiSimFilters:
    RESIDENCE_BUILDING = "Residence_Building.csv"
