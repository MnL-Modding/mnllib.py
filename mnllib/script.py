from __future__ import annotations

import abc
import functools
import math
import os
import struct
import io
import typing
from typing import override

from .consts import MNL_DEBUG_MESSAGE_ENCODING, MnLDataTypes
from .misc import MnLDataType

if typing.TYPE_CHECKING:
    from .managers import MnLScriptManager


class CommandParsingError(Exception):
    pass


class InvalidCommandIDError(CommandParsingError):
    message: str
    command_id: int

    def __init__(self, command_id: int, message: str | None = None) -> None:
        if message is None:
            message = f"0x{command_id:04X}"
        super().__init__(message)
        self.message = message
        self.command_id = command_id

    def __reduce__(self) -> tuple[type[typing.Self], tuple[int, str]]:
        return self.__class__, (self.command_id, self.message)


class Variable:
    number: int

    def __init__(self, number: int) -> None:
        self.number = number

    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    @classmethod
    def from_bytes(cls, data: bytes) -> typing.Self:
        (number,) = struct.unpack("<H", data)

        return cls(number)

    def to_bytes(self) -> bytes:
        return struct.pack("<H", self.number)


class Command(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_stream(
        cls,
        manager: MnLScriptManager,
        stream: typing.BinaryIO,
        *,
        first_short: int | None = None,
    ) -> typing.Self:
        pass

    @abc.abstractmethod
    def to_bytes(self, manager: MnLScriptManager, offset: int) -> bytes:
        pass

    @abc.abstractmethod
    def serialized_len(self, manager: MnLScriptManager, offset: int) -> int:
        pass


class CodeCommand(Command):
    command_id: int
    result_variable: Variable | None
    arguments: list[int | float | Variable]

    def __init__(
        self,
        command_id: int,
        arguments: list[int | float | Variable] = [],
        result_variable: Variable | None = None,
    ) -> None:
        self.command_id = command_id
        self.result_variable = result_variable
        self.arguments = arguments

    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    @classmethod
    @override
    def from_stream(
        cls,
        manager: MnLScriptManager,
        stream: typing.BinaryIO,
        *,
        first_short: int | None = None,
    ) -> typing.Self:
        if first_short is not None:
            command_id = first_short
        else:
            (command_id,) = struct.unpack("<H", stream.read(2))
        if command_id >= len(manager.command_metadata_table):
            raise InvalidCommandIDError(command_id)
        (param_variables_bitfield,) = struct.unpack("<I", stream.read(4))

        param_metadata = manager.command_metadata_table[command_id]
        if param_metadata.has_return_value:
            result_variable = Variable.from_bytes(stream.read(2))
        else:
            result_variable = None
        arguments: list[int | float | Variable] = []
        for i, param_type in enumerate(param_metadata.parameter_types):
            if param_variables_bitfield & (1 << i) != 0:
                arguments.append(Variable.from_bytes(stream.read(2)))
            else:
                arguments.append(
                    param_type.struct_obj.unpack(
                        stream.read(param_type.struct_obj.size)
                    )[0]
                )

        return cls(command_id, arguments, result_variable)

    @override
    def to_bytes(self, manager: MnLScriptManager, offset: int) -> bytes:
        data_io = io.BytesIO()

        param_variables_bitfield = 0
        for i, argument in enumerate(self.arguments):
            if isinstance(argument, Variable):
                param_variables_bitfield |= 1 << i
        data_io.write(struct.pack("<HI", self.command_id, param_variables_bitfield))

        param_metadata = manager.command_metadata_table[self.command_id]
        if param_metadata.has_return_value:
            if self.result_variable is None:
                raise TypeError(
                    f"command (0x{self.command_id:04X}) has a return value "
                    "but None is specified"
                )
            elif not isinstance(
                self.result_variable, Variable
            ):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise TypeError(
                    "command.result_variable must be an mnllib.Variable, "
                    f"not '{type(self.result_variable).__name__}'"
                )
            data_io.write(self.result_variable.to_bytes())
        if len(param_metadata.parameter_types) != len(self.arguments):
            raise ValueError(
                f"number of arguments ({len(self.arguments)}) of "
                f"command (0x{self.command_id:04X}) doesn't match that specified by "
                f"the metadata ({len(param_metadata.parameter_types)})"
            )
        for param_type, argument in zip(param_metadata.parameter_types, self.arguments):
            if isinstance(argument, Variable):
                data_io.write(argument.to_bytes())
            else:
                data_io.write(param_type.struct_obj.pack(argument))

        return data_io.getvalue()

    @override
    def serialized_len(self, manager: MnLScriptManager, offset: int) -> int:
        result = 6

        param_metadata = manager.command_metadata_table[self.command_id]
        if param_metadata.has_return_value:
            result += 2
        if len(param_metadata.parameter_types) != len(self.arguments):
            raise ValueError(
                f"number of arguments ({len(self.arguments)}) of "
                f"command (0x{self.command_id:04X}) doesn't match that specified by "
                f"the metadata ({len(param_metadata.parameter_types)})"
            )
        for param_type, argument in zip(param_metadata.parameter_types, self.arguments):
            if isinstance(argument, Variable):
                result += 2
            else:
                result += param_type.struct_obj.size

        return result


class DataCommand(Command):
    pass


class RawDataCommand(DataCommand):
    data: bytes

    def __init__(self, data: bytes) -> None:
        self.data = data

    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    @classmethod
    @override
    def from_stream(
        cls,
        manager: MnLScriptManager,
        stream: typing.BinaryIO,
        *,
        first_short: int | None = None,
    ) -> typing.Self:
        return cls(
            (struct.pack("<H", first_short) if first_short is not None else b"")
            + stream.read()
        )

    @override
    def to_bytes(self, manager: MnLScriptManager, offset: int) -> bytes:
        return self.data

    @override
    def serialized_len(self, manager: MnLScriptManager, offset: int) -> int:
        return len(self.data)


class ArrayCommand(DataCommand):
    data_type: MnLDataType
    array: list[int]

    def __init__(self, data_type: MnLDataType, array: list[int]) -> None:
        self.data_type = data_type
        self.array = array

    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    @classmethod
    @override
    def from_stream(
        cls,
        manager: MnLScriptManager,
        stream: typing.BinaryIO,
        *,
        first_short: int | None = None,
    ) -> typing.Self:
        if first_short is None:
            first_short = typing.cast(int, struct.unpack("<H", stream.read(2))[0])

        data_type = MnLDataTypes((first_short >> 8) & 0x0F)  # type: ignore[call-arg]
        length = first_short & 0xFF
        data_size = data_type.struct_obj.size * length
        array = list(
            x[0] for x in data_type.struct_obj.iter_unpack(stream.read(data_size))
        )
        if len(array) != length:
            raise ValueError(f"array expected {length} elements, got {len(array)}")

        necessary_padding = (-(2 + data_size)) % 4
        padding = stream.read(necessary_padding)
        if padding != b"\xff" * necessary_padding:
            # raise ValueError("array is not padded to 4 bytes")
            stream.seek(-len(padding), os.SEEK_CUR)

        return cls(data_type, array)

    @override
    def to_bytes(self, manager: MnLScriptManager, offset: int) -> bytes:
        length = len(self.array)
        if length > 0xFF:
            raise ValueError(
                f"array must have at most 0xFF (255) elements, got {length}"
            )

        data = struct.pack("<H", length | (self.data_type.id << 8) | 0x8000) + b"".join(
            [self.data_type.struct_obj.pack(x) for x in self.array]
        )
        return b"\xff" * ((-offset) % 4) + data + b"\xff" * ((-len(data)) % 4)

    @override
    def serialized_len(self, manager: MnLScriptManager, offset: int) -> int:
        length = len(self.array)
        if length > 0xFF:
            raise ValueError(
                f"array must have at most 0xFF (255) elements, got {length}"
            )

        size = 2 + self.data_type.struct_obj.size * length
        return (-offset) % 4 + math.ceil(size / 4) * 4


def command_from_stream(
    manager: MnLScriptManager,
    stream: typing.BinaryIO,
    *,
    first_short: int | None = None,
) -> Command:
    if first_short is None:
        first_short = typing.cast(int, struct.unpack("<H", stream.read(2))[0])

    if first_short & 0xF000 == 0x8000:
        old_offset = stream.tell()
        try:
            decoded_data = (struct.pack("<H", first_short) + stream.read()).decode(
                MNL_DEBUG_MESSAGE_ENCODING
            )
        except UnicodeDecodeError:
            pass
        else:
            if not any(0x01 <= ord(x) <= 0x1F or x == "\x7f" for x in decoded_data):
                raise ValueError(f"array is valid {MNL_DEBUG_MESSAGE_ENCODING}")
        stream.seek(old_offset)
        command = ArrayCommand.from_stream(manager, stream, first_short=first_short)
        # new_offset = stream.tell()
        # stream.seek(old_offset)
        # data_raw = struct.pack("<H", first_short) + stream.read(
        #     new_offset - old_offset
        # )
        # if command.to_bytes(manager, 0).rstrip(b"\xff") != data_raw.rstrip(b"\xff"):
        #     raise ValueError("array doesn't get rebuilt successfully")
        return command
    else:
        return CodeCommand.from_stream(manager, stream, first_short=first_short)


class Subroutine:
    commands: list[Command]
    footer: bytes

    def __init__(self, commands: list[Command], footer: bytes = b"") -> None:
        self.commands = commands
        self.footer = footer

    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    @classmethod
    def from_stream(
        cls, manager: MnLScriptManager, stream: typing.BinaryIO
    ) -> typing.Self:
        commands: list[Command] = []
        while True:
            old_offset = stream.tell()

            first_short_data = stream.read(2)
            if len(first_short_data) < 2:
                footer = first_short_data
                break
            (first_short,) = struct.unpack("<H", first_short_data)

            try:
                commands.append(
                    command_from_stream(manager, stream, first_short=first_short)
                )
            except (struct.error, InvalidCommandIDError, ValueError):
                stream.seek(old_offset)
                footer = stream.read()
                break

        return cls(commands, footer)

    def to_bytes(
        self, manager: MnLScriptManager, offset: int, *, with_footer: bool = True
    ) -> bytes:
        data_io = io.BytesIO()

        for command in self.commands:
            offset += data_io.write(command.to_bytes(manager, offset))

        if with_footer:
            data_io.write(self.footer)

        return data_io.getvalue()

    def serialized_len(
        self, manager: MnLScriptManager, offset: int, *, with_footer: bool = True
    ) -> int:
        return functools.reduce(
            lambda current_offset, command: current_offset
            + command.serialized_len(manager, offset + current_offset),
            self.commands,
            0,
        ) + (len(self.footer) if with_footer else 0)


class CommandMetadata:
    has_return_value: bool
    parameter_types: list[MnLDataType]

    def __init__(
        self, has_return_value: bool, parameter_types: list[MnLDataType]
    ) -> None:
        self.has_return_value = has_return_value
        self.parameter_types = parameter_types

    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    @classmethod
    def from_bytes(cls, data: bytes) -> typing.Self:
        param_metadata, *raw_parameter_types = struct.unpack("<B15B", data)
        has_return_value = param_metadata & 0x80 != 0
        number_of_parameters = param_metadata & 0x7F

        parameter_types: list[MnLDataType] = []
        for i in range(number_of_parameters):
            parameter_types.append(
                MnLDataTypes(
                    (raw_parameter_types[i // 2] >> (i % 2 * 4)) & 0x0F
                )  # type: ignore[call-arg]
            )

        return cls(has_return_value, parameter_types)

    def to_bytes(self) -> bytes:
        param_metadata = (self.has_return_value * 0x80) | (
            len(self.parameter_types) & 0x7F
        )

        raw_parameter_types = [0] * 15
        for i, parameter in enumerate(self.parameter_types):
            raw_parameter_types[i // 2] |= parameter.id << (i % 2 * 4)

        return struct.pack("<B15B", param_metadata, *raw_parameter_types)
