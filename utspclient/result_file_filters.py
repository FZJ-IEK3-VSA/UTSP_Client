"""
This module defines relevant output files for typical use cases to avoid transmitting
and storing unneeded files
"""

from typing import Dict
from utspclient.datastructures import ResultFileRequirement


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

    class Cars:
        _template = "Car {i}, {power}kW Charging Power, avg. Speed {speed} km h"
        CAR1 = _template.format(i=1, power=22, speed=30)
        CAR2 = _template.format(i=2, power=22, speed=30)
        CAR3 = _template.format(i=3, power=22, speed=60)
        CAR4 = _template.format(i=4, power=22, speed=60)
        ALL = [CAR1, CAR2, CAR3, CAR4]

    @staticmethod
    def car_state(car: str) -> str:
        """Result file names for car states"""
        return f"Results/Carstate.{car}.HH1.json"

    @staticmethod
    def all_car_states_optional() -> Dict[str, ResultFileRequirement]:
        """Helper function to get any created car state file."""
        return {
            LPGFilters.car_state(c): ResultFileRequirement.OPTIONAL
            for c in LPGFilters.Cars.ALL
        }

    @staticmethod
    def car_location(car: str) -> str:
        """Result file names for car locations"""
        return f"Results/CarLocation.{car}.HH1.json"

    @staticmethod
    def all_car_locations_optional() -> Dict[str, ResultFileRequirement]:
        """Helper function to get any created car location file."""
        return {
            LPGFilters.car_location(c): ResultFileRequirement.OPTIONAL
            for c in LPGFilters.Cars.ALL
        }

    @staticmethod
    def driving_distance(car: str) -> str:
        """Result file names for driving distances"""
        return f"Results/DrivingDistance.{car}.HH1.json"

    @staticmethod
    def all_driving_distances_optional() -> Dict[str, ResultFileRequirement]:
        """Helper function to get any created driving distance file."""
        return {
            LPGFilters.driving_distance(c): ResultFileRequirement.OPTIONAL
            for c in LPGFilters.Cars.ALL
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
