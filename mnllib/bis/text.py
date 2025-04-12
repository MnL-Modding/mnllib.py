import struct
import io
import typing
from typing import override


class TextTable:
    entries: list[bytes]
    is_dialog: bool
    textbox_sizes: list[tuple[int, int]] | None

    def __init__(
        self,
        entries: list[bytes],
        is_dialog: bool,
        textbox_sizes: list[tuple[int, int]] | None = None,
    ) -> None:
        self.entries = entries
        self.is_dialog = is_dialog
        self.textbox_sizes = textbox_sizes

    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    @classmethod
    def from_bytes(cls, data: bytes, is_dialog: bool) -> typing.Self:
        data_io = io.BytesIO(data)

        entry_offsets: list[int] = []
        while (data_io.tell() < entry_offsets[0]) if len(entry_offsets) > 0 else True:
            entry_offsets.append(struct.unpack("<I", data_io.read(4))[0])

        entries: list[bytes] = []
        if is_dialog:
            textbox_sizes: list[tuple[int, int]] | None = []
        else:
            textbox_sizes = None
        for i, offset in enumerate(entry_offsets):
            entry_data = data[
                offset : entry_offsets[i + 1] if i + 1 < len(entry_offsets) else None
            ]
            if is_dialog:
                typing.cast(list[tuple[int, int]], textbox_sizes).append(
                    struct.unpack_from("<BB", entry_data)
                )
                entry_data = entry_data[2:]
            entries.append(entry_data)

        return cls(entries, is_dialog, textbox_sizes)

    def to_bytes(self) -> bytes:
        entry_offsets_raw = io.BytesIO()
        entries_raw = io.BytesIO()

        base_entry_offset = len(self.entries) * 4
        for i, entry in enumerate(self.entries):
            entry_offsets_raw.write(
                struct.pack("<I", base_entry_offset + entries_raw.tell())
            )
            if self.is_dialog:
                entries_raw.write(
                    struct.pack(
                        "<BB",
                        *typing.cast(list[tuple[int, int]], self.textbox_sizes)[i],
                    )
                )
            entries_raw.write(entry)

        return entry_offsets_raw.getvalue() + entries_raw.getvalue()


class LanguageTable:
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
                is_dialog and 0x44 <= i <= 0x48
            ):
                text_tables.append(TextTable.from_bytes(text_table_data, is_dialog))
            else:
                text_tables.append(text_table_data)

        return cls(text_tables, index)

    def to_bytes(self) -> bytes:
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
