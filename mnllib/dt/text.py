import functools
import multiprocessing
import os
import struct
import typing
from typing import override

import pymsbmnl

from .consts import (
    DEFAULT_MESSAGE_ATTRIBUTES,
    DEFAULT_MESSAGE_STYLE,
    MESSAGE_HEIGHT_AUTO,
    MESSAGE_WIDTH_AUTO,
    MessageAlignment,
    SpecialCharacter,
    message_footer_padding,
    message_header_padding,
)


class DTLMSAdapter(pymsbmnl.LMSAdapter):
    language: str

    def __init__(self, language: str) -> None:
        super().__init__()

        self.set_little_endian()

        self.language = language

    @property
    @override
    def section_order(self) -> list[pymsbmnl.SectionName]:
        return ["TXT2", "TSY1", "ATR1"]

    @override
    def padding_byte(self, section_name: pymsbmnl.SectionName) -> int | None:
        return 0x00 if section_name != "ATR1" else 0xAB

    @property
    @override
    def header_padding(self) -> bytes:
        return message_header_padding(self.language)

    @override
    def read_char(self, stream: pymsbmnl.BinaryMemoryIO) -> str:
        char = super().read_char(stream)

        try:
            return f"[{SpecialCharacter(char).name}]"
        except ValueError:
            return char

    @override
    def read_tag(self, stream: pymsbmnl.BinaryMemoryIO) -> str:
        group_id = stream.read_u16()
        tag_id = stream.read_u16()
        args_size = stream.read_u16()

        match group_id, tag_id:
            case 0x0000, 0x0000:
                base_text_len = stream.read_u16()
                ruby_text_len = stream.read_u16()

                ruby_text = stream.read(ruby_text_len).decode(self.charset)
                base_text = stream.read(base_text_len).decode(self.charset)

                return f"[Ruby {base_text};{ruby_text}]"

            case 0x0000, 0x0001:
                return f"[Font {stream.read(args_size).hex().upper()}]"
            case 0x0000, 0x0002:
                return f"[Size {stream.read_u16()}%]"

            case 0x0000, 0x0003:
                color = stream.read(args_size)
                if len(color) == 4 and color[3] == 0xFF:
                    color = color[:3]
                return f"[Color #{color.hex().upper()}]"

            case 0x0000, 0x0004:
                return "[Next]"

            case 0x0001, _:
                try:
                    alignment = MessageAlignment(tag_id).name.lower()
                except ValueError:
                    alignment = repr(tag_id)
                return f"[Align {alignment}]"

            case 0x0003, 0x0000:
                return f"[Pause {stream.read_u16()}]"
            case 0x0003, 0x0001:
                return "[Wait]"
            case 0x0003, 0x0002:
                return f"[Speed {stream.read_u16()}]"

            case 0x0004, 0x0000 | 0x0001:
                pad = stream.read_u16()
                digits = stream.read_u16()
                variable = stream.read_u16()
                return f"[Var{
                    "2" if tag_id == 0x0001 else ""
                } {variable:04X} digits={digits}{
                    f" pad={pad}" if pad != 0 else ""
                }]"

            case 0x0005, _:
                return f"[Option{f" instant={tag_id}" if tag_id != 1 else ""}]"

            case 0x0007, 0x0000:
                return "[DelayOff]"
            case 0x0007, 0x0001:
                return "[DelayOn]"

            case 0x0008, 0x0000:
                return f"[Space {stream.read_u16()}]"
            case 0x0008, 0x0001:
                return f"[Indent {stream.read_u16()}]"

            case _:
                return f"[{group_id:04X}:{tag_id:04X}:{
                    stream.read(args_size).hex(" ").upper()
                }]"

    @override
    def read_closing_tag(self, stream: pymsbmnl.BinaryMemoryIO) -> str:
        group_id = stream.read_u16()
        tag_id = stream.read_u16()

        match group_id, tag_id:
            case _:
                return f"[/{group_id:04X}:{tag_id:04X}]"

    @override
    def write_tag(self, stream: pymsbmnl.BinaryMemoryIO, tag: str) -> None:
        if tag.startswith("/"):
            inner_tag = tag[1:]
            self.write_chars(stream, "\u000f")

            if ":" in inner_tag:
                group_id, tag_id = inner_tag.split(":", maxsplit=1)
                stream.write_u16(int(group_id, base=16))
                stream.write_u16(int(tag_id, base=16))
                return

            match inner_tag.casefold():
                case _:
                    raise ValueError(f"unknown closing tag '{tag}'")

            return

        try:
            self.write_chars(stream, SpecialCharacter[tag.upper()])
            return
        except KeyError:
            pass

        self.write_chars(stream, "\u000e")

        if ":" in tag:
            sections = tag.split(":")
            stream.write_u16(int(sections[0], base=16))
            stream.write_u16(int(sections[1], base=16))
            arg_data = bytes.fromhex(sections[2]) if len(sections) >= 3 else b""
            stream.write_u16(len(arg_data))
            stream.write(arg_data)
            return

        tag_type, *raw_args = tag.split(" ")
        pos_args: list[str] = []
        kw_args: dict[str, str] = {}
        for arg in raw_args:
            if "=" in arg:
                key, value = arg.split("=", maxsplit=1)
                key = key.casefold()
                if key in kw_args:
                    raise ValueError(f"keyword argument repeated: {key}")
                kw_args[key] = value
            else:
                pos_args.append(arg)

        match tag_type.casefold():
            case "ruby":
                stream.write_u16(0x0000)
                stream.write_u16(0x0000)

                base_text, ruby_text = " ".join(pos_args).split(";", maxsplit=1)
                encoded_base_text = base_text.encode(self.charset)
                encoded_ruby_text = ruby_text.encode(self.charset)

                stream.write_u16(4 + len(encoded_ruby_text))
                stream.write_u16(len(encoded_base_text))
                stream.write_u16(len(encoded_ruby_text))
                stream.write(encoded_ruby_text)
                stream.write(encoded_base_text)

            case "font":
                stream.write_u16(0x0000)
                stream.write_u16(0x0001)
                font = bytes.fromhex(" ".join(pos_args))
                stream.write_u16(len(font))
                stream.write(font)
            case "size":
                stream.write_u16(0x0000)
                stream.write_u16(0x0002)
                size = int(pos_args[0].rstrip("%"), base=0)
                stream.write_u16(2)
                stream.write_u16(size)

            case "color" | "colour":
                stream.write_u16(0x0000)
                stream.write_u16(0x0003)
                color = bytes.fromhex(" ".join(pos_args).lstrip("#"))
                if len(color) == 3:
                    color += b"\xff"
                elif len(color) != 4:
                    raise ValueError("color must be in format RRGGBB or RRGGBBAA")
                stream.write_u16(len(color))
                stream.write(color)

            case "next":
                stream.write_u16(0x0000)
                stream.write_u16(0x0004)
                stream.write_u16(0)

            case "align":
                stream.write_u16(0x0001)
                try:
                    alignment = int(pos_args[0], base=0)
                except ValueError:
                    alignment = MessageAlignment[pos_args[0].upper()]
                stream.write_u16(alignment)
                stream.write_u16(0)

            case "pause":
                stream.write_u16(0x0003)
                stream.write_u16(0x0000)
                frames = int(pos_args[0], base=0)
                stream.write_u16(2)
                stream.write_u16(frames)
            case "wait":
                stream.write_u16(0x0003)
                stream.write_u16(0x0001)
                stream.write_u16(0)
            case "speed":
                stream.write_u16(0x0003)
                stream.write_u16(0x0002)
                speed = int(pos_args[0], base=0)
                stream.write_u16(2)
                stream.write_u16(speed)

            case "var" | "var2" as tag_type:
                stream.write_u16(0x0004)
                stream.write_u16(0x0001 if tag_type == "var2" else 0x0000)
                stream.write_u16(6)
                try:
                    pad = int(kw_args["pad"], base=0)
                except KeyError:
                    pad = 0
                stream.write_u16(pad)
                stream.write_u16(int(kw_args["digits"], base=0))
                stream.write_u16(int(pos_args[0], base=16))

            case "option":
                stream.write_u16(0x0005)
                try:
                    instant = int(kw_args["instant"], base=0)
                except KeyError:
                    instant = 1
                stream.write_u16(instant)
                stream.write_u16(0)

            case "delayoff":
                stream.write_u16(0x0007)
                stream.write_u16(0x0000)
                stream.write_u16(0)
            case "delayon":
                stream.write_u16(0x0007)
                stream.write_u16(0x0001)
                stream.write_u16(0)

            case "space":
                stream.write_u16(0x0008)
                stream.write_u16(0x0000)
                amount = int(pos_args[0], base=0)
                stream.write_u16(2)
                stream.write_u16(amount)
            case "indent":
                stream.write_u16(0x0008)
                stream.write_u16(0x0001)
                amount = int(pos_args[0], base=0)
                stream.write_u16(2)
                stream.write_u16(amount)

            case _:
                raise ValueError(f"unknown tag '{tag_type}'")

    @property
    @override
    def supports_labels(self) -> bool:
        return False

    @property
    @override
    def supports_attributes(self) -> bool:
        return True

    @property
    @override
    def attributes_size(self) -> int:
        return 3

    @override
    def create_default_attributes(self) -> dict[str, typing.Any]:
        return DEFAULT_MESSAGE_ATTRIBUTES.copy()

    @override
    def parse_attributes(
        self, stream: pymsbmnl.BinaryMemoryIO, root_offset: int, root_size: int
    ) -> dict[str, typing.Any]:
        return {"width": stream.read_u16(), "height": stream.read_u8()}

    @override
    def write_attributes(
        self, stream: pymsbmnl.BinaryMemoryIO, attributes: dict[str, typing.Any]
    ) -> None:
        stream.write_u16(attributes.get("width", MESSAGE_WIDTH_AUTO))
        stream.write_u8(attributes.get("height", MESSAGE_HEIGHT_AUTO))

    @property
    @override
    def supports_styles(self) -> bool:
        return True

    @override
    def create_default_style(self) -> int:
        return DEFAULT_MESSAGE_STYLE


