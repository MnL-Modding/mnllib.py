from __future__ import annotations

import io
import os
import struct
import typing
import warnings

from ..misc import MnLLibWarning
from ..script import Subroutine
from ..utils import read_length_prefixed_array

if typing.TYPE_CHECKING:
    from .managers import FEventScriptManager


class FEventScriptHeader:
    index: int | None

    unk_0x00: bytes
    offsets_unk1: bytes
    array1: list[int]
    array2: list[int]
    section1_unk1: bytes
    array3: list[tuple[int, int, int, int, int]]
    array4: list[int]
    subroutine_table: list[int]
    post_table_subroutine: Subroutine

    def __init__(
        self,
        index: int | None = None,
        *,
        unk_0x00: bytes,
        offsets_unk1: bytes,
        array1: list[int],
        array2: list[int],
        section1_unk1: bytes,
        array3: list[tuple[int, int, int, int, int]],
        array4: list[int],
        subroutine_table: list[int] = [],
        post_table_subroutine: Subroutine | None = None,
    ) -> None:
        self.index = index

        self.unk_0x00 = unk_0x00
        self.offsets_unk1 = offsets_unk1
        self.array1 = array1
        self.array2 = array2
        self.section1_unk1 = section1_unk1
        self.array3 = array3
        self.array4 = array4
        self.subroutine_table = subroutine_table
        self.post_table_subroutine = (
            post_table_subroutine
            if post_table_subroutine is not None
            else Subroutine([])
        )

    @classmethod
    def from_stream(
        cls,
        manager: FEventScriptManager,
        stream: typing.BinaryIO,
        index: int | None = None,
    ) -> typing.Self:
        unk_0x00 = stream.read(12)
        section1_offset, section2_offset, section3_offset = struct.unpack(
            "<III", stream.read(4 * 3)
        )
        offsets_unk1 = stream.read(section1_offset - stream.tell())

        array1 = read_length_prefixed_array(stream, "<I")
        array2 = read_length_prefixed_array(stream, "<H", "<H")
        section1_unk1 = stream.read(section2_offset - stream.tell())

        array3 = read_length_prefixed_array(stream, "<IIIIII")

        if stream.tell() != section3_offset:
            warnings.warn(
                f"There are extra bytes between the 2nd and 3rd section of the {
                    f"header of script {index}"
                    if index is not None
                    else "script header"
                }!",
                MnLLibWarning,
            )
            stream.seek(section3_offset)
        array4 = read_length_prefixed_array(stream, "<I")
        subroutine_table: list[int] = []
        post_table_subroutine = Subroutine([])
        while (
            (stream.tell() - section3_offset < subroutine_table[0])
            if len(subroutine_table) > 0
            else True
        ):
            offset_data = stream.read(4)
            if offset_data == b"":
                break
            (offset,) = struct.unpack("<I", offset_data)
            if offset <= stream.tell() - 4 - section3_offset or (
                len(subroutine_table) > 0 and offset < subroutine_table[-1]
            ):
                stream.seek(-4, os.SEEK_CUR)
                post_table_subroutine = Subroutine.from_stream(
                    manager,
                    io.BytesIO(
                        stream.read(
                            subroutine_table[0] - stream.tell() + section3_offset
                            if len(subroutine_table) > 0
                            else -1
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
            array2=array2,
            section1_unk1=section1_unk1,
            array3=array3,
            array4=array4,
            subroutine_table=subroutine_table,
            post_table_subroutine=post_table_subroutine,
        )

    def to_bytes(self, manager: FEventScriptManager) -> bytes:
        data_io = io.BytesIO()

        data_io.write(self.unk_0x00)
        section1_offset = 0x18 + len(self.offsets_unk1)
        section2_offset = (
            section1_offset
            + (1 + len(self.array1)) * 4
            + (1 + len(self.array2)) * 2
            + len(self.section1_unk1)
        )
        section3_offset = section2_offset + 4 + len(self.array3) * 24
        post_table_subroutine_raw = self.post_table_subroutine.to_bytes(manager)
        header_end_offset = (
            section3_offset
            + 4
            + len(self.array4) * 4
            + len(self.subroutine_table) * 4
            + len(post_table_subroutine_raw)
        )
        data_io.write(
            struct.pack("<III", section1_offset, section2_offset, section3_offset)
        )
        data_io.write(self.offsets_unk1)

        data_io.write(struct.pack("<I", len(self.array1)))
        data_io.write(struct.pack(f"<{len(self.array1)}I", *self.array1))
        data_io.write(struct.pack("<H", len(self.array2)))
        data_io.write(struct.pack(f"<{len(self.array2)}H", *self.array2))
        data_io.write(self.section1_unk1)

        data_io.write(struct.pack("<I", len(self.array3)))
        for elements in self.array3:
            data_io.write(struct.pack("<IIIIII", *elements))

        data_io.write(struct.pack("<I", len(self.array4)))
        data_io.write(struct.pack(f"<{len(self.array4)}I", *self.array4))
        subroutine_base_offset = header_end_offset - section3_offset
        for offset in self.subroutine_table:
            data_io.write(struct.pack("<I", offset + subroutine_base_offset))
        data_io.write(post_table_subroutine_raw)

        return data_io.getvalue()


class FEventScript:
    index: int | None
    header: FEventScriptHeader
    subroutines: list[Subroutine]

    def __init__(
        self,
        header: FEventScriptHeader,
        subroutines: list[Subroutine],
        index: int | None = None,
    ) -> None:
        self.index = index
        self.header = header
        self.subroutines = subroutines

    @classmethod
    def from_bytes(
        cls, manager: FEventScriptManager, data: bytes, index: int | None = None
    ) -> typing.Self:
        data_io = io.BytesIO(data)
        header = FEventScriptHeader.from_stream(manager, data_io, index)

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

        return cls(header, subroutines, index)

    def to_bytes(self, manager: FEventScriptManager) -> bytes:
        subroutines_raw = io.BytesIO()
        self.header.subroutine_table = []
        for subroutine in self.subroutines:
            self.header.subroutine_table.append(subroutines_raw.tell())
            subroutines_raw.write(subroutine.to_bytes(manager))

        return self.header.to_bytes(manager) + subroutines_raw.getvalue()
