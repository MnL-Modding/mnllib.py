import os
import struct
import typing
from typing import override
import warnings

from ..consts import DEFAULT_DATA_DIR_PATH
from ..managers import MnLScriptManager
from ..misc import MnLLibWarning
from ..n3ds.consts import fs_std_code_bin_path, fs_std_romfs_path
from ..utils import stream_or_open_file
from .consts import (
    FEVENT_COMMAND_METADATA_TABLE_ADDRESS,
    FEVENT_PATH,
    FEVENT_NUMBER_OF_COMMANDS,
    FEVENT_OFFSET_TABLE_LENGTH_ADDRESS,
    SCRIPT_ALIGNMENT,
)
from .misc import determine_version_from_code_bin
from .script import FEventScript


type FEventScriptPair = tuple[bytes | FEventScript, bytes | FEventScript | None]


class FEventScriptManager(MnLScriptManager):
    fevent_offset_table: list[tuple[tuple[int, int], tuple[int, int]]]
    fevent_scripts: list[FEventScriptPair]

    def __init__(
        self,
        data_dir: str | os.PathLike[str] | None = DEFAULT_DATA_DIR_PATH,
        *,
        parse_all: bool = False,
    ) -> None:
        super().__init__()

        if data_dir is not None:
            self.load_all(data_dir, parse_all=parse_all)
        else:
            self.fevent_offset_table = []
            self.fevent_scripts = []

    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def load_code_bin(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_code_bin_path(),
    ) -> None:
        with stream_or_open_file(file, "rb") as file:
            version_pair = determine_version_from_code_bin(file)

            file.seek(FEVENT_COMMAND_METADATA_TABLE_ADDRESS[version_pair])
            self.load_command_metadata_table(file, FEVENT_NUMBER_OF_COMMANDS)

            file.seek(FEVENT_OFFSET_TABLE_LENGTH_ADDRESS[version_pair] + 8)
            fevent_offset_table_length = struct.unpack("<I", file.read(4))[0] // 8 - 2
            if fevent_offset_table_length % 2 != 0:
                warnings.warn(
                    "The length of the FEvent offset table "
                    f"({fevent_offset_table_length}) is not even!",
                    MnLLibWarning,
                )
            file.seek(4, os.SEEK_CUR)
            self.fevent_offset_table = []
            for _ in range(fevent_offset_table_length // 2):
                self.fevent_offset_table.append(
                    (
                        struct.unpack("<II", file.read(4 * 2)),
                        struct.unpack("<II", file.read(4 * 2)),
                    )
                )

    def load_fevent(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_romfs_path(FEVENT_PATH),
        *,
        parse_all: bool = False,
    ) -> None:
        with stream_or_open_file(file, "rb") as file:
            self.fevent_scripts = []
            for i, (first_offset, second_offset) in enumerate(self.fevent_offset_table):
                file.seek(first_offset[0])
                data = file.read(first_offset[1])
                if parse_all:
                    first: bytes | FEventScript = FEventScript.from_bytes(
                        self, data, index=i * 2
                    )
                else:
                    first = data
                if second_offset[1] != 0:
                    file.seek(second_offset[0])
                    data = file.read(second_offset[1])
                    if parse_all:
                        second: bytes | FEventScript | None = FEventScript.from_bytes(
                            self, data, index=i * 2 + 1
                        )
                    else:
                        second = data
                else:
                    second = None
                self.fevent_scripts.append((first, second))

    def load_all(
        self,
        data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH,
        *,
        parse_all: bool = False,
    ) -> None:
        self.load_code_bin(fs_std_code_bin_path(data_dir=data_dir))
        self.load_fevent(
            fs_std_romfs_path(FEVENT_PATH, data_dir=data_dir), parse_all=parse_all
        )

    def save_code_bin(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_code_bin_path(),
    ) -> None:
        with stream_or_open_file(file, "r+b") as file:
            version_pair = determine_version_from_code_bin(file)

            file.seek(0)
            code_bin_raw = bytearray(file.read())

            self.save_command_metadata_table(
                code_bin_raw,
                FEVENT_COMMAND_METADATA_TABLE_ADDRESS[version_pair],
                FEVENT_NUMBER_OF_COMMANDS,
            )

            fevent_offset_table_length_address = FEVENT_OFFSET_TABLE_LENGTH_ADDRESS[
                version_pair
            ]
            old_fevent_offset_table_length = (
                struct.unpack(
                    "<I",
                    code_bin_raw[
                        fevent_offset_table_length_address
                        + 8 : (fevent_offset_table_length_address + 12)
                    ],
                )[0]
                // 8
                - 2
            )
            del code_bin_raw[
                fevent_offset_table_length_address : fevent_offset_table_length_address
                + 16
                + old_fevent_offset_table_length * 8
            ]
            fevent_offset_table_length = len(self.fevent_offset_table)
            code_bin_raw[
                fevent_offset_table_length_address:fevent_offset_table_length_address
            ] = struct.pack(
                "<HHIIHH",
                0,
                fevent_offset_table_length * 2,
                0,
                (fevent_offset_table_length * 2 + 2) * 8,
                0,
                fevent_offset_table_length * 2 - 1,
            ) + b"".join(
                [
                    struct.pack("<IIII", *first_offset, *second_offset)
                    for first_offset, second_offset in self.fevent_offset_table
                ]
            )

            file.seek(0)
            file.truncate()
            file.write(code_bin_raw)

    def save_fevent(
        self,
        file: typing.BinaryIO | str | os.PathLike[str] = fs_std_romfs_path(FEVENT_PATH),
    ) -> None:
        with stream_or_open_file(file, "wb") as file:
            self.fevent_offset_table = []
            for first, second in self.fevent_scripts:
                first_offset = file.tell()
                first_len = file.write(
                    first.to_bytes(self) if isinstance(first, FEventScript) else first
                )
                file.write(b"\xff" * ((-first_len) % SCRIPT_ALIGNMENT))
                second_offset = file.tell()
                if second is not None:
                    second_len = file.write(
                        second.to_bytes(self)
                        if isinstance(second, FEventScript)
                        else second
                    )
                    file.write(b"\xff" * ((-second_len) % SCRIPT_ALIGNMENT))
                else:
                    second_len = 0
                self.fevent_offset_table.append(
                    ((first_offset, first_len), (second_offset, second_len))
                )

    def save_all(
        self, data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH
    ) -> None:
        self.save_fevent(fs_std_romfs_path(FEVENT_PATH, data_dir=data_dir))
        self.save_code_bin(fs_std_code_bin_path(data_dir=data_dir))

    def parsed_script(
        self, room_id: int, pair_index: int, *, save: bool = True
    ) -> FEventScript | None:
        """
        Parse the given script if it isn't parsed already,
        optionally save the parsed script and return it.
        """
        script = self.fevent_scripts[room_id][pair_index]
        if not isinstance(script, bytes):
            return script

        parsed_script = FEventScript.from_bytes(
            self, script, index=room_id * 2 + pair_index
        )
        if save:
            script_pair = list(self.fevent_scripts[room_id])
            script_pair[pair_index] = parsed_script
            self.fevent_scripts[room_id] = typing.cast(
                FEventScriptPair, tuple(script_pair)
            )
        return parsed_script
