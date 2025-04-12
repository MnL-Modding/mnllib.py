import dataclasses
import struct
import typing
from typing import override


class MnLLibWarning(UserWarning):
    pass


@dataclasses.dataclass
class MnLDataType:
    id: int
    struct_obj: struct.Struct

    def __init__(self, id: int, struct_obj: str | struct.Struct) -> None:
        self.id = id
        self.struct_obj = (
            struct_obj
            if isinstance(struct_obj, struct.Struct)
            else struct.Struct(struct_obj)
        )

    @override
    def __eq__(self, other: object, /) -> bool:
        if self is other:
            return True

        if other.__class__ is self.__class__:
            other = typing.cast(typing.Self, other)
            return (
                self.id == other.id
                and self.struct_obj.format == other.struct_obj.format
            )

        return NotImplemented


def decode_varint(stream: typing.BinaryIO) -> int:
    (data,) = struct.unpack("<B", stream.read(1))
    size = data >> 6
    result = data & 0b00111111
    for i in range(size):
        result |= struct.unpack("<B", stream.read(1))[0] << ((i + 1) * 6)
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
