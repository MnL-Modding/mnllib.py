from __future__ import annotations

import struct
import io
import typing

from .managers import MnLScriptManager
from .misc import FEventChunk


class TextTable:
    strings: list[bytes]
    is_dialog: bool
    textbox_sizes: list[tuple[int, int]] | None

    def __init__(
        self,
        strings: list[bytes],
        is_dialog: bool,
        textbox_sizes: list[tuple[int, int]] | None = None,
    ) -> None:
        self.strings = strings
        self.is_dialog = is_dialog
        self.textbox_sizes = textbox_sizes

    @classmethod
    def from_bytes(cls, data: bytes, is_dialog: bool) -> typing.Self:
        data_io = io.BytesIO(data)

        string_offsets: list[int] = []
        while (data_io.tell() < string_offsets[0]) if len(string_offsets) > 0 else True:
            string_offsets.append(struct.unpack("<I", data_io.read(4))[0])

        strings: list[bytes] = []
        if is_dialog:
            textbox_sizes: list[tuple[int, int]] | None = []
        else:
            textbox_sizes = None
        for i, offset in enumerate(string_offsets):
            string_data = data[
                offset : string_offsets[i + 1] if i + 1 < len(string_offsets) else None
            ]
            if is_dialog:
                typing.cast(list[tuple[int, int]], textbox_sizes).append(
                    struct.unpack_from("<BB", string_data)
                )
                string_data = string_data[2:]
            strings.append(string_data)

        return cls(strings, is_dialog, textbox_sizes)

    def to_bytes(self) -> bytes:
        string_offsets_raw = io.BytesIO()
        strings_raw = io.BytesIO()

        base_string_offset = len(self.strings) * 4
        for i, string in enumerate(self.strings):
            string_offsets_raw.write(
                struct.pack("<I", base_string_offset + strings_raw.tell())
            )
            if self.is_dialog:
                strings_raw.write(
                    struct.pack(
                        "<BB",
                        *typing.cast(list[tuple[int, int]], self.textbox_sizes)[i],
                    )
                )
            strings_raw.write(string)

        return string_offsets_raw.getvalue() + strings_raw.getvalue()


class LanguageTable(FEventChunk):
    index: int | None
    text_tables: list[TextTable | bytes | None]

    def __init__(
        self, text_tables: list[TextTable | bytes | None], index: int | None = None
    ) -> None:
        self.index = index
        self.text_tables = text_tables

    @classmethod
    def from_bytes(
        cls, data: bytes, is_dialog: bool, index: int | None = None
    ) -> typing.Self:
        data_io = io.BytesIO(data)

        language_table: list[int] = []
        while (data_io.tell() < language_table[0]) if len(language_table) > 0 else True:
            language_table.append(struct.unpack("<I", data_io.read(4))[0])

        text_tables: list[TextTable | bytes | None] = []
        for i, offset in enumerate(language_table):
            text_table_data = data[
                offset : language_table[i + 1] if i + 1 < len(language_table) else None
            ]
            if len(text_table_data) <= 0:
                text_tables.append(None)
            elif (not is_dialog and i != len(language_table) - 1) or (
                is_dialog and i >= 0x44 and i <= 0x48
            ):
                text_tables.append(TextTable.from_bytes(text_table_data, is_dialog))
            else:
                text_tables.append(text_table_data)

        return cls(text_tables, index)

    def to_bytes(self, manager: MnLScriptManager | None = None) -> bytes:
        text_table_offsets_raw = io.BytesIO()
        text_tables_raw = io.BytesIO()

        base_text_table_offset = len(self.text_tables) * 4
        for text_table in self.text_tables:
            offset = base_text_table_offset + text_tables_raw.tell()
            text_table_offsets_raw.write(struct.pack("<I", offset))
            if isinstance(text_table, TextTable):
                text_tables_raw.write(text_table.to_bytes())
            elif isinstance(text_table, bytes):
                text_tables_raw.write(text_table)

        return text_table_offsets_raw.getvalue() + text_tables_raw.getvalue()
