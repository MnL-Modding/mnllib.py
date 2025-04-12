import hashlib
import os
import typing

from ..utils import stream_or_open_file
from ..n3ds.misc import N3DSRegion


type DTVersion = typing.Literal["1.0", "1.1"]
type DTVersionPair = tuple[N3DSRegion, DTVersion]


def determine_version_from_code_bin(
    code_bin: typing.BinaryIO | str | os.PathLike[str],
) -> DTVersionPair:
    with stream_or_open_file(code_bin, "rb") as code_bin:
        code_bin.seek(0)
        match hashlib.sha256(code_bin.read(256)).hexdigest():
            case "9bff1e997bcd957743fc8d8fd44ff2b82aa0785a814c4f2a94afe2427c7a0164":
                return ("E", "1.0")
            case "5e7c239b8bca10d6e762ed38b0354f931c3f3b086bc0f7c2721b2da9ab31dca2":
                return ("E", "1.1")
            case "5faf04a224aeb0aaa96d7d005af15dac795347eb6f237855a01df3ab7cf62a87":
                return ("P", "1.0")
            case "f67913aaeb11ce8b36e49d052fdfd31e77148c4e4e1ac2b8bd48edebb27b7f73":
                return ("P", "1.1")
            case "af4ce922c4acebeffa0544901a996738fbef3f437aa932f2d39903ffc2039974":
                return ("J", "1.0")
            case "ad9dd9e7c1ba76c20019ad1d8aa4164061c67c3ff1f51c9eeecf5cef795f72c7":
                return ("J", "1.1")
            case "a206ea8e1132fa332b0c0ce2237bd00986415d02948b31eddec6890531076816":
                return ("K", "1.0")
            case digest:
                raise ValueError(
                    "unknown region/version of the game with "
                    f"SHA-256 of the first 256 bytes of 'code.bin': {digest}"
                )
