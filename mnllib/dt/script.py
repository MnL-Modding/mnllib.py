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
    from .managers import FEventScriptManager


class FEventScriptHeader:
    index: int | None

    init_subroutine: int | None
    unk_0x04: int
    triggers: list[tuple[int, int, int, int, int, int, int]]
    sprite_groups: list[int]
    particle_effects: list[int]
    actors: list[tuple[int, int, int, int, int, int]]
    array4: list[int]
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
        particle_effects: list[int],
        actors: list[tuple[int, int, int, int, int, int]],
        array4: list[int],
        subroutine_table: list[int] = [],
        post_table_subroutine: Subroutine | None = None,
    ) -> None:
        self.index = index

        self.init_subroutine = init_subroutine
        self.unk_0x04 = unk_0x04
        self.triggers = triggers if triggers is not None else []
        self.sprite_groups = sprite_groups
        self.particle_effects = particle_effects
        self.actors = actors
        self.array4 = array4
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
        sprite_groups = read_length_prefixed_array(stream, "<I")
        particle_effects = read_length_prefixed_array(stream, "<H", "<H")

        stream.seek(section3_offset)
        actors = read_length_prefixed_array(stream, "<IIIIII")

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
        array4 = read_length_prefixed_array(stream, "<I")
        subroutine_table: list[int] = []
        post_table_subroutine = Subroutine([])
        while (
            (stream.tell() - section4_offset < subroutine_table[0])
            if len(subroutine_table) > 0
            else True
        ):
            offset_data = stream.read(4)
            if offset_data == b"":
                break
            (offset,) = struct.unpack("<I", offset_data)
            if offset <= stream.tell() - 4 - section4_offset or (
                len(subroutine_table) > 0 and offset < subroutine_table[-1]
            ):
                stream.seek(-4, os.SEEK_CUR)
                post_table_subroutine = Subroutine.from_stream(
                    manager,
                    io.BytesIO(
                        stream.read(
                            subroutine_table[0] - stream.tell() + section4_offset
                            if len(subroutine_table) > 0
                            else -1
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
            particle_effects=particle_effects,
            actors=actors,
            array4=array4,
            subroutine_table=subroutine_table,
            post_table_subroutine=post_table_subroutine,
        )

    def to_bytes(self, manager: FEventScriptManager) -> bytes:
        data_io = io.BytesIO()

        section1_empty = len(self.triggers) <= 0 and (
            self.index is not None and self.index % 2 != 0
        )
        if self.init_subroutine is None:
            raise TypeError("init_subroutine must not be None")
        data_io.write(struct.pack("<II", self.init_subroutine, self.unk_0x04))
        section1_offset = 0x18
        section2_offset = section1_offset + (
            4 + len(self.triggers) * 4 * 7 if not section1_empty else 0
        )
        section3_offset = (
            math.ceil(
                (
                    section2_offset
                    + (1 + len(self.sprite_groups)) * 4
                    + (1 + len(self.particle_effects)) * 2
                )
                / 4
            )
            * 4
        )
        section4_offset = section3_offset + 4 + len(self.actors) * 4 * 6
        post_table_subroutine_offset = (
            section4_offset + 4 + len(self.array4) * 4 + len(self.subroutine_table) * 4
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

        data_io.write(struct.pack("<I", len(self.sprite_groups)))
        data_io.write(struct.pack(f"<{len(self.sprite_groups)}I", *self.sprite_groups))
        data_io.write(struct.pack("<H", len(self.particle_effects)))
        data_io.write(
            struct.pack(f"<{len(self.particle_effects)}H", *self.particle_effects)
        )
        data_io.write(b"\xff" * ((-data_io.tell()) % 4))

        data_io.write(struct.pack("<I", len(self.actors)))
        for actors_elements in self.actors:
            data_io.write(struct.pack("<IIIIII", *actors_elements))

        data_io.write(struct.pack("<I", len(self.array4)))
        data_io.write(struct.pack(f"<{len(self.array4)}I", *self.array4))
        subroutine_base_offset = header_end_offset - section4_offset
        for offset in self.subroutine_table:
            data_io.write(struct.pack("<I", offset + subroutine_base_offset))
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
                        subroutine.footer[
                            : (
                                -1
                                if len(subroutine.footer) > 0
                                and subroutine.footer[-1] == 0x00
                                else None
                            )
                        ]
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
