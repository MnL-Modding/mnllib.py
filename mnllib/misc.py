from __future__ import annotations

import abc
import struct
import typing

if typing.TYPE_CHECKING:
    from .managers import MnLScriptManager


class MnLLibWarning(UserWarning):
    pass


class FEventChunk(abc.ABC):
    @abc.abstractmethod
    def to_bytes(self, manager: MnLScriptManager) -> bytes:
        pass


def decode_varint(stream: typing.BinaryIO) -> int:
    (data,) = struct.unpack("<B", stream.read(1))
    size = data >> 6
    result = data & 0b00111111
    for i in range(size):
        result |= struct.unpack("<B", stream.read(1))[0] << (i + 1) * 6
    return result


def encode_varint(value: int) -> bytearray:
    result = bytearray([value & 0b00111111])
    value >>= 6
    while value > 255:
        result.append(value & 0xFF)
        result[0] += 1 << 6
        value >>= 6
    if value > 0:
        result.append(value)
        result[0] += 1 << 6
    return result


def parse_fevent_chunk(
    manager: MnLScriptManager, data: bytes, index: int | None = None
) -> FEventChunk | None:
    from .script import FEventScript
    from .text import LanguageTable

    if len(data) == 0:
        return None
    elif struct.unpack_from("<I", data)[0] == 0x128:
        return LanguageTable.from_bytes(data, is_dialog=True, index=index)
    else:
        return FEventScript.from_bytes(manager, data, index)
