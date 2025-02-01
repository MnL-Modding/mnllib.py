import pathlib
import struct
import typing
import warnings

from ..managers import MnLScriptManager
from ..misc import MnLLibWarning
from .consts import (
    CODE_BIN_PATH,
    COMMAND_PARAMETER_STRUCT_MAP,
    FEVENT_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS,
    FEVENT_FILE_NAME,
    FEVENT_NUMBER_OF_COMMANDS,
    FEVENT_OFFSET_TABLE_ADDRESS,
    FEVENT_OFFSET_TABLE_LENGTH_ADDRESS,
    FEVENT_SCRIPT_ALIGNMENT,
)
from .script import FEventScript


class FEventScriptManager(MnLScriptManager):
    fevent_offset_table: list[tuple[tuple[int, int], tuple[int, int]]]
    fevent_scripts: list[tuple[FEventScript, FEventScript | None]]

    def __init__(self, load: bool = True) -> None:
        super().__init__(
            command_parameter_metadata_struct_map=COMMAND_PARAMETER_STRUCT_MAP
        )

        if load:
            self.load_all()
        else:
            self.fevent_offset_table = []
            self.fevent_scripts = []

    def load_code_bin(
        self,
        file: typing.BinaryIO | pathlib.Path | str = f"data/{CODE_BIN_PATH}",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "rb")
            close_file = True

        try:
            file.seek(FEVENT_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS)
            self.load_command_parameter_metadata_table(file, FEVENT_NUMBER_OF_COMMANDS)

            file.seek(FEVENT_OFFSET_TABLE_LENGTH_ADDRESS + 8)
            fevent_offset_table_length = struct.unpack("<I", file.read(4))[0] // 8 - 2
            if fevent_offset_table_length % 2 != 0:
                warnings.warn(
                    "The length of the FEvent offset table "
                    f"({fevent_offset_table_length}) is not even!",
                    MnLLibWarning,
                )
            file.seek(FEVENT_OFFSET_TABLE_ADDRESS)
            self.fevent_offset_table = []
            for _ in range(fevent_offset_table_length // 2):
                self.fevent_offset_table.append(
                    (
                        struct.unpack("<II", file.read(4 * 2)),
                        struct.unpack("<II", file.read(4 * 2)),
                    )
                )
        finally:
            if close_file:
                file.close()

    def load_fevent(
        self,
        file: typing.BinaryIO | pathlib.Path | str = f"data/romfs/{FEVENT_FILE_NAME}",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "rb")
            close_file = True

        try:
            self.fevent_scripts = []
            for i, (first_offset, second_offset) in enumerate(self.fevent_offset_table):
                file.seek(first_offset[0])
                first = FEventScript.from_bytes(
                    self, file.read(first_offset[1]), index=i * 2
                )
                if second_offset[1] != 0:
                    file.seek(second_offset[0])
                    second = FEventScript.from_bytes(
                        self, file.read(second_offset[1]), index=i * 2 + 1
                    )
                else:
                    second = None
                self.fevent_scripts.append((first, second))
        finally:
            if close_file:
                file.close()

    def load_all(self) -> None:
        self.load_code_bin()
        self.load_fevent()

    def save_code_bin(
        self,
        file: typing.BinaryIO | pathlib.Path | str = f"data/{CODE_BIN_PATH}",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "r+b")
            close_file = True

        try:
            code_bin_raw = bytearray(file.read())

            self.save_command_parameter_metadata_table(
                code_bin_raw,
                FEVENT_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS,
                FEVENT_NUMBER_OF_COMMANDS,
            )

            old_fevent_offset_table_length = (
                struct.unpack(
                    "<I",
                    code_bin_raw[
                        FEVENT_OFFSET_TABLE_LENGTH_ADDRESS
                        + 8 : (FEVENT_OFFSET_TABLE_LENGTH_ADDRESS + 12)
                    ],
                )[0]
                // 8
                - 2
            )
            del code_bin_raw[
                FEVENT_OFFSET_TABLE_LENGTH_ADDRESS : FEVENT_OFFSET_TABLE_ADDRESS
                + old_fevent_offset_table_length * 8
            ]
            fevent_offset_table_length = len(self.fevent_offset_table)
            code_bin_raw[
                FEVENT_OFFSET_TABLE_LENGTH_ADDRESS:FEVENT_OFFSET_TABLE_LENGTH_ADDRESS
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
        finally:
            if close_file:
                file.close()

    def save_fevent(
        self,
        file: typing.BinaryIO | pathlib.Path | str = f"data/romfs/{FEVENT_FILE_NAME}",
    ) -> None:
        close_file = False
        if isinstance(file, (pathlib.Path, str)):
            file = open(file, "wb")
            close_file = True

        try:
            self.fevent_offset_table = []
            for first, second in self.fevent_scripts:
                first_offset = file.tell()
                first_len = file.write(first.to_bytes(self))
                file.write(b"\xff" * ((-first_len) % FEVENT_SCRIPT_ALIGNMENT))
                second_offset = file.tell()
                if second is not None:
                    second_len = file.write(second.to_bytes(self))
                    file.write(b"\xff" * ((-second_len) % FEVENT_SCRIPT_ALIGNMENT))
                else:
                    second_len = 0
                self.fevent_offset_table.append(
                    ((first_offset, first_len), (second_offset, second_len))
                )
        finally:
            if close_file:
                file.close()

    def save_all(self) -> None:
        self.save_fevent()
        self.save_code_bin()
