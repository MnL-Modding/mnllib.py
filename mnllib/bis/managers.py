import os
import pathlib
import struct
import itertools
import warnings
import typing
from typing import override

from ..consts import DEFAULT_DATA_DIR_PATH
from ..managers import MnLScriptManager
from ..misc import MnLLibWarning
from ..nds.consts import fs_std_data_path, fs_std_overlay_path
from ..utils import read_length_prefixed_array, stream_or_open_file
from .consts import (
    BATTLE_COMMAND_METADATA_TABLE_ADDRESS,
    BATTLE_NUMBER_OF_COMMANDS,
    BATTLE_SCRIPTS_DIRECTORY_NAME,
    BATTLE_SCRIPTS_FILES_METADATA,
    FEVENT_COMMAND_METADATA_TABLE_ADDRESS,
    FEVENT_PATH,
    FEVENT_OFFSET_TABLE_LENGTH_ADDRESS,
    FEVENT_OFFSET_TABLE_ADDRESS,
    FEVENT_NUMBER_OF_COMMANDS,
    SCRIPT_ALIGNMENT,
    MENU_COMMAND_METADATA_TABLE_ADDRESS,
    MENU_NUMBER_OF_COMMANDS,
    SHOP_COMMAND_METADATA_TABLE_ADDRESS,
    SHOP_NUMBER_OF_COMMANDS,
)
from .script import BattleScript, FEventScript
from .text import LanguageTable


type FEventChunkTriple = tuple[FEventScript, FEventScript | None, LanguageTable | None]


class FEventScriptManager(MnLScriptManager):
    fevent_offset_table: list[tuple[int, int, int]]
    fevent_chunks: list[FEventChunkTriple]
    fevent_footer_offset: int
    fevent_footer: bytes

    def __init__(
        self, data_dir: str | os.PathLike[str] | None = DEFAULT_DATA_DIR_PATH
    ) -> None:
        super().__init__()

        if data_dir is not None:
            self.load_all(data_dir)
        else:
            self.fevent_offset_table = []
            self.fevent_chunks = []
            self.fevent_footer_offset = 0
            self.fevent_footer = b""

    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def load_overlay3(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_overlay_path(3),
    ) -> None:
        with stream_or_open_file(file, "rb") as file:
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

    def load_overlay6(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_overlay_path(6),
    ) -> None:
        with stream_or_open_file(file, "rb") as file:
            file.seek(FEVENT_COMMAND_METADATA_TABLE_ADDRESS)
            self.load_command_metadata_table(file, FEVENT_NUMBER_OF_COMMANDS)

    def load_fevent(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_data_path(FEVENT_PATH),
    ) -> None:
        with stream_or_open_file(file, "rb") as file:
            flat_fevent_offset_table = list(
                itertools.chain.from_iterable(self.fevent_offset_table)
            )
            self.fevent_chunks = []
            for room_id, triple in enumerate(self.fevent_offset_table):
                data: list[bytes] = []
                for triple_index, offset in enumerate(triple):
                    file.seek(offset)
                    index = room_id * 3 + triple_index
                    data.append(
                        file.read(
                            (flat_fevent_offset_table[index + 1] - offset)
                            if index + 1 < len(flat_fevent_offset_table)
                            else 0
                        )
                    )
                    index += 1
                self.fevent_chunks.append(
                    (
                        FEventScript.from_bytes(self, data[0], index=room_id * 3),
                        (
                            FEventScript.from_bytes(
                                self, data[1], index=room_id * 3 + 1
                            )
                            if len(data[1]) > 0
                            else None
                        ),
                        (
                            LanguageTable.from_bytes(
                                data[2], is_dialog=True, index=room_id * 3 + 2
                            )
                            if len(data[2]) > 0
                            else None
                        ),
                    )
                )

            file.seek(self.fevent_footer_offset)
            self.fevent_footer = file.read()

    def load_all(
        self, data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH
    ) -> None:
        self.load_overlay3(fs_std_overlay_path(3, data_dir=data_dir))
        self.load_overlay6(fs_std_overlay_path(6, data_dir=data_dir))
        self.load_fevent(fs_std_data_path(FEVENT_PATH, data_dir=data_dir))

    def save_overlay3(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_overlay_path(3),
    ) -> None:
        with stream_or_open_file(file, "r+b") as file:
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

    def save_overlay6(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_overlay_path(6),
    ) -> None:
        with stream_or_open_file(file, "r+b") as file:
            overlay6_raw = bytearray(file.read())

            self.save_command_metadata_table(
                overlay6_raw,
                FEVENT_COMMAND_METADATA_TABLE_ADDRESS,
                FEVENT_NUMBER_OF_COMMANDS,
            )

            file.seek(0)
            file.truncate()
            file.write(overlay6_raw)

    def save_fevent(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_data_path(FEVENT_PATH),
    ) -> None:
        with stream_or_open_file(file, "wb") as file:
            self.fevent_offset_table = []
            for triple in self.fevent_chunks:
                offset_triple: tuple[int, ...] = ()
                for chunk in triple:
                    offset_triple += (file.tell(),)
                    if isinstance(chunk, FEventScript):
                        file.write(chunk.to_bytes(self))
                        file.write(b"\x00" * ((-file.tell()) % SCRIPT_ALIGNMENT))
                    elif isinstance(chunk, LanguageTable):
                        file.write(chunk.to_bytes())
                self.fevent_offset_table.append(
                    typing.cast(tuple[int, int, int], offset_triple)
                )

            self.fevent_footer_offset = file.tell()
            file.write(self.fevent_footer)

    def save_all(
        self, data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH
    ) -> None:
        self.save_fevent(fs_std_data_path(FEVENT_PATH, data_dir=data_dir))
        self.save_overlay6(fs_std_overlay_path(6, data_dir=data_dir))
        self.save_overlay3(fs_std_overlay_path(3, data_dir=data_dir))


