import struct
import typing


class MnLLibWarning(UserWarning):
    pass


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
