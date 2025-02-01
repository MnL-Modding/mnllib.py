import os
import math
import struct
import io
import warnings
import typing

from ..misc import MnLLibWarning, decode_varint, encode_varint


def decompress(stream: typing.BinaryIO) -> bytes:
    result = io.BytesIO()

    uncompressed_size = decode_varint(stream)
    num_blocks = decode_varint(stream) + 1

    for _ in range(num_blocks):
        (block_size,) = struct.unpack("<H", stream.read(2))
        block_start = stream.tell()

        def process_block() -> None:
            for _ in range(256):
                (commands_byte,) = struct.unpack("<B", stream.read(1))
                for _ in range(4):
                    current_command = commands_byte & 0x03
                    match current_command:
                        case 0:
                            return
                        case 1:
                            result.write(stream.read(1))
                        case 2:
                            data, data2 = struct.unpack("<BB", stream.read(2))
                            result.seek(-(data | ((data2 & 0xF0) << 4)), os.SEEK_CUR)
                            data_to_copy = result.read((data2 & 0x0F) + 2)
                            result.seek(0, os.SEEK_END)
                            result.write(data_to_copy)
                        case 3:
                            (count,) = struct.unpack("<B", stream.read(1))
                            data = stream.read(1)
                            result.write(data * (count + 2))
                        case _:
                            typing.assert_never(current_command)
                    commands_byte >>= 2

        process_block()
        actual_block_size = stream.tell() - block_start
        if actual_block_size != block_size:
            warnings.warn(
                f"The declared compressed block size ({block_size}) doesn't match "
                f"the actual one ({actual_block_size})!",
                MnLLibWarning,
            )

    actual_uncompressed_size = result.tell()
    if actual_uncompressed_size != uncompressed_size:
        warnings.warn(
            f"The declared uncompressed size ({uncompressed_size}) doesn't match "
            f"the actual one ({actual_uncompressed_size})!",
            MnLLibWarning,
        )
    return result.getvalue()


def compress(data: bytes) -> bytes:
    result = io.BytesIO()

    uncompressed_size = len(data)
    result.write(encode_varint(uncompressed_size))
    num_blocks = math.ceil(uncompressed_size / 512)
    result.write(encode_varint(num_blocks - 1))

    for block_number in range(num_blocks):
        uncompressed_block_position = block_number * 512
        uncompressed_block_size = min(
            uncompressed_size - uncompressed_block_position, 512
        )
        uncompressed_block_offset = 0
        compressed_block_position = result.tell()
        result.write(struct.pack("<H", 0x0000))
        last_command_number = -1

        while uncompressed_block_offset < uncompressed_block_size:
            commands_byte_position = result.tell()
            commands_byte = 0x00
            result.write(struct.pack("<B", commands_byte))
            for command_number in range(4):
                if uncompressed_block_offset >= uncompressed_block_size:
                    break
                current_uncompressed_position = (
                    uncompressed_block_position + uncompressed_block_offset
                )
                first_byte = data[current_uncompressed_position]

                lz77_best_length = 0
                lz77_best_offset = -1
                for offset in range(
                    min(current_uncompressed_position, 0xFFF),
                    1,
                    -1,
                ):
                    current_length = 0
                    while (
                        current_length < 17
                        and current_length < offset
                        and uncompressed_block_offset + current_length
                        < uncompressed_block_size
                    ):
                        if (
                            data[current_uncompressed_position + current_length]
                            != data[
                                current_uncompressed_position - offset + current_length
                            ]
                        ):
                            break
                        current_length += 1
                    if current_length > lz77_best_length:
                        lz77_best_length = current_length
                        lz77_best_offset = offset

                rle_count = 1
                while (
                    uncompressed_block_offset + rle_count < uncompressed_block_size
                    and rle_count < 257
                ):
                    if data[current_uncompressed_position + rle_count] != first_byte:
                        break
                    rle_count += 1

                best_length = max(lz77_best_length, rle_count)
                if best_length <= 1:
                    current_command = 1
                    result.write(struct.pack("<B", first_byte))
                elif lz77_best_length > rle_count:
                    current_command = 2
                    result.write(
                        struct.pack(
                            "<BB",
                            lz77_best_offset & 0x0FF,
                            (lz77_best_length - 2) | ((lz77_best_offset & 0xF00) >> 4),
                        )
                    )
                else:
                    current_command = 3
                    result.write(struct.pack("<BB", rle_count - 2, first_byte))

                commands_byte |= current_command << (command_number * 2)
                uncompressed_block_offset += best_length
                last_command_number = command_number
            result.seek(commands_byte_position)
            result.write(struct.pack("<B", commands_byte))
            result.seek(0, os.SEEK_END)

        if last_command_number == 3:
            result.write(struct.pack("<B", 0x00))
        compressed_block_end_position = result.tell()
        result.seek(compressed_block_position)
        result.write(
            struct.pack(
                "<H", compressed_block_end_position - compressed_block_position - 2
            )
        )
        result.seek(0, os.SEEK_END)

    return result.getvalue()
