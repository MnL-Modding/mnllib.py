from __future__ import annotations

import io
import math
import os
import struct
import typing
from typing import override
import warnings

from ..consts import MNL_DEBUG_MESSAGE_ENCODING
from ..misc import MnLLibWarning
from ..script import ArrayCommand, Subroutine
from ..utils import read_length_prefixed_array

if typing.TYPE_CHECKING:
    from .managers import BattleScriptManager, FEventScriptManager


class FEventScriptHeader:
    index: int | None

    init_subroutine: int | None
    unk_0x04: int
    triggers: list[tuple[int, int, int, int, int, int, int]]
    sprite_groups: list[int]
    sprite_groups_unk1: int
    palettes: list[int]
    palettes_unk1: int
    particle_effects: list[int]
    visual_effects: list[int]
    actors: list[tuple[int, int, int, int, int]]
    array5: list[int]
    subroutine_table: list[int]
    post_table_subroutine: Subroutine

    def __init__(
        self,
        index: int | None = None,
        *,
        init_subroutine: int | None = None,
        unk_0x04: int = 0,
        triggers: list[tuple[int, int, int, int, int, int, int]] | None = None,
        sprite_groups: list[int],
        sprite_groups_unk1: int,
        palettes: list[int],
        palettes_unk1: int,
        particle_effects: list[int],
        visual_effects: list[int],
        actors: list[tuple[int, int, int, int, int]],
        array5: list[int],
        subroutine_table: list[int] = [],
        post_table_subroutine: Subroutine | None = None,
    ) -> None:
        self.index = index

        self.init_subroutine = init_subroutine
        self.unk_0x04 = unk_0x04
        self.triggers = triggers if triggers is not None else []
        self.sprite_groups = sprite_groups
        self.sprite_groups_unk1 = sprite_groups_unk1
        self.palettes = palettes
        self.palettes_unk1 = palettes_unk1
        self.particle_effects = particle_effects
        self.visual_effects = visual_effects
        self.actors = actors
        self.array5 = array5
        self.subroutine_table = subroutine_table
        self.post_table_subroutine = (
            post_table_subroutine
            if post_table_subroutine is not None
            else Subroutine([])
        )

    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    @classmethod
    def from_stream(
        cls,
        manager: FEventScriptManager,
        stream: typing.BinaryIO,
        index: int | None = None,
    ) -> typing.Self:
        init_subroutine, unk_0x04 = struct.unpack("<II", stream.read(4 * 2))
        section1_offset, section2_offset, section3_offset, section4_offset = (
            struct.unpack("<IIII", stream.read(4 * 4))
        )
        if section1_offset == 0:
            section1_offset = section2_offset

        if stream.tell() != section1_offset:
            warnings.warn(
                f"There are extra bytes between the beginning and 1st section of the {
                    f"header of script {index}"
                    if index is not None
                    else "script header"
                }!",
                MnLLibWarning,
            )
            stream.seek(section1_offset)
        if section2_offset != section1_offset:
            triggers = read_length_prefixed_array(stream, "<IIIIIII")
        else:
            triggers = []

        if stream.tell() != section2_offset:
            warnings.warn(
                f"There are extra bytes between the 1st and 2nd section of the {
                    f"header of script {index}"
                    if index is not None
                    else "script header"
                }!",
                MnLLibWarning,
            )
            stream.seek(section2_offset)
        (sprite_groups_len_plus_one,) = struct.unpack("<I", stream.read(4))
        sprite_groups = [
            struct.unpack("<I", stream.read(4))[0]
            for _ in range(sprite_groups_len_plus_one - 1)
        ]
        (sprite_groups_unk1,) = struct.unpack("<I", stream.read(4))
        (palettes_len_plus_one,) = struct.unpack("<I", stream.read(4))
        palettes = [
            struct.unpack("<I", stream.read(4))[0]
            for _ in range(palettes_len_plus_one - 1)
        ]
        (palettes_unk1,) = struct.unpack("<I", stream.read(4))
        particle_effects = read_length_prefixed_array(stream, "<H", "<H")
        stream.seek(math.ceil(stream.tell() / 4) * 4 + 4)
        visual_effects = read_length_prefixed_array(stream, "<H", "<H")

        stream.seek(section3_offset)
        actors = read_length_prefixed_array(stream, "<IIIII")

        if stream.tell() != section4_offset:
            warnings.warn(
                f"There are extra bytes between the 3rd and 4th section of the {
                    f"header of script {index}"
                    if index is not None
                    else "script header"
                }!",
                MnLLibWarning,
            )
            stream.seek(section4_offset)
        array5 = read_length_prefixed_array(stream, "<H", "<H")
        subroutine_table: list[int] = []
        post_table_subroutine = Subroutine([])
        while (
            (stream.tell() - section4_offset < subroutine_table[0])
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
                            subroutine_table[0] - stream.tell() + section4_offset
                        )
                    ),
                )
                break
            subroutine_table.append(offset)
        subroutine_base_offset = stream.tell() - section4_offset
        subroutine_table = [
            offset - subroutine_base_offset for offset in subroutine_table
        ]

        return cls(
            index,
            init_subroutine=init_subroutine,
            unk_0x04=unk_0x04,
            triggers=triggers,
            sprite_groups=sprite_groups,
            sprite_groups_unk1=sprite_groups_unk1,
            palettes=palettes,
            palettes_unk1=palettes_unk1,
            particle_effects=particle_effects,
            visual_effects=visual_effects,
            actors=actors,
            array5=array5,
            subroutine_table=subroutine_table,
            post_table_subroutine=post_table_subroutine,
        )

    def to_bytes(self, manager: FEventScriptManager) -> bytes:
        data_io = io.BytesIO()

        section1_empty = len(self.triggers) <= 0 and (
            self.index is not None and self.index % 3 != 0
        )
        if self.init_subroutine is None:
            raise TypeError("init_subroutine must not be None")
        data_io.write(struct.pack("<II", self.init_subroutine, self.unk_0x04))
        section1_offset = 0x18
        section2_offset = section1_offset + (
            4 + len(self.triggers) * 4 * 7 if not section1_empty else 0
        )
        section3_offset = (
            section2_offset
            + (2 + len(self.sprite_groups)) * 4
            + (2 + len(self.palettes)) * 4
            + math.ceil((1 + len(self.particle_effects)) * 2 / 4) * 4
            + 4
            + math.ceil((1 + len(self.visual_effects)) * 2 / 4) * 4
        )
        section4_offset = section3_offset + 4 + len(self.actors) * 4 * 5
        post_table_subroutine_offset = (
            section4_offset + 2 + len(self.array5) * 2 + len(self.subroutine_table) * 2
        )
        post_table_subroutine_raw = self.post_table_subroutine.to_bytes(
            manager, post_table_subroutine_offset
        )
        header_end_offset = post_table_subroutine_offset + len(
            post_table_subroutine_raw
        )
        data_io.write(
            struct.pack(
                "<IIII",
                section1_offset if not section1_empty else 0,
                section2_offset,
                section3_offset,
                section4_offset,
            )
        )
        if not section1_empty:
            data_io.write(struct.pack("<I", len(self.triggers)))
            for triggers_elements in self.triggers:
                data_io.write(struct.pack("<IIIIIII", *triggers_elements))

        data_io.write(struct.pack("<I", len(self.sprite_groups) + 1))
        data_io.write(struct.pack(f"<{len(self.sprite_groups)}I", *self.sprite_groups))
        data_io.write(struct.pack("<I", self.sprite_groups_unk1))
        data_io.write(struct.pack("<I", len(self.palettes) + 1))
        data_io.write(struct.pack(f"<{len(self.palettes)}I", *self.palettes))
        data_io.write(struct.pack("<I", self.palettes_unk1))
        data_io.write(struct.pack("<H", len(self.particle_effects)))
        data_io.write(
            struct.pack(f"<{len(self.particle_effects)}H", *self.particle_effects)
        )
        data_io.write(b"\xff" * ((-data_io.tell()) % 4))
        data_io.write(b"\x00\x00\xff\xff")
        data_io.write(struct.pack("<H", len(self.visual_effects)))
        data_io.write(
            struct.pack(f"<{len(self.visual_effects)}H", *self.visual_effects)
        )
        data_io.write(b"\xff" * ((-data_io.tell()) % 4))

        data_io.write(struct.pack("<I", len(self.actors)))
        for actors_elements in self.actors:
            data_io.write(struct.pack("<IIIII", *actors_elements))

        data_io.write(struct.pack("<H", len(self.array5)))
        data_io.write(struct.pack(f"<{len(self.array5)}H", *self.array5))
        subroutine_base_offset = header_end_offset - section4_offset
        for offset in self.subroutine_table:
            data_io.write(struct.pack("<H", offset + subroutine_base_offset))
        data_io.write(post_table_subroutine_raw)

        return data_io.getvalue()


