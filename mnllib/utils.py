from __future__ import annotations

import builtins
import contextlib
import enum
import io
import os
import struct
import typing
from typing import override

if typing.TYPE_CHECKING:
    import _typeshed


type _Opener = typing.Callable[[str, int], int]


class VariableRangeEnum(enum.IntEnum):
    range: range

    def __new__(cls, value: builtins.range | int) -> typing.Self:
        if isinstance(value, int):
            value = range(value, (value | 0x0FFF) + 1)
        obj = int.__new__(cls, value.start)
        obj._value_ = value.start
        obj.range = value
        return obj

    @classmethod
    @override
    def _missing_(cls, value: object) -> typing.Self | None:
        if isinstance(value, range):
            for member in cls:
                if member.range == value:
                    return member
        elif isinstance(value, int):
            for member in cls:
                if value in member.range:
                    return member
        return None


@typing.overload
def stream_or_open_file[T: io.TextIOWrapper](
    file: T | _typeshed.FileDescriptorOrPath,
    mode: _typeshed.OpenTextMode = "r",
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> io.TextIOWrapper | contextlib.nullcontext[T]: ...
@typing.overload
def stream_or_open_file[T: io.FileIO](
    file: T | _typeshed.FileDescriptorOrPath,
    mode: _typeshed.OpenBinaryMode,
    buffering: typing.Literal[0],
    encoding: None = None,
    errors: None = None,
    newline: None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> io.FileIO | contextlib.nullcontext[T]: ...
@typing.overload
def stream_or_open_file[T: io.BufferedRandom](
    file: T | _typeshed.FileDescriptorOrPath,
    mode: _typeshed.OpenBinaryModeUpdating,
    buffering: typing.Literal[-1, 1] = -1,
    encoding: None = None,
    errors: None = None,
    newline: None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> io.BufferedRandom | contextlib.nullcontext[T]: ...
@typing.overload
def stream_or_open_file[T: io.BufferedWriter](
    file: T | _typeshed.FileDescriptorOrPath,
    mode: _typeshed.OpenBinaryModeWriting,
    buffering: typing.Literal[-1, 1] = -1,
    encoding: None = None,
    errors: None = None,
    newline: None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> io.BufferedWriter | contextlib.nullcontext[T]: ...
@typing.overload
def stream_or_open_file[T: io.BufferedReader](
    file: T | _typeshed.FileDescriptorOrPath,
    mode: _typeshed.OpenBinaryModeReading,
    buffering: typing.Literal[-1, 1] = -1,
    encoding: None = None,
    errors: None = None,
    newline: None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> io.BufferedReader | contextlib.nullcontext[T]: ...
@typing.overload
def stream_or_open_file[T: typing.BinaryIO](
    file: T | _typeshed.FileDescriptorOrPath,
    mode: _typeshed.OpenBinaryMode,
    buffering: int = -1,
    encoding: None = None,
    errors: None = None,
    newline: None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> typing.BinaryIO | contextlib.nullcontext[T]: ...
@typing.overload
def stream_or_open_file[T: typing.IO[typing.Any]](
    file: T | _typeshed.FileDescriptorOrPath,
    mode: str,
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> typing.IO[typing.Any] | contextlib.nullcontext[T]: ...


def stream_or_open_file[T: typing.IO[typing.Any]](
    file: T | _typeshed.FileDescriptorOrPath,
    *args: typing.Any,
    **kwargs: typing.Any,
) -> typing.IO[typing.Any] | contextlib.nullcontext[T]:
    if isinstance(file, (int, str, bytes, os.PathLike)):
        return open(file, *args, **kwargs)  # pyright: ignore[reportUnknownVariableType]
    else:
        return contextlib.nullcontext(file)


def read_length_prefixed_array(
    stream: typing.BinaryIO,
    element_format: str | struct.Struct,
    length_format: str | struct.Struct = struct.Struct("<I"),
    *,
    length_in_bytes: bool = False,
) -> list[typing.Any]:
    if not isinstance(element_format, struct.Struct):
        element_format = struct.Struct(element_format)
    if not isinstance(length_format, struct.Struct):
        length_format = struct.Struct(length_format)

    (length,) = length_format.unpack(stream.read(length_format.size))
    elements: list[typing.Any | tuple[typing.Any, ...]] = []
    for element in element_format.iter_unpack(
        stream.read(
            element_format.size * length
            if not length_in_bytes
            else length - length_format.size
        )
    ):
        if len(element) == 1:
            element = element[0]
        elements.append(element)
    return elements
