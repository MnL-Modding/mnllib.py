import enum
import typing
from typing import override

from .misc import MnLDataType


MNL_DEBUG_MESSAGE_ENCODING = "shift_jis"


DEFAULT_DATA_DIR_PATH = "data"


class MnLDataTypes(MnLDataType, enum.Enum):
    @classmethod
    @override
    def _missing_(cls, value: object) -> typing.Self | None:
        if isinstance(value, MnLDataType):
            for member in cls:
                if member == value:
                    return member
        elif isinstance(value, int):
            for member in cls:
                if member.id == value:
                    return member
        return None

    U_BYTE = 0x0, "<B"
    U_SHORT = 0x1, "<H"
    U_INT = 0x2, "<I"
    S_BYTE = 0x3, "<b"
    S_SHORT = 0x4, "<h"
    S_INT = 0x5, "<i"
    FX16 = 0x6, "<h"
    FX32 = 0x7, "<i"
    FLOAT = 0x8, "<f"
