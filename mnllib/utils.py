import struct
import typing


def read_length_prefixed_array(
    stream: typing.BinaryIO,
    element_format: str | struct.Struct,
    length_format: str | struct.Struct = struct.Struct("<I"),
) -> list[typing.Any]:
    if not isinstance(element_format, struct.Struct):
        element_format = struct.Struct(element_format)
    if not isinstance(length_format, struct.Struct):
        length_format = struct.Struct(length_format)

    (length,) = length_format.unpack(stream.read(length_format.size))
    elements: list[typing.Any | tuple[typing.Any, ...]] = []
    for element in element_format.iter_unpack(
        stream.read(element_format.size * length)
    ):
        if len(element) == 1:
            element = element[0]
        elements.append(element)
    return elements
