from __future__ import annotations

import os
import struct
import io
import warnings
import typing

from .consts import COMMAND_PARAMETER_STRUCT_MAP, NUMBER_OF_COMMANDS
from .misc import FEventChunk, MnLLibWarning
from .utils import read_length_prefixed_array

if typing.TYPE_CHECKING:
    from .managers import MnLScriptManager


class ScriptHeader:
    index: int

    unk_0x00: bytes
    offsets_unk1: bytes
    array1: list[int]
    var1: int
    array2: list[int]
    var2: int
    array3: list[int]
    section1_unk1: bytes
    array4: list[tuple[int, int, int, int, int]]
    array5: list[int]
    subroutine_table: list[int]
    post_table_subroutine: Subroutine

    def __init__(
        self,
        index: int,
        *,
        unk_0x00: bytes,
        offsets_unk1: bytes,
        array1: list[int],
        var1: int,
        array2: list[int],
        var2: int,
        array3: list[int],
        section1_unk1: bytes,
        array4: list[tuple[int, int, int, int, int]],
        array5: list[int],
        subroutine_table: list[int],
        post_table_subroutine: Subroutine,
    ) -> None:
        self.index = index

        self.unk_0x00 = unk_0x00
        self.offsets_unk1 = offsets_unk1
        self.array1 = array1
        self.var1 = var1
        self.array2 = array2
        self.var2 = var2
        self.array3 = array3
        self.section1_unk1 = section1_unk1
        self.array4 = array4
        self.array5 = array5
        self.subroutine_table = subroutine_table
        self.post_table_subroutine = post_table_subroutine

    @classmethod
    def from_stream(
        cls, manager: MnLScriptManager, index: int, stream: typing.BinaryIO
    ) -> typing.Self:
        unk_0x00 = stream.read(12)
        section1_offset, section2_offset, section3_offset = struct.unpack(
            "<III", stream.read(4 * 3)
        )
        offsets_unk1 = stream.read(section1_offset - stream.tell())

        (array1_length_plus_one,) = struct.unpack("<I", stream.read(4))
        array1 = [
            struct.unpack("<I", stream.read(4))[0]
            for _ in range(array1_length_plus_one - 1)
        ]
        (var1,) = struct.unpack("<I", stream.read(4))
        (array2_length_plus_one,) = struct.unpack("<I", stream.read(4))
        array2 = [
            struct.unpack("<I", stream.read(4))[0]
            for _ in range(array2_length_plus_one - 1)
        ]
        (var2,) = struct.unpack("<I", stream.read(4))
        array3 = read_length_prefixed_array(stream, "<H", "<H")
        section1_unk1 = stream.read(section2_offset - stream.tell())

        array4 = read_length_prefixed_array(stream, "<IIIII")

        if stream.tell() != section3_offset:
            warnings.warn(
                "There are extra bytes between the 2nd and 3rd section of "
                f"the header of script {index}!",
                MnLLibWarning,
            )
            stream.seek(section3_offset)
        array5 = read_length_prefixed_array(stream, "<H", "<H")
        subroutine_table: list[int] = []
        post_table_subroutine = Subroutine([])
        while (
            (stream.tell() - section3_offset < subroutine_table[0])
            if len(subroutine_table) > 0
            else True
        ):
            (offset,) = struct.unpack("<H", stream.read(2))
            if len(subroutine_table) > 0 and offset < subroutine_table[-1]:
                stream.seek(-2, os.SEEK_CUR)
                post_table_subroutine = Subroutine.from_stream(
                    manager,
                    io.BytesIO(
                        stream.read(
                            subroutine_table[0] - stream.tell() + section3_offset
                        )
                    ),
                )
                break
            subroutine_table.append(offset)
        subroutine_base_offset = stream.tell() - section3_offset
        subroutine_table = [
            offset - subroutine_base_offset for offset in subroutine_table
        ]

        return cls(
            index,
            unk_0x00=unk_0x00,
            offsets_unk1=offsets_unk1,
            array1=array1,
            var1=var1,
            array2=array2,
            var2=var2,
            array3=array3,
            section1_unk1=section1_unk1,
            array4=array4,
            array5=array5,
            subroutine_table=subroutine_table,
            post_table_subroutine=post_table_subroutine,
        )

    def to_bytes(self, manager: MnLScriptManager) -> bytes:
        data_io = io.BytesIO()

        data_io.write(self.unk_0x00)
        section1_offset = 0x18 + len(self.offsets_unk1)
        section2_offset = (
            section1_offset
            + (2 + len(self.array1)) * 4
            + (2 + len(self.array2)) * 4
            + (1 + len(self.array3)) * 2
            + len(self.section1_unk1)
        )
        section3_offset = section2_offset + 4 + len(self.array4) * 20
        post_table_subroutine_raw = self.post_table_subroutine.to_bytes(manager)
        header_end_offset = (
            section3_offset
            + 2
            + len(self.array5) * 2
            + len(self.subroutine_table) * 2
            + len(post_table_subroutine_raw)
        )
        data_io.write(
            struct.pack("<III", section1_offset, section2_offset, section3_offset)
        )
        data_io.write(self.offsets_unk1)

        data_io.write(struct.pack("<I", len(self.array1) + 1))
        data_io.write(struct.pack(f"<{len(self.array1)}I", *self.array1))
        data_io.write(struct.pack("<I", self.var1))
        data_io.write(struct.pack("<I", len(self.array2) + 1))
        data_io.write(struct.pack(f"<{len(self.array2)}I", *self.array2))
        data_io.write(struct.pack("<I", self.var2))
        data_io.write(struct.pack("<H", len(self.array3)))
        data_io.write(struct.pack(f"<{len(self.array3)}H", *self.array3))
        data_io.write(self.section1_unk1)

        data_io.write(struct.pack("<I", len(self.array4)))
        for a, b, c, d, e in self.array4:
            data_io.write(struct.pack("<IIIII", a, b, c, d, e))

        data_io.write(struct.pack("<H", len(self.array5)))
        data_io.write(struct.pack(f"<{len(self.array5)}H", *self.array5))
        subroutine_base_offset = header_end_offset - section3_offset
        for offset in self.subroutine_table:
            data_io.write(struct.pack("<H", offset + subroutine_base_offset))
        data_io.write(post_table_subroutine_raw)

        return data_io.getvalue()


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
        arguments: list[int | Variable],
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
        if command_id >= NUMBER_OF_COMMANDS:
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
                if param_type >= len(COMMAND_PARAMETER_STRUCT_MAP):
                    raise InvalidCommandParameterTypeError(param_type)
                arguments.append(
                    COMMAND_PARAMETER_STRUCT_MAP[param_type].unpack(
                        stream.read(COMMAND_PARAMETER_STRUCT_MAP[param_type].size)
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
                if param_type >= len(COMMAND_PARAMETER_STRUCT_MAP):
                    raise InvalidCommandParameterTypeError(param_type)
                data_io.write(COMMAND_PARAMETER_STRUCT_MAP[param_type].pack(argument))

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


class Script(FEventChunk):
    index: int
    header: ScriptHeader
    subroutines: list[Subroutine]

    def __init__(
        self, index: int, header: ScriptHeader, subroutines: list[Subroutine]
    ) -> None:
        self.index = index
        self.header = header
        self.subroutines = subroutines

    @classmethod
    def from_bytes(
        cls, manager: MnLScriptManager, index: int, data: bytes
    ) -> typing.Self:
        data_io = io.BytesIO(data)
        header = ScriptHeader.from_stream(manager, index, data_io)

        subroutine_base_offset = data_io.tell()
        subroutines: list[Subroutine] = []
        for i, offset in enumerate(header.subroutine_table):
            subroutines.append(
                Subroutine.from_stream(
                    manager,
                    io.BytesIO(
                        data[
                            subroutine_base_offset
                            + offset : (
                                (
                                    subroutine_base_offset
                                    + header.subroutine_table[i + 1]
                                )
                                if i + 1 < len(header.subroutine_table)
                                else None
                            )
                        ]
                    ),
                )
            )

        return cls(index, header, subroutines)

    def to_bytes(self, manager: MnLScriptManager) -> bytes:
        subroutines_raw = io.BytesIO()
        self.header.subroutine_table = []
        for subroutine in self.subroutines:
            self.header.subroutine_table.append(subroutines_raw.tell())
            subroutines_raw.write(subroutine.to_bytes(manager))

        return self.header.to_bytes(manager) + subroutines_raw.getvalue()


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
