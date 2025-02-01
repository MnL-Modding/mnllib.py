import pathlib
import struct
import itertools
import warnings
import typing

from .consts import (
    BATTLE_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS,
    BATTLE_NUMBER_OF_COMMANDS,
    BATTLE_SCRIPTS_DIRECTORY_NAME,
    BATTLE_SCRIPTS_FILES_METADATA,
    COMMAND_PARAMETER_STRUCT_MAP,
    FEVENT_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS,
    FEVENT_FILE_NAME,
    FEVENT_OFFSET_TABLE_LENGTH_ADDRESS,
    FEVENT_OFFSET_TABLE_ADDRESS,
    FEVENT_NUMBER_OF_COMMANDS,
    MENU_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS,
    MENU_NUMBER_OF_COMMANDS,
    SHOP_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS,
    SHOP_NUMBER_OF_COMMANDS,
)
from ..managers import MnLScriptManager
from ..misc import MnLLibWarning
from ..utils import read_length_prefixed_array
from .misc import FEventChunk, parse_fevent_chunk
from .script import BattleScript, FEventScript


class FEventScriptManager(MnLScriptManager):
    fevent_offset_table: list[tuple[int, int, int]]
    fevent_chunks: list[
        tuple[FEventScript | None, FEventChunk | None, FEventChunk | None]
    ]
    fevent_footer_offset: int
    fevent_footer: bytes

    def __init__(self, load: bool = True) -> None:
        super().__init__(
            command_parameter_metadata_struct_map=COMMAND_PARAMETER_STRUCT_MAP
        )

        if load:
            self.load_all()
        else:
            self.fevent_offset_table = []
            self.fevent_chunks = []
            self.fevent_footer_offset = 0
            self.fevent_footer = b""

    def load_overlay3(
        self,
        file: (
            typing.BinaryIO | pathlib.Path | str
        ) = "data/overlay.dec/overlay_0003.dec.bin",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
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
        self,
        file: (
            typing.BinaryIO | pathlib.Path | str
        ) = "data/overlay.dec/overlay_0006.dec.bin",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "rb")
            close_file = True

        try:
            file.seek(FEVENT_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS)
            self.load_command_parameter_metadata_table(file, FEVENT_NUMBER_OF_COMMANDS)
        finally:
            if close_file:
                file.close()

    def load_fevent(
        self,
        file: typing.BinaryIO | pathlib.Path | str = f"data/data/{FEVENT_FILE_NAME}",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
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
                            file.read(
                                (flat_fevent_offset_table[index + 1] - offset)
                                if index + 1 < len(flat_fevent_offset_table)
                                else 0
                            ),
                            index,
                        ),
                    )
                    index += 1
                self.fevent_chunks.append(
                    typing.cast(
                        tuple[
                            FEventScript | None, FEventChunk | None, FEventChunk | None
                        ],
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
        self,
        file: (
            typing.BinaryIO | pathlib.Path | str
        ) = "data/overlay.dec/overlay_0003.dec.bin",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
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
                        struct.pack("<III", *offsets)
                        for offsets in self.fevent_offset_table
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
        self,
        file: (
            typing.BinaryIO | pathlib.Path | str
        ) = "data/overlay.dec/overlay_0006.dec.bin",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "r+b")
            close_file = True

        try:
            overlay6_raw = bytearray(file.read())

            self.save_command_parameter_metadata_table(
                overlay6_raw,
                FEVENT_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS,
                FEVENT_NUMBER_OF_COMMANDS,
            )

            file.seek(0)
            file.truncate()
            file.write(overlay6_raw)
        finally:
            if close_file:
                file.close()

    def save_fevent(
        self,
        file: typing.BinaryIO | pathlib.Path | str = f"data/data/{FEVENT_FILE_NAME}",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
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


class BattleScriptManager(MnLScriptManager):
    battle_offset_tables: dict[int, list[int]]
    battle_scripts_files: dict[int, list[BattleScript]]
    battle_scripts_files_footer_offsets: dict[int, int]
    battle_scripts_files_footers: dict[int, bytes]

    def __init__(self, load: bool = True) -> None:
        super().__init__(
            command_parameter_metadata_struct_map=COMMAND_PARAMETER_STRUCT_MAP
        )

        if load:
            self.load_all()
        else:
            self.battle_offset_tables = {}
            self.battle_scripts_files = {}
            self.battle_scripts_files_footer_offsets = {}
            self.battle_scripts_files_footers = {}

    def load_overlay12(
        self,
        file: (
            typing.BinaryIO | pathlib.Path | str
        ) = "data/overlay.dec/overlay_0012.dec.bin",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "rb")
            close_file = True

        try:
            file.seek(BATTLE_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS)
            self.load_command_parameter_metadata_table(file, BATTLE_NUMBER_OF_COMMANDS)
        finally:
            if close_file:
                file.close()

    def load_overlay14(
        self,
        file: (
            typing.BinaryIO | pathlib.Path | str
        ) = "data/overlay.dec/overlay_0014.dec.bin",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "rb")
            close_file = True

        try:
            self.battle_offset_tables = {}
            self.battle_scripts_files_footer_offsets = {}
            for address, metadata in BATTLE_SCRIPTS_FILES_METADATA.items():
                file.seek(metadata.offset_table_address)
                self.battle_offset_tables[address] = read_length_prefixed_array(
                    file, "<I", length_in_bytes=True
                )
                self.battle_scripts_files_footer_offsets[address] = (
                    self.battle_offset_tables[address].pop()
                )
        finally:
            if close_file:
                file.close()

    def load_battle_scripts_file(
        self, address: int, file: typing.BinaryIO | pathlib.Path | str
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "rb")
            close_file = True

        try:
            self.battle_scripts_files[address] = []
            offset_table = self.battle_offset_tables[address]
            footer_offset = self.battle_scripts_files_footer_offsets[address]
            for index, offset in enumerate(offset_table):
                file.seek(offset)
                self.battle_scripts_files[address].append(
                    BattleScript.from_bytes(
                        self,
                        file.read(
                            (
                                offset_table[index + 1]
                                if index + 1 < len(offset_table)
                                else footer_offset
                            )
                            - offset
                        ),
                        index,
                    )
                )

            file.seek(footer_offset)
            self.battle_scripts_files_footers[address] = file.read()
        finally:
            if close_file:
                file.close()

    def load_all_battle_scripts_files(
        self,
        directory: pathlib.Path | str = f"data/data/{BATTLE_SCRIPTS_DIRECTORY_NAME}",
    ) -> None:
        if isinstance(directory, str):
            directory = pathlib.Path(directory)

        self.battle_scripts_files = {}
        self.battle_scripts_files_footers = {}
        for address in self.battle_offset_tables.keys():
            self.load_battle_scripts_file(
                address, directory / BATTLE_SCRIPTS_FILES_METADATA[address].filename
            )

    def load_all(self) -> None:
        self.load_overlay12()
        self.load_overlay14()
        self.load_all_battle_scripts_files()

    def save_overlay12(
        self,
        file: (
            typing.BinaryIO | pathlib.Path | str
        ) = "data/overlay.dec/overlay_0012.dec.bin",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "r+b")
            close_file = True

        try:
            overlay12_raw = bytearray(file.read())

            self.save_command_parameter_metadata_table(
                overlay12_raw,
                BATTLE_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS,
                BATTLE_NUMBER_OF_COMMANDS,
            )

            file.seek(0)
            file.truncate()
            file.write(overlay12_raw)
        finally:
            if close_file:
                file.close()

    def save_overlay14(
        self,
        file: (
            typing.BinaryIO | pathlib.Path | str
        ) = "data/overlay.dec/overlay_0014.dec.bin",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "r+b")
            close_file = True

        try:
            overlay14_raw = bytearray(file.read())

            for address, offset_table in self.battle_offset_tables.items():
                metadata = BATTLE_SCRIPTS_FILES_METADATA[address]

                old_offset_table_length = (
                    struct.unpack(
                        "<I",
                        overlay14_raw[
                            metadata.offset_table_address : (
                                metadata.offset_table_address + 4
                            )
                        ],
                    )[0]
                    // 4
                    - 1
                )
                del overlay14_raw[
                    metadata.offset_table_address : metadata.offset_table_address
                    + 4
                    + old_offset_table_length * 4
                ]
                overlay14_raw[
                    metadata.offset_table_address : metadata.offset_table_address
                ] = struct.pack("<I", (len(offset_table) + 2) * 4) + b"".join(
                    [
                        struct.pack("<I", x)
                        for x in itertools.chain(
                            offset_table,
                            [self.battle_scripts_files_footer_offsets[address]],
                        )
                    ]
                )

            file.seek(0)
            file.truncate()
            file.write(overlay14_raw)
        finally:
            if close_file:
                file.close()

    def save_battle_scripts_file(
        self, address: int, file: typing.BinaryIO | pathlib.Path | str
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "wb")
            close_file = True

        try:
            self.battle_offset_tables[address] = []
            for script in self.battle_scripts_files[address]:
                self.battle_offset_tables[address].append(file.tell())
                file.write(script.to_bytes(self))

            self.battle_scripts_files_footer_offsets[address] = file.tell()
            file.write(self.battle_scripts_files_footers[address])
        finally:
            if close_file:
                file.close()

    def save_all_battle_scripts_files(
        self,
        directory: pathlib.Path | str = f"data/data/{BATTLE_SCRIPTS_DIRECTORY_NAME}",
    ) -> None:
        if isinstance(directory, str):
            directory = pathlib.Path(directory)

        for address in self.battle_scripts_files.keys():
            self.save_battle_scripts_file(
                address, directory / BATTLE_SCRIPTS_FILES_METADATA[address].filename
            )

    def save_all(self) -> None:
        self.save_all_battle_scripts_files()
        self.save_overlay14()
        self.save_overlay12()


class MenuScriptManager(MnLScriptManager):
    def __init__(self, load: bool = True) -> None:
        super().__init__(
            command_parameter_metadata_struct_map=COMMAND_PARAMETER_STRUCT_MAP
        )
        if load:
            self.load_all()

    def load_overlay123(
        self,
        file: (
            typing.BinaryIO | pathlib.Path | str
        ) = "data/overlay.dec/overlay_0123.dec.bin",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "rb")
            close_file = True

        try:
            file.seek(MENU_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS)
            self.load_command_parameter_metadata_table(file, MENU_NUMBER_OF_COMMANDS)
        finally:
            if close_file:
                file.close()

    def load_all(self) -> None:
        self.load_overlay123()

    def save_overlay123(
        self,
        file: (
            typing.BinaryIO | pathlib.Path | str
        ) = "data/overlay.dec/overlay_0123.dec.bin",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "r+b")
            close_file = True

        try:
            overlay123_raw = bytearray(file.read())

            self.save_command_parameter_metadata_table(
                overlay123_raw,
                MENU_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS,
                MENU_NUMBER_OF_COMMANDS,
            )

            file.seek(0)
            file.truncate()
            file.write(overlay123_raw)
        finally:
            if close_file:
                file.close()

    def save_all(self) -> None:
        self.save_overlay123()


class ShopScriptManager(MnLScriptManager):
    def __init__(self, load: bool = True) -> None:
        super().__init__(
            command_parameter_metadata_struct_map=COMMAND_PARAMETER_STRUCT_MAP
        )
        if load:
            self.load_all()

    def load_overlay124(
        self,
        file: (
            typing.BinaryIO | pathlib.Path | str
        ) = "data/overlay.dec/overlay_0124.dec.bin",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "rb")
            close_file = True

        try:
            file.seek(SHOP_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS)
            self.load_command_parameter_metadata_table(file, SHOP_NUMBER_OF_COMMANDS)
        finally:
            if close_file:
                file.close()

    def load_all(self) -> None:
        self.load_overlay124()

    def save_overlay124(
        self,
        file: (
            typing.BinaryIO | pathlib.Path | str
        ) = "data/overlay.dec/overlay_0124.dec.bin",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "r+b")
            close_file = True

        try:
            overlay124_raw = bytearray(file.read())

            self.save_command_parameter_metadata_table(
                overlay124_raw,
                SHOP_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS,
                SHOP_NUMBER_OF_COMMANDS,
            )

            file.seek(0)
            file.truncate()
            file.write(overlay124_raw)
        finally:
            if close_file:
                file.close()

    def save_all(self) -> None:
        self.save_overlay124()