class BattleScriptManager(MnLScriptManager):
    battle_offset_tables: dict[int, list[int]]
    battle_scripts_files: dict[int, list[BattleScript]]
    battle_scripts_files_footer_offsets: dict[int, int]
    battle_scripts_files_footers: dict[int, bytes]

    def __init__(
        self, data_dir: str | os.PathLike[str] | None = DEFAULT_DATA_DIR_PATH
    ) -> None:
        super().__init__()

        if data_dir is not None:
            self.load_all(data_dir)
        else:
            self.battle_offset_tables = {}
            self.battle_scripts_files = {}
            self.battle_scripts_files_footer_offsets = {}
            self.battle_scripts_files_footers = {}

    def load_overlay12(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_overlay_path(12),
    ) -> None:
        with stream_or_open_file(file, "rb") as file:
            file.seek(BATTLE_COMMAND_METADATA_TABLE_ADDRESS)
            self.load_command_metadata_table(file, BATTLE_NUMBER_OF_COMMANDS)

    def load_overlay14(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_overlay_path(14),
    ) -> None:
        with stream_or_open_file(file, "rb") as file:
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

    def load_battle_scripts_file(
        self, address: int, file: typing.BinaryIO | str | os.PathLike[str]
    ) -> None:
        with stream_or_open_file(file, "rb") as file:
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

    def load_all_battle_scripts_files(
        self,
        directory: str | os.PathLike[str] = fs_std_data_path(
            BATTLE_SCRIPTS_DIRECTORY_NAME
        ),
    ) -> None:
        self.battle_scripts_files = {}
        self.battle_scripts_files_footers = {}
        for address in self.battle_offset_tables.keys():
            self.load_battle_scripts_file(
                address,
                pathlib.Path(
                    directory, BATTLE_SCRIPTS_FILES_METADATA[address].filename
                ),
            )

    def load_all(
        self, data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH
    ) -> None:
        self.load_overlay12(fs_std_overlay_path(12, data_dir=data_dir))
        self.load_overlay14(fs_std_overlay_path(14, data_dir=data_dir))
        self.load_all_battle_scripts_files(
            fs_std_data_path(BATTLE_SCRIPTS_DIRECTORY_NAME, data_dir=data_dir)
        )

    def save_overlay12(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_overlay_path(12),
    ) -> None:
        with stream_or_open_file(file, "r+b") as file:
            overlay12_raw = bytearray(file.read())

            self.save_command_metadata_table(
                overlay12_raw,
                BATTLE_COMMAND_METADATA_TABLE_ADDRESS,
                BATTLE_NUMBER_OF_COMMANDS,
            )

            file.seek(0)
            file.truncate()
            file.write(overlay12_raw)

    def save_overlay14(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_overlay_path(14),
    ) -> None:
        with stream_or_open_file(file, "r+b") as file:
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

    def save_battle_scripts_file(
        self, address: int, file: typing.BinaryIO | str | os.PathLike[str]
    ) -> None:
        with stream_or_open_file(file, "wb") as file:
            self.battle_offset_tables[address] = []
            for script in self.battle_scripts_files[address]:
                self.battle_offset_tables[address].append(file.tell())
                file.write(script.to_bytes(self))
                file.write(b"\x00" * ((-file.tell()) % SCRIPT_ALIGNMENT))

            self.battle_scripts_files_footer_offsets[address] = file.tell()
            file.write(self.battle_scripts_files_footers[address])

    def save_all_battle_scripts_files(
        self,
        directory: str | os.PathLike[str] = fs_std_data_path(
            BATTLE_SCRIPTS_DIRECTORY_NAME
        ),
    ) -> None:
        for address in self.battle_scripts_files.keys():
            self.save_battle_scripts_file(
                address,
                pathlib.Path(
                    directory, BATTLE_SCRIPTS_FILES_METADATA[address].filename
                ),
            )

    def save_all(
        self, data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH
    ) -> None:
        self.save_all_battle_scripts_files(
            fs_std_data_path(BATTLE_SCRIPTS_DIRECTORY_NAME, data_dir=data_dir)
        )
        self.save_overlay14(fs_std_overlay_path(14, data_dir=data_dir))
        self.save_overlay12(fs_std_overlay_path(12, data_dir=data_dir))


