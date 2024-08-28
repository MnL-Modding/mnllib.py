import struct
import itertools
import warnings
import typing

from .consts import (
    COMMAND_PARAMETER_METADATA_TABLE_ADDRESS,
    FEVENT_OFFSET_TABLE_LENGTH_ADDRESS,
    FEVENT_OFFSET_TABLE_ADDRESS,
    NUMBER_OF_COMMANDS,
)
from .misc import FEventChunk, MnLLibWarning, parse_fevent_chunk
from .script import CommandParameterMetadata, Script


class MnLScriptManager:
    fevent_offset_table: list[tuple[int, int, int]]
    command_parameter_metadata_table: list[CommandParameterMetadata]
    fevent_chunks: list[tuple[Script | None, FEventChunk | None, FEventChunk | None]]
    fevent_footer_offset: int
    fevent_footer: bytes

    def __init__(self, load: bool = True) -> None:
        if load:
            self.load_all()

    def load_overlay3(
        self, file: typing.BinaryIO | str = "data/overlay.dec/overlay_0003.dec.bin"
    ) -> None:
        close_file = False
        if isinstance(file, str):
            file = open(file, "rb")
            close_file = True

        try:
            file.seek(FEVENT_OFFSET_TABLE_LENGTH_ADDRESS)
            fevent_offset_table_length = struct.unpack("<I", file.read(4))[0] // 4 - 1
            if fevent_offset_table_length % 3 != 1:
                warnings.warn(
                    "The length of the FEvent offset table "
                    f"({fevent_offset_table_length}) % 3 is not 1, "
                    f"but rather {fevent_offset_table_length % 3}!",
                    MnLLibWarning,
                )
            self.fevent_offset_table = []
            for _ in range(fevent_offset_table_length // 3):
                self.fevent_offset_table.append(struct.unpack("<III", file.read(4 * 3)))
            (self.fevent_footer_offset,) = struct.unpack("<I", file.read(4))
        finally:
            if close_file:
                file.close()

    def load_overlay6(
        self, file: typing.BinaryIO | str = "data/overlay.dec/overlay_0006.dec.bin"
    ) -> None:
        close_file = False
        if isinstance(file, str):
            file = open(file, "rb")
            close_file = True

        try:
            file.seek(COMMAND_PARAMETER_METADATA_TABLE_ADDRESS)
            self.command_parameter_metadata_table = []
            for _ in range(NUMBER_OF_COMMANDS):
                self.command_parameter_metadata_table.append(
                    CommandParameterMetadata.from_bytes(file.read(16))
                )
        finally:
            if close_file:
                file.close()

    def load_fevent(
        self, file: typing.BinaryIO | str = "data/data/FEvent/FEvent.dat"
    ) -> None:
        close_file = False
        if isinstance(file, str):
            file = open(file, "rb")
            close_file = True

        try:
            flat_fevent_offset_table = list(
                itertools.chain.from_iterable(self.fevent_offset_table)
            )
            index = 0
            self.fevent_chunks = []
            for triple in self.fevent_offset_table:
                chunk_triple: tuple[FEventChunk | None, ...] = ()
                for offset in triple:
                    file.seek(offset)
                    chunk_triple += (
                        parse_fevent_chunk(
                            self,
                            index,
                            file.read(
                                (flat_fevent_offset_table[index + 1] - offset)
                                if index + 1 < len(flat_fevent_offset_table)
                                else 0
                            ),
                        ),
                    )
                    index += 1
                self.fevent_chunks.append(
                    typing.cast(
                        tuple[Script | None, FEventChunk | None, FEventChunk | None],
                        chunk_triple,
                    )
                )

            file.seek(self.fevent_footer_offset)
            self.fevent_footer = file.read()
        finally:
            if close_file:
                file.close()

    def load_all(self) -> None:
        self.load_overlay3()
        self.load_overlay6()
        self.load_fevent()

    def save_overlay3(
        self, file: typing.BinaryIO | str = "data/overlay.dec/overlay_0003.dec.bin"
    ) -> None:
        close_file = False
        if isinstance(file, str):
            file = open(file, "r+b")
            close_file = True

        try:
            overlay3_raw = bytearray(file.read())

            old_fevent_offset_table_length = (
                struct.unpack(
                    "<I",
                    overlay3_raw[
                        FEVENT_OFFSET_TABLE_LENGTH_ADDRESS : (
                            FEVENT_OFFSET_TABLE_LENGTH_ADDRESS + 4
                        )
                    ],
                )[0]
                // 4
                - 1
            )
            del overlay3_raw[
                FEVENT_OFFSET_TABLE_LENGTH_ADDRESS : FEVENT_OFFSET_TABLE_ADDRESS
                + old_fevent_offset_table_length * 4
            ]
            overlay3_raw[
                FEVENT_OFFSET_TABLE_LENGTH_ADDRESS:FEVENT_OFFSET_TABLE_LENGTH_ADDRESS
            ] = (
                struct.pack("<I", (len(self.fevent_offset_table) * 3 + 2) * 4)
                + b"".join(
                    [
                        struct.pack("<III", a, b, c)
                        for a, b, c in self.fevent_offset_table
                    ]
                )
                + struct.pack("<I", self.fevent_footer_offset)
            )

            file.seek(0)
            file.truncate()
            file.write(overlay3_raw)
        finally:
            if close_file:
                file.close()

    def save_overlay6(
        self, file: typing.BinaryIO | str = "data/overlay.dec/overlay_0006.dec.bin"
    ) -> None:
        close_file = False
        if isinstance(file, str):
            file = open(file, "r+b")
            close_file = True

        try:
            overlay6_raw = bytearray(file.read())

            overlay6_raw[
                COMMAND_PARAMETER_METADATA_TABLE_ADDRESS : (
                    COMMAND_PARAMETER_METADATA_TABLE_ADDRESS + NUMBER_OF_COMMANDS * 16
                )
            ] = b"".join(
                [
                    parameter_metadata.to_bytes()
                    for parameter_metadata in self.command_parameter_metadata_table
                ]
            )

            file.seek(0)
            file.truncate()
            file.write(overlay6_raw)
        finally:
            if close_file:
                file.close()

    def save_fevent(
        self, file: typing.BinaryIO | str = "data/FEvent/FEvent.dat"
    ) -> None:
        close_file = False
        if isinstance(file, str):
            file = open(file, "wb")
            close_file = True

        try:
            self.fevent_offset_table = []
            for triple in self.fevent_chunks:
                offset_triple: tuple[int, ...] = ()
                for chunk in triple:
                    offset_triple += (file.tell(),)
                    if chunk is not None:
                        file.write(chunk.to_bytes(self))
                self.fevent_offset_table.append(
                    typing.cast(tuple[int, int, int], offset_triple)
                )

            self.fevent_footer_offset = file.tell()
            file.write(self.fevent_footer)
        finally:
            if close_file:
                file.close()

    def save_all(self) -> None:
        self.save_fevent()
        self.save_overlay6()
        self.save_overlay3()