class FEventScript:
    index: int | None
    header: FEventScriptHeader
    subroutines: list[Subroutine]
    debug_messages: list[str]

    def __init__(
        self,
        header: FEventScriptHeader,
        subroutines: list[Subroutine],
        debug_messages: list[str] | None = None,
        index: int | None = None,
    ) -> None:
        self.index = index
        self.header = header
        self.subroutines = subroutines
        self.debug_messages = debug_messages if debug_messages is not None else []

    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    @classmethod
    def from_bytes(
        cls, manager: FEventScriptManager, data: bytes, index: int | None = None
    ) -> typing.Self:
        data_io = io.BytesIO(data)
        header = FEventScriptHeader.from_stream(manager, data_io, index)

        subroutine_base_offset = data_io.tell()
        subroutines: list[Subroutine] = []
        debug_messages: list[str] = []
        for i, offset in enumerate(header.subroutine_table):
            subroutine = Subroutine.from_stream(
                manager,
                io.BytesIO(
                    data[
                        subroutine_base_offset
                        + offset : (
                            (subroutine_base_offset + header.subroutine_table[i + 1])
                            if i + 1 < len(header.subroutine_table)
                            else None
                        )
                    ]
                ),
            )

            if len(subroutine.commands) > 0 and isinstance(
                subroutine.commands[0], ArrayCommand
            ):
                last_subroutine = (
                    subroutines[-1] if i > 0 else header.post_table_subroutine
                )
                last_subroutine.footer = last_subroutine.footer.rstrip(b"\xff")

            if i == len(header.subroutine_table) - 1:
                try:
                    debug_messages = (
                        subroutine.footer.rstrip(b"\x00")
                        .decode(MNL_DEBUG_MESSAGE_ENCODING)
                        .split("\x00")
                    )
                except UnicodeDecodeError:
                    pass
                else:
                    if debug_messages == [""]:
                        del debug_messages[0]
                    subroutine.footer = b""

            subroutines.append(subroutine)

        return cls(header, subroutines, debug_messages, index)

    def to_bytes(self, manager: FEventScriptManager) -> bytes:
        self.header.subroutine_table = [0] * len(self.subroutines)
        offset = len(self.header.to_bytes(manager))
        subroutines_raw = io.BytesIO()
        for i, subroutine in enumerate(self.subroutines):
            if len(subroutine.commands) > 0 and isinstance(
                subroutine.commands[0], ArrayCommand
            ):
                offset += subroutines_raw.write(b"\xff" * ((-offset) % 4))
            self.header.subroutine_table[i] = subroutines_raw.tell()
            offset += subroutines_raw.write(subroutine.to_bytes(manager, offset))

        return (
            self.header.to_bytes(manager)
            + subroutines_raw.getvalue()
            + "".join([x + "\x00" for x in self.debug_messages]).encode(
                MNL_DEBUG_MESSAGE_ENCODING
            )
        )


