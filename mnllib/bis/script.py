from __future__ import annotations

import io
import os
import struct
import typing
import warnings

from ..misc import MnLLibWarning
from ..script import Subroutine
from ..utils import read_length_prefixed_array
from .misc import FEventChunk

if typing.TYPE_CHECKING:
    from .managers import BattleScriptManager, FEventScriptManager


class FEventScriptHeader:
    index: int | None

    unk_0x00: bytes
    offsets_unk1: bytes
    array1: list[int]
    var1: int
    array2: list[int]
    var2: int
    array3: list[int]
    section1_unk1: bytes
    array4: list[tuple[int, int, int, int, int]]
    array5: list[int]
    subroutine_table: list[int]
    post_table_subroutine: Subroutine

    def __init__(
        self,
        index: int | None = None,
        *,
        unk_0x00: bytes,
        offsets_unk1: bytes,
        array1: list[int],
        var1: int,
        array2: list[int],
        var2: int,
        array3: list[int],
        section1_unk1: bytes,
        array4: list[tuple[int, int, int, int, int]],
        array5: list[int],
        subroutine_table: list[int] = [],
        post_table_subroutine: Subroutine | None = None,
    ) -> None:
        self.index = index

        self.unk_0x00 = unk_0x00
        self.offsets_unk1 = offsets_unk1
        self.array1 = array1
        self.var1 = var1
        self.array2 = array2
        self.var2 = var2
        self.array3 = array3
        self.section1_unk1 = section1_unk1
        self.array4 = array4
        self.array5 = array5
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

        (array1_length_plus_one,) = struct.unpack("<I", stream.read(4))
        array1 = [
            struct.unpack("<I", stream.read(4))[0]
            for _ in range(array1_length_plus_one - 1)
        ]
        (var1,) = struct.unpack("<I", stream.read(4))
        (array2_length_plus_one,) = struct.unpack("<I", stream.read(4))
        array2 = [
            struct.unpack("<I", stream.read(4))[0]
            for _ in range(array2_length_plus_one - 1)
        ]
        (var2,) = struct.unpack("<I", stream.read(4))
        array3 = read_length_prefixed_array(stream, "<H", "<H")
        section1_unk1 = stream.read(section2_offset - stream.tell())

        array4 = read_length_prefixed_array(stream, "<IIIII")

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
        array5 = read_length_prefixed_array(stream, "<H", "<H")
        subroutine_table: list[int] = []
        post_table_subroutine = Subroutine([])
        while (
            (stream.tell() - section3_offset < subroutine_table[0])
            if len(subroutine_table) > 0
            else True
        ):
            (offset,) = struct.unpack("<H", stream.read(2))
            if len(subroutine_table) > 0 and offset < subroutine_table[-1]:
                stream.seek(-2, os.SEEK_CUR)
                post_table_subroutine = Subroutine.from_stream(
                    manager,
                    io.BytesIO(
                        stream.read(
                            subroutine_table[0] - stream.tell() + section3_offset
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
            var1=var1,
            array2=array2,
            var2=var2,
            array3=array3,
            section1_unk1=section1_unk1,
            array4=array4,
            array5=array5,
            subroutine_table=subroutine_table,
            post_table_subroutine=post_table_subroutine,
        )

    def to_bytes(self, manager: FEventScriptManager) -> bytes:
        data_io = io.BytesIO()

        data_io.write(self.unk_0x00)
        section1_offset = 0x18 + len(self.offsets_unk1)
        section2_offset = (
            section1_offset
            + (2 + len(self.array1)) * 4
            + (2 + len(self.array2)) * 4
            + (1 + len(self.array3)) * 2
            + len(self.section1_unk1)
        )
        section3_offset = section2_offset + 4 + len(self.array4) * 20
        post_table_subroutine_raw = self.post_table_subroutine.to_bytes(manager)
        header_end_offset = (
            section3_offset
            + 2
            + len(self.array5) * 2
            + len(self.subroutine_table) * 2
            + len(post_table_subroutine_raw)
        )
        data_io.write(
            struct.pack("<III", section1_offset, section2_offset, section3_offset)
        )
        data_io.write(self.offsets_unk1)

        data_io.write(struct.pack("<I", len(self.array1) + 1))
        data_io.write(struct.pack(f"<{len(self.array1)}I", *self.array1))
        data_io.write(struct.pack("<I", self.var1))
        data_io.write(struct.pack("<I", len(self.array2) + 1))
        data_io.write(struct.pack(f"<{len(self.array2)}I", *self.array2))
        data_io.write(struct.pack("<I", self.var2))
        data_io.write(struct.pack("<H", len(self.array3)))
        data_io.write(struct.pack(f"<{len(self.array3)}H", *self.array3))
        data_io.write(self.section1_unk1)

        data_io.write(struct.pack("<I", len(self.array4)))
        for elements in self.array4:
            data_io.write(struct.pack("<IIIII", *elements))

        data_io.write(struct.pack("<H", len(self.array5)))
        data_io.write(struct.pack(f"<{len(self.array5)}H", *self.array5))
        subroutine_base_offset = header_end_offset - section3_offset
        for offset in self.subroutine_table:
            data_io.write(struct.pack("<H", offset + subroutine_base_offset))
        data_io.write(post_table_subroutine_raw)

        return data_io.getvalue()


class FEventScript(FEventChunk):
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


class BattleScript:
    index: int | None
    post_table_subroutine: Subroutine
    other_subroutines: list[Subroutine | None]
    other_subroutines_body_order: list[int]
    main_subroutine: Subroutine

    def __init__(
        self,
        other_subroutines: list[Subroutine | None],
        main_subroutine: Subroutine,
        index: int | None = None,
        post_table_subroutine: Subroutine = Subroutine([]),
        other_subroutines_body_order: list[int] | None = None,
    ) -> None:
        self.index = index
        self.post_table_subroutine = post_table_subroutine
        self.other_subroutines = other_subroutines
        if other_subroutines_body_order is None:
            other_subroutines_body_order = [
                i for i, x in enumerate(other_subroutines) if x is not None
            ]
        self.other_subroutines_body_order = other_subroutines_body_order
        self.main_subroutine = main_subroutine

    @classmethod
    def from_bytes(
        cls, manager: BattleScriptManager, data: bytes, index: int | None = None
    ) -> typing.Self:
        data_io = io.BytesIO(data)
        num_offsets, main_subroutine_offset = struct.unpack("<HH", data_io.read(4))
        num_other_subroutines = num_offsets - 1
        other_subroutine_offsets = struct.unpack(
            f"<{num_other_subroutines}H", data_io.read(num_other_subroutines * 2)
        )
        other_subroutines_body_order = sorted(
            range(len(other_subroutine_offsets)),
            key=lambda x: other_subroutine_offsets[x],
        )[other_subroutine_offsets.count(0) :]

        if len(other_subroutines_body_order) > 0:
            post_table_subroutine = Subroutine.from_stream(
                manager,
                io.BytesIO(
                    data[
                        2
                        + num_offsets * 2 : 4
                        + other_subroutines_body_order[0] * 2
                        + other_subroutine_offsets[other_subroutines_body_order[0]]
                    ]
                ),
            )
        else:
            post_table_subroutine = Subroutine([])

        other_subroutines: list[Subroutine | None] = []
        for i, offset in enumerate(other_subroutine_offsets):
            if offset == 0:
                other_subroutines.append(None)
                continue

            try:
                next_body_order_subroutine_index = other_subroutines_body_order[
                    other_subroutines_body_order.index(i) + 1
                ]
            except IndexError:
                next_body_order_subroutine_index = None
            other_subroutines.append(
                Subroutine.from_stream(
                    manager,
                    io.BytesIO(
                        data[
                            4
                            + i * 2
                            + offset : (
                                (
                                    4
                                    + next_body_order_subroutine_index * 2
                                    + other_subroutine_offsets[
                                        next_body_order_subroutine_index
                                    ]
                                )
                                if next_body_order_subroutine_index is not None
                                else 2 + main_subroutine_offset
                            )
                        ]
                    ),
                )
            )

        if main_subroutine_offset != 0:
            data_io.seek(2 + main_subroutine_offset)
        main_subroutine = Subroutine.from_stream(manager, data_io)

        return cls(
            other_subroutines,
            main_subroutine,
            index,
            post_table_subroutine,
            other_subroutines_body_order,
        )

    def to_bytes(self, manager: BattleScriptManager) -> bytes:
        subroutines_raw = io.BytesIO()
        subroutines_raw.write(self.post_table_subroutine.to_bytes(manager))

        num_other_subroutines = len(self.other_subroutines)
        other_subroutine_offsets: list[int] = [0] * num_other_subroutines
        for i in self.other_subroutines_body_order:
            subroutine = self.other_subroutines[i]
            if subroutine is None:
                raise TypeError(
                    f"subroutine (with index {i}{
                        f" of script {self.index}"
                        if self.index is not None
                        else ""
                    }) specified in 'self.other_subroutines_body_order' "
                    "must not be None"
                )

            other_subroutine_offsets[i] = (
                num_other_subroutines - i
            ) * 2 + subroutines_raw.tell()
            subroutines_raw.write(subroutine.to_bytes(manager))

        main_subroutine_offset = (
            (1 + num_other_subroutines) * 2 + subroutines_raw.tell()
            if subroutines_raw.tell() != 0
            else 0
        )
        subroutines_raw.write(self.main_subroutine.to_bytes(manager))

        return (
            struct.pack(
                f"<{num_other_subroutines + 2}H",
                num_other_subroutines + 1,
                main_subroutine_offset,
                *other_subroutine_offsets,
            )
            + subroutines_raw.getvalue()
        )