def read_msbt_chunk(language: str, chunk: bytes) -> pymsbmnl.LMSDocument:
    if len(chunk) > 0:
        return pymsbmnl.msbt_from_buffer(lambda: DTLMSAdapter(language), chunk)
    else:
        return pymsbmnl.LMSDocument(lambda: DTLMSAdapter(language))


def read_msbt_archive(
    archive: typing.BinaryIO, offset_table: typing.BinaryIO, language: str
) -> list[pymsbmnl.LMSDocument]:
    offset_table.seek(8, os.SEEK_CUR)
    offset_table_length = struct.unpack("<I", offset_table.read(4))[0] // 8 - 2
    offset_table.seek(4, os.SEEK_CUR)

    chunks: list[bytes] = []
    for _ in range(offset_table_length):
        offset, length = struct.unpack("<II", offset_table.read(4 * 2))
        archive.seek(offset)
        chunks.append(archive.read(length))
    with multiprocessing.Pool() as pool:
        return pool.map(functools.partial(read_msbt_chunk, language), chunks)


def serialize_msbt_chunk(chunk: pymsbmnl.LMSDocument) -> bytes:
    if len(chunk.messages) > 0:
        data = chunk.makebin().rstrip(b"\xab")
        data += message_footer_padding(
            typing.cast(DTLMSAdapter, chunk.adapter).language
        )[: (-len(data)) % 16]
        return data
    else:
        return b""


def write_msbt_archive(
    chunks: list[pymsbmnl.LMSDocument],
    archive: typing.BinaryIO,
    offset_table: typing.BinaryIO,
    *,
    is_battle: bool = False,
) -> None:
    chunks_len = len(chunks)
    offset_table.write(
        struct.pack(
            "<HHIIHH",
            0,
            chunks_len,
            0x00060000 if is_battle else 0,
            (chunks_len + 2) * 8,
            0,
            chunks_len - 1,
        )
    )

    with multiprocessing.Pool() as pool:
        serialized_chunks = pool.map(serialize_msbt_chunk, chunks)
    for chunk in serialized_chunks:
        offset = archive.tell()
        archive.write(chunk)
        offset_table.write(struct.pack("<II", offset, len(chunk)))
