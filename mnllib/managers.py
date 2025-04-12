import abc
import typing

from .script import CommandMetadata


class MnLScriptManager(abc.ABC):
    command_metadata_table: list[CommandMetadata]

    def __init__(self) -> None:
        self.command_metadata_table = []

    def load_command_metadata_table(
        self, stream: typing.BinaryIO, number_of_commands: int
    ) -> None:
        self.command_metadata_table = []
        for _ in range(number_of_commands):
            self.command_metadata_table.append(
                CommandMetadata.from_bytes(stream.read(16))
            )

    def save_command_metadata_table(
        self, data: bytearray, metadata_table_address: int, number_of_commands: int
    ) -> None:
        data[
            metadata_table_address : (metadata_table_address + number_of_commands * 16)
        ] = b"".join(
            [
                parameter_metadata.to_bytes()
                for parameter_metadata in self.command_metadata_table
            ]
        )
