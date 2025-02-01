from __future__ import annotations

import os
import struct
import io
import typing

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


class InvalidCommandParameterTypeError(CommandParsingError):
    message: str
    parameter_type: int

    def __init__(self, parameter_type: int, message: str | None = None) -> None:
        if message is None:
            message = f"0x{parameter_type:X}"
        super().__init__(message)
        self.message = message
        self.parameter_type = parameter_type

    def __reduce__(self) -> tuple[type[typing.Self], tuple[int, str]]:
        return self.__class__, (self.parameter_type, self.message)


class Variable:
    number: int

    def __init__(self, number: int) -> None:
        self.number = number

    @classmethod
    def from_bytes(cls, data: bytes) -> typing.Self:
        (number,) = struct.unpack("<H", data)

        return cls(number)

    def to_bytes(self) -> bytes:
        return struct.pack("<H", self.number)


class Command:
    command_id: int
    result_variable: Variable | None
    arguments: list[int | Variable]

    def __init__(
        self,
        command_id: int,
        arguments: list[int | Variable] = [],
        result_variable: Variable | None = None,
    ) -> None:
        self.command_id = command_id
        self.result_variable = result_variable
        self.arguments = arguments

    @classmethod
    def from_stream(
        cls, manager: MnLScriptManager, stream: typing.BinaryIO
    ) -> typing.Self:
        command_id: int
        (command_id,) = struct.unpack("<H", stream.read(2))
        if command_id >= len(manager.command_parameter_metadata_table):
            raise InvalidCommandIDError(command_id)
        (param_variables_bitfield,) = struct.unpack("<I", stream.read(4))

        param_metadata = manager.command_parameter_metadata_table[command_id]
        if param_metadata.has_return_value:
            result_variable = Variable.from_bytes(stream.read(2))
        else:
            result_variable = None
        arguments: list[int | Variable] = []
        for i, param_type in enumerate(param_metadata.parameter_types):
            if param_variables_bitfield & (1 << i):
                arguments.append(Variable.from_bytes(stream.read(2)))
            else:
                if param_type >= len(manager.command_parameter_metadata_struct_map):
                    raise InvalidCommandParameterTypeError(param_type)
                arguments.append(
                    manager.command_parameter_metadata_struct_map[param_type].unpack(
                        stream.read(
                            manager.command_parameter_metadata_struct_map[
                                param_type
                            ].size
                        )
                    )[0]
                )

        return cls(command_id, arguments, result_variable)

    def to_bytes(self, manager: MnLScriptManager) -> bytes:
        data_io = io.BytesIO()

        param_variables_bitfield = 0
        for i, argument in enumerate(self.arguments):
            if isinstance(argument, Variable):
                param_variables_bitfield |= 1 << i
        data_io.write(struct.pack("<HI", self.command_id, param_variables_bitfield))

        if self.result_variable is not None:
            data_io.write(self.result_variable.to_bytes())
        param_metadata = manager.command_parameter_metadata_table[self.command_id]
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
                if param_type >= len(manager.command_parameter_metadata_struct_map):
                    raise InvalidCommandParameterTypeError(param_type)
                data_io.write(
                    manager.command_parameter_metadata_struct_map[param_type].pack(
                        argument
                    )
                )

        return data_io.getvalue()


class Subroutine:
    commands: list[Command]
    footer: bytes

    def __init__(self, commands: list[Command], footer: bytes = b"") -> None:
        self.commands = commands
        self.footer = footer

    @classmethod
    def from_stream(
        cls, manager: MnLScriptManager, stream: typing.BinaryIO
    ) -> typing.Self:
        footer = b""
        commands: list[Command] = []
        while stream.read(1) != b"":
            stream.seek(-1, os.SEEK_CUR)
            old_offset = stream.tell()
            try:
                commands.append(Command.from_stream(manager, stream))
            except (struct.error, InvalidCommandIDError):
                stream.seek(old_offset)
                footer = stream.read()
                break
        return cls(commands, footer)

    def to_bytes(self, manager: MnLScriptManager) -> bytes:
        data_io = io.BytesIO()

        for command in self.commands:
            data_io.write(command.to_bytes(manager))
        data_io.write(self.footer)

        return data_io.getvalue()


class CommandParameterMetadata:
    has_return_value: bool
    parameter_types: list[int]

    def __init__(self, has_return_value: bool, parameter_types: list[int]) -> None:
        self.has_return_value = has_return_value
        self.parameter_types = parameter_types

    @classmethod
    def from_bytes(cls, data: bytes) -> typing.Self:
        param_metadata, *raw_parameter_types = struct.unpack("<B15B", data)
        has_return_value = param_metadata & 0x80 != 0
        number_of_parameters = param_metadata & 0x7F

        parameter_types: list[int] = []
        for i in range(number_of_parameters):
            parameter_types.append((raw_parameter_types[i // 2] >> (i % 2 * 4)) & 0x0F)

        return cls(has_return_value, parameter_types)

    def to_bytes(self) -> bytes:
        param_metadata = (self.has_return_value * 0x80) | (
            len(self.parameter_types) & 0x7F
        )

        raw_parameter_types = [0] * 15
        for i, parameter in enumerate(self.parameter_types):
            raw_parameter_types[i // 2] |= parameter << (i % 2 * 4)

        return struct.pack("<B15B", param_metadata, *raw_parameter_types)