class MenuScriptManager(MnLScriptManager):
    def __init__(
        self, data_dir: str | os.PathLike[str] | None = DEFAULT_DATA_DIR_PATH
    ) -> None:
        super().__init__()

        if data_dir is not None:
            self.load_all(data_dir)

    def load_overlay123(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_overlay_path(123),
    ) -> None:
        with stream_or_open_file(file, "rb") as file:
            file.seek(MENU_COMMAND_METADATA_TABLE_ADDRESS)
            self.load_command_metadata_table(file, MENU_NUMBER_OF_COMMANDS)

    def load_all(
        self, data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH
    ) -> None:
        self.load_overlay123(fs_std_overlay_path(123, data_dir=data_dir))

    def save_overlay123(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_overlay_path(123),
    ) -> None:
        with stream_or_open_file(file, "r+b") as file:
            overlay123_raw = bytearray(file.read())

            self.save_command_metadata_table(
                overlay123_raw,
                MENU_COMMAND_METADATA_TABLE_ADDRESS,
                MENU_NUMBER_OF_COMMANDS,
            )

            file.seek(0)
            file.truncate()
            file.write(overlay123_raw)

    def save_all(
        self, data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH
    ) -> None:
        self.save_overlay123(fs_std_overlay_path(123, data_dir=data_dir))


class ShopScriptManager(MnLScriptManager):
    def __init__(
        self, data_dir: str | os.PathLike[str] | None = DEFAULT_DATA_DIR_PATH
    ) -> None:
        super().__init__()

        if data_dir is not None:
            self.load_all(data_dir)

    def load_overlay124(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_overlay_path(124),
    ) -> None:
        with stream_or_open_file(file, "rb") as file:
            file.seek(SHOP_COMMAND_METADATA_TABLE_ADDRESS)
            self.load_command_metadata_table(file, SHOP_NUMBER_OF_COMMANDS)

    def load_all(
        self, data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH
    ) -> None:
        self.load_overlay124(fs_std_overlay_path(124, data_dir=data_dir))

    def save_overlay124(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_overlay_path(124),
    ) -> None:
        with stream_or_open_file(file, "r+b") as file:
            overlay124_raw = bytearray(file.read())

            self.save_command_metadata_table(
                overlay124_raw,
                SHOP_COMMAND_METADATA_TABLE_ADDRESS,
                SHOP_NUMBER_OF_COMMANDS,
            )

            file.seek(0)
            file.truncate()
            file.write(overlay124_raw)

    def save_all(
        self, data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH
    ) -> None:
        self.save_overlay124(fs_std_overlay_path(124, data_dir=data_dir))