class BattleScript:
    index: int | None
    post_table_subroutine: Subroutine
    other_subroutines: list[Subroutine | None]
    other_subroutines_body_order: list[int]
    main_subroutine: Subroutine
    debug_messages: list[str]

    def __init__(
        self,
        other_subroutines: list[Subroutine | None],
        main_subroutine: Subroutine,
        index: int | None = None,
        post_table_subroutine: Subroutine = Subroutine([]),
        debug_messages: list[str] | None = None,
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
        self.debug_messages = debug_messages if debug_messages is not None else []

    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

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
            subroutine = Subroutine.from_stream(
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

            if (
                i > 0
                and other_subroutines[-1] is not None
                and len(subroutine.commands) > 0
                and isinstance(subroutine.commands[0], ArrayCommand)
            ):
                other_subroutines[-1].footer = other_subroutines[-1].footer.rstrip(
                    b"\xff"
                )

            other_subroutines.append(subroutine)

        if main_subroutine_offset != 0:
            data_io.seek(2 + main_subroutine_offset)
        main_subroutine = Subroutine.from_stream(manager, data_io)
        try:
            debug_messages = (
                main_subroutine.footer.rstrip(b"\x00")
                .decode(MNL_DEBUG_MESSAGE_ENCODING)
                .split("\x00")
            )
        except UnicodeDecodeError:
            debug_messages = []
        else:
            if debug_messages == [""]:
                del debug_messages[0]
            main_subroutine.footer = b""

        return cls(
            other_subroutines,
            main_subroutine,
            index,
            post_table_subroutine,
            debug_messages,
            other_subroutines_body_order,
        )

    def to_bytes(self, manager: BattleScriptManager) -> bytes:
        num_other_subroutines = len(self.other_subroutines)
        absolute_offset = (2 + num_other_subroutines) * 2

        subroutines_raw = io.BytesIO()
        absolute_offset += subroutines_raw.write(
            self.post_table_subroutine.to_bytes(manager, absolute_offset)
        )

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

            if len(subroutine.commands) > 0 and isinstance(
                subroutine.commands[0], ArrayCommand
            ):
                absolute_offset += subroutines_raw.write(
                    b"\xff" * ((-absolute_offset) % 4)
                )
            other_subroutine_offsets[i] = (
                num_other_subroutines - i
            ) * 2 + subroutines_raw.tell()
            absolute_offset += subroutines_raw.write(
                subroutine.to_bytes(manager, absolute_offset)
            )

        if len(self.main_subroutine.commands) > 0 and isinstance(
            self.main_subroutine.commands[0], ArrayCommand
        ):
            absolute_offset += subroutines_raw.write(b"\xff" * ((-absolute_offset) % 4))
        main_subroutine_offset = (
            (1 + num_other_subroutines) * 2 + subroutines_raw.tell()
            if subroutines_raw.tell() != 0
            else 0
        )
        subroutines_raw.write(self.main_subroutine.to_bytes(manager, absolute_offset))

        return (
            struct.pack(
                f"<{2 + num_other_subroutines}H",
                num_other_subroutines + 1,
                main_subroutine_offset,
                *other_subroutine_offsets,
            )
            + subroutines_raw.getvalue()
            + "".join([x + "\x00" for x in self.debug_messages]).encode(
                MNL_DEBUG_MESSAGE_ENCODING
            )
        )
