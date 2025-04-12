import os
import pathlib

from ..consts import DEFAULT_DATA_DIR_PATH


HEADER_PATH = "header.bin"
ARM9_PATH = "arm9.bin"
DECOMPRESSED_ARM9_PATH = "arm9.dec.bin"
ARM9_POST_DATA_PATH = "arm9_post.bin"
ARM7_PATH = "arm7.bin"
ARM9_OVERLAY_TABLE_PATH = "y9.bin"
ARM7_OVERLAY_TABLE_PATH = "y7.bin"
BANNER_PATH = "banner.bin"

DATA_DIR = "data"
OVERLAYS_DIR = "overlay"
DECOMPRESSED_OVERLAYS_DIR = "overlay.dec"


def fs_std_data_path(
    path: str | os.PathLike[str],
    data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH,
) -> pathlib.Path:
    return pathlib.Path(data_dir, DATA_DIR, path)


def fs_std_overlay_path(
    overlay_id: int, data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH
) -> pathlib.Path:
    return pathlib.Path(
        data_dir, DECOMPRESSED_OVERLAYS_DIR, f"overlay_{overlay_id:04}.dec.bin"
    )
