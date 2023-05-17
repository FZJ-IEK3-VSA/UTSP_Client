"""
Common data structures for communication with the UTSP server.
"""

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from dataclasses_json import dataclass_json  # type: ignore


class CalculationStatus(Enum):
    """Indicates the current state of a request"""

    UNKNOWN = 0
    INCALCULATION = 1
    INDATABASE = 2
    CALCULATIONSTARTED = 3
    CALCULATIONFAILED = 4


class ResultFileRequirement(Enum):
    """Determines whether specified result files are required or optional. Only
    when a required file is not created by the provider an error is raised."""

    REQUIRED = 0
    OPTIONAL = 1


@dataclass_json
@dataclass
class TimeSeriesRequest:
    """
    Contains all necessary information for a calculation request.
    It also functions as an identifier for the request, so sending the same object
    again will always return the same results.
    """

    #: provider-specific string defining the requested results
    simulation_config: str
    #: the provider which shall process the request
    providername: str
    #: optional unique identifier, can be used to force recalculation of otherwhise identical requests
    guid: str = ""
    #: Desired files created by the provider that are sent back as result. Throws an error if one of these files is not
    #: created. If left empty all created files are returned.
    required_result_files: Dict[str, Optional[ResultFileRequirement]] = field(default_factory=dict)  # type: ignore
    #: Names and contents of additional input files to be created in the provider container, if required. For internal
    #: reasons the 'bytes' type cannot be used here, so the file contents are stored base64-encoded.
    input_files: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.required_result_files, dict):
            raise RuntimeError(
                "Invalid TimeSeriesRequest: the required_result_files attribute must be a dict"
            )
        if not isinstance(self.input_files, dict):
            raise RuntimeError(
                "Invalid TimeSeriesRequest: the input_files attribute must be a dict"
            )

    def get_hash(self) -> str:
        """
        Calculates a hash for this object. This is used to distinguish different
        requests.

        :return: the hash of this object
        :rtype: str
        """
        # hash the json representation of the object
        data = self.to_json().encode("utf-8")  # type: ignore
        return hashlib.sha256(data).hexdigest()


@dataclass_json
@dataclass
class ResultDelivery:
    """Contains the results for a singe request"""

    #: the original request the results belong to
    original_request: TimeSeriesRequest
    #: Names and contents of all result files
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        for key, value in self.data.items():
            if isinstance(value, List):
                # bytes are stored as a list in json; convert it back
                self.data[key] = bytes(value)


@dataclass_json
@dataclass
class RestReply:
    """Reply from the UTSP server to a single request. Contains all available information about the request."""

    #: compressed result data, if the request finished without an error
    result_delivery: Optional[bytes] = None
    #: current status of the request
    status: CalculationStatus = CalculationStatus.UNKNOWN
    #: hash of the original request which this reply belongs to
    request_hash: str = ""
    #: optional information, or an error message if the request failed
    info: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.status, int):
            # convert status from int to enum
            self.status = CalculationStatus(self.status)
        if isinstance(self.result_delivery, List):
            # bytes are stored as a list in json; convert it back
            self.result_delivery = bytes(self.result_delivery)
