"""
Common data structures for communication with the UTSP server.
"""

import base64
import hashlib
from dataclasses import dataclass, field
from enum import Enum
import sys
from typing import Dict, Mapping, Optional
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


@dataclass_json
@dataclass
class ResultDelivery:
    """
    Contains the results for a singe request.
    Can compress/decompress the result file contents to reduce size.
    Can also encode each file using base64 to allow serializing
    objects of this class to json. When encoded, the data member is
    None and the encoded str data is contained in the internal member
    __data_encoded.
    """

    #: the original request the results belong to
    original_request: TimeSeriesRequest
    #: name and content of all result files
    data: dict[str, bytes] | None = field(default_factory=dict)
    is_compressed: bool = False

    def __post_init__(self):
        # separate member for storing base64-encoded data
        self.__data_encoded: dict[str, str] | None = None

    def is_encoded(self) -> bool:
        """
        Checks if the data is currently encoded or not.

        :return: True if the data is encoded, else False
        """
        assert (self.data is None) != (
            self.__data_encoded is None
        ), "Bug in ResultDelivery: both data members were None"
        return self.data is None

    def get_data(self) -> Mapping[str, bytes | str]:
        """
        Returns a reference to the currently active data dict,
        containing encoded or decoded data.

        :return: the data dict
        """
        data = self.__data_encoded if self.is_encoded() else self.data
        assert data is not None, "Bug in ResultDelivery: both data members were None"
        return data

    def size_in_gb(self) -> float:
        """
        Returns the total size of the result data in gigabytes.

        :return: size in gigabytes
        """
        data = self.get_data()
        size = sum(sys.getsizeof(r) for r in data.values())
        return round(size / 1024**3, 2)

    def get_file_count(self) -> int:
        """
        Returns the number of contained files.

        :return: number of files
        """
        return len(self.get_data())

    def compress_data(self):
        """
        Compresses the data to use less storage
        """
        assert not self.is_compressed, "Data is already compressed"
        assert self.data is not None, "Cannot compress encoded data"
        self.data = {k: zlib.compress(v) for k, v in self.data.items()}
        self.is_compressed = True

    def decompress_data(self):
        """
        Decompresses the data.
        """
        assert self.is_compressed, "Data is not compressed"
        assert self.data is not None, "Data has to be decoded before decompression"
        self.data = {k: zlib.decompress(v) for k, v in self.data.items()}
        self.is_compressed = False

    def encode_data(self):
        """
        base64-encode the data for conversion to json.
        """
        assert self.data is not None, "Data is already encoded"
        self.__data_encoded = {
            k: base64.b64encode(b).decode() for k, b in self.data.items()
        }

    def decode_data(self):
        """
        Decode the base64-encoded data
        """
        assert self.__data_encoded is not None, "Data is not encoded"
        self.data = {
            k: base64.b64decode(s.encode()) for k, s in self.__data_encoded.items()
        }


@dataclass_json
@dataclass
class RestReply:
    """Reply from the UTSP server to a single request. Contains all available information about the request."""

    #: compressed result data, if the request finished without an error
    result_delivery: Optional[ResultDelivery] = None
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
