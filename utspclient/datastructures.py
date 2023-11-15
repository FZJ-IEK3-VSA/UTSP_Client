"""
Common data structures for communication between the UTSP server
and the client.
"""

import abc
import base64
import hashlib
from dataclasses import dataclass, field
from enum import Enum
import sys
from typing import Dict, Optional
import zlib

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


@dataclass
class ResultDeliveryBase(abc.ABC):
    """
    Base class for the results for a singe request.
    """

    #: the original request the results belong to
    original_request: TimeSeriesRequest
    #: name and content of all result files
    data: dict = field(default_factory=dict)

    def size_in_gb(self) -> float:
        """
        Returns the total size of the result data in gigabytes.

        :return: size in gigabytes
        """
        size = sum(sys.getsizeof(r) for r in self.data.values())
        return round(size / 1024**3, 2)

    def get_file_count(self) -> int:
        """
        Returns the number of contained files.

        :return: number of files
        """
        return len(self.data)


@dataclass
class ResultDelivery(ResultDeliveryBase):
    """
    Contains the results for a singe request.
    Can compress/decompress the result file contents to reduce size.
    Should not be serialized to json due to the bytes in the data
    member. For that purpose, the object can be encoded to a
    EncodedResultDelivery object first.
    """

    #: name and content of all result files
    data: dict[str, bytes] = field(default_factory=dict)
    is_compressed: bool = False

    def compress_data(self):
        """
        Compresses the data to use less storage
        """
        assert not self.is_compressed, "Data is already compressed"
        self.data = {k: zlib.compress(v) for k, v in self.data.items()}
        self.is_compressed = True

    def decompress_data(self):
        """
        Decompresses the data.
        """
        assert self.is_compressed, "Data is not compressed"
        self.data = {k: zlib.decompress(v) for k, v in self.data.items()}
        self.is_compressed = False

    def encode_data(self):
        """
        base64-encode the data for conversion to json.
        """
        data = {k: base64.b64encode(b).decode() for k, b in self.data.items()}
        return EncodedResultDelivery(self.original_request, data, self.is_compressed)


@dataclass_json
@dataclass
class EncodedResultDelivery(ResultDeliveryBase):
    """
    Contains encoded result data for a singe request.
    Can be decoded back to a ResultDelivery object.
    """

    #: name and content of all result files
    data: dict[str, str] = field(default_factory=dict)
    is_compressed: bool = False

    def decode_data(self) -> ResultDelivery:
        """
        Decode the base64-encoded data
        """
        data = {k: base64.b64decode(s.encode()) for k, s in self.data.items()}
        return ResultDelivery(self.original_request, data, self.is_compressed)


@dataclass_json
@dataclass
class RestReply:
    """Reply from the UTSP server to a single request. Contains all available information about the request."""

    #: compressed result data, if the request finished without an error
    result_delivery: Optional[EncodedResultDelivery] = None
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
