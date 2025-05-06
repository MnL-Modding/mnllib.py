import hashlib
import os
import typing

from structured import ByteOrder, Structured, char, uint16, uint8

from ..n3ds.consts import fs_std_code_bin_path
from ..n3ds.misc import N3DSRegion
from ..utils import stream_or_open_file
from .consts import ENEMY_STATS_ADDRESS, NUMBER_OF_ENEMIES


type DTVersion = typing.Literal["1.0", "1.1"]
type DTVersionPair = tuple[N3DSRegion, DTVersion]


def determine_version_from_code_bin(
    code_bin: typing.BinaryIO | str | os.PathLike[str],
) -> DTVersionPair:
    with stream_or_open_file(code_bin, "rb") as code_bin:
        code_bin.seek(0)
        match hashlib.sha256(code_bin.read(256)).hexdigest():
            case "9bff1e997bcd957743fc8d8fd44ff2b82aa0785a814c4f2a94afe2427c7a0164":
                return ("E", "1.0")
            case "5e7c239b8bca10d6e762ed38b0354f931c3f3b086bc0f7c2721b2da9ab31dca2":
                return ("E", "1.1")
            case "5faf04a224aeb0aaa96d7d005af15dac795347eb6f237855a01df3ab7cf62a87":
                return ("P", "1.0")
            case "f67913aaeb11ce8b36e49d052fdfd31e77148c4e4e1ac2b8bd48edebb27b7f73":
                return ("P", "1.1")
            case "af4ce922c4acebeffa0544901a996738fbef3f437aa932f2d39903ffc2039974":
                return ("J", "1.0")
            case "ad9dd9e7c1ba76c20019ad1d8aa4164061c67c3ff1f51c9eeecf5cef795f72c7":
                return ("J", "1.1")
            case "a206ea8e1132fa332b0c0ce2237bd00986415d02948b31eddec6890531076816":
                return ("K", "1.0")
            case digest:
                raise ValueError(
                    "unknown region/version of the game with "
                    f"SHA-256 of the first 256 bytes of 'code.bin': {digest}"
                )


class EnemyStats(Structured, byte_order=ByteOrder.LE):
    name_index: uint16
    unk1: typing.Annotated[bytes, char[6]]
    object_id: uint16
    unk2: typing.Annotated[bytes, char[14]]
    level: uint8
    attributes1: uint8
    hp: uint16
    power: uint16
    defense: uint16
    speed: uint16
    unk3: uint16
    weaknesses: uint8
    unk4: typing.Annotated[bytes, char[3]]
    exp: uint16
    coins: uint16
    coin_rate: uint16
    item_type: uint16
    item_chance: uint16
    rare_item_type: uint16
    rare_item_chance: uint16
    unk5: typing.Annotated[bytes, char[6]]


def load_enemy_stats(
    *,
    code_bin: typing.BinaryIO | str | os.PathLike[str] = fs_std_code_bin_path(),
) -> list[EnemyStats]:
    with stream_or_open_file(code_bin, "rb") as code_bin:
        version_pair = determine_version_from_code_bin(code_bin)

        code_bin.seek(ENEMY_STATS_ADDRESS[version_pair])
        return [
            EnemyStats.create_unpack_read(code_bin) for _ in range(NUMBER_OF_ENEMIES)
        ]


def save_enemy_stats(
    enemy_stats: list[EnemyStats],
    *,
    code_bin: typing.BinaryIO | str | os.PathLike[str] = fs_std_code_bin_path(),
) -> None:
    if len(enemy_stats) != NUMBER_OF_ENEMIES:
        raise ValueError(
            f"enemy_stats must be exactly {NUMBER_OF_ENEMIES} elements long"
        )

    with stream_or_open_file(code_bin, "r+b") as code_bin:
        version_pair = determine_version_from_code_bin(code_bin)

        code_bin.seek(ENEMY_STATS_ADDRESS[version_pair])
        for enemy in enemy_stats:
            enemy.pack_write(code_bin)
