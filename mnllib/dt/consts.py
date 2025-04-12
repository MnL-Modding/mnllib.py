import enum
import types
import warnings

from ..misc import MnLLibWarning
from .misc import DTVersionPair


SCRIPT_ALIGNMENT = 4


FEVENT_PATH = "FEvent/FEvent.dat"
FEVENT_COMMAND_METADATA_TABLE_ADDRESS: dict[DTVersionPair, int] = {
    ("E", "1.0"): 0x5739DB,
    ("E", "1.1"): 0x5739DB,
    ("P", "1.0"): 0x574A53,
    ("P", "1.1"): 0x573A53,
    ("J", "1.0"): 0x57376B,
    ("J", "1.1"): 0x57376B,
    ("K", "1.0"): 0x573B13,
}
FEVENT_NUMBER_OF_COMMANDS = 0x025D
FEVENT_OFFSET_TABLE_LENGTH_ADDRESS: dict[DTVersionPair, int] = {
    ("E", "1.0"): 0x57AF04,
    ("E", "1.1"): 0x57AF04,
    ("P", "1.0"): 0x57BF7C,
    ("P", "1.1"): 0x57AF7C,
    ("J", "1.0"): 0x57AC94,
    ("J", "1.1"): 0x57AC94,
    ("K", "1.0"): 0x57B03C,
}

FMES_NUMBER_OF_CHUNKS = 0x317

MESSAGE_DIR_PATH = "Message"
SOUND_DATA_PATH = "Sound/SoundData.arc"


def message_header_padding(language: str) -> bytes:
    match language:
        case "US_English":
            return bytes.fromhex("10 00 00 00 00 00 A0 5C 10 00")
        case _ if language.startswith("US_"):
            return bytes.fromhex("10 00 00 00 00 00 18 3C C8 00")
        case _ if language.startswith("EU_"):
            return bytes.fromhex("60 00 00 00 00 00 18 3C D8 00")
        case "JP_Japanese":
            return bytes.fromhex("41 00 00 1C 30 01 9C F9 39 00")
        case "KR_Korean":
            return bytes.fromhex("10 00 00 00 00 00 18 3C EF 00")
        case _:
            warnings.warn(
                f"Unknown language '{language}', using null byte header padding!",
                MnLLibWarning,
            )
            return b"\x00" * 10


def message_footer_padding(language: str) -> bytes:
    match language:
        case "US_English":
            return bytes.fromhex("C0 2E 10 00 98 5C 10 00 34 F7 40 00 DD 14 06")
        case _ if language.startswith("US_"):
            return bytes.fromhex("C0 2E 10 00 10 3C C8 00 34 F7 40 00 DD 14 06")
        case _ if language.startswith("EU_"):
            return bytes.fromhex("C0 2E 60 00 10 3C D8 00 F4 F9 3A 00 DD 14 AA")
        case "JP_Japanese":
            return bytes.fromhex("80 F7 39 00 4E 2F 75 00 6C F7 39 00 FE 1D 30")
        case "KR_Korean":
            return bytes.fromhex("58 2E 10 00 10 3C EF 00 8C F5 37 00 DD 14 6B")
        case _:
            warnings.warn(
                f"Unknown language '{language}', using null byte footer padding!",
                MnLLibWarning,
            )
            return b"\x00" * 15


MESSAGE_WIDTH_AUTO = 0
MESSAGE_HEIGHT_AUTO = 0x04


class MessageStyle(enum.IntEnum):
    NO_BACKGROUND = 0x00000000
    NORMAL = 0x00000001
    SHOUTING = 0x00000002
    SYSTEM = 0x00000003


DEFAULT_MESSAGE_ATTRIBUTES = types.MappingProxyType(
    {"width": MESSAGE_WIDTH_AUTO, "height": MESSAGE_HEIGHT_AUTO}
)
DEFAULT_MESSAGE_STYLE = MessageStyle.NORMAL


class SpecialCharacter(enum.StrEnum):
    A = "\ue000"
    B = "\ue001"
    X = "\ue002"
    Y = "\ue003"
    L = "\ue004"
    R = "\ue005"
    DPAD = "\ue006"
    HOME = "\ue073"


class MessageAlignment(enum.IntEnum):
    LEFT = 0x0
    CENTER = 0x1
    RIGHT = 0x2
    RESET = 0x4
