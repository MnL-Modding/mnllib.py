import abc
import struct
import typing

from .script import CommandParameterMetadata


class MnLScriptManager(abc.ABC):
    command_parameter_metadata_struct_map: list[struct.Struct]
    command_parameter_metadata_table: list[CommandParameterMetadata]

    def __init__(
        self, command_parameter_metadata_struct_map: list[struct.Struct]
    ) -> None:
        self.command_parameter_metadata_struct_map = (
            command_parameter_metadata_struct_map
        )
        self.command_parameter_metadata_table = []

    def load_command_parameter_metadata_table(
        self, stream: typing.BinaryIO, number_of_commands: int
    ) -> None:
        self.command_parameter_metadata_table = []
        for _ in range(number_of_commands):
            self.command_parameter_metadata_table.append(
                CommandParameterMetadata.from_bytes(stream.read(16))
            )

    def save_command_parameter_metadata_table(
        self, data: bytearray, metadata_table_address: int, number_of_commands: int
    ) -> None:
        data[
            metadata_table_address : (metadata_table_address + number_of_commands * 16)
        ] = b"".join(
            [
                parameter_metadata.to_bytes()
                for parameter_metadata in self.command_parameter_metadata_table
            ]
        )
