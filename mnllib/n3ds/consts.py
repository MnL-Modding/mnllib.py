import os
import pathlib

from ..consts import DEFAULT_DATA_DIR_PATH


EXEFS_DIR = "exefs"
ROMFS_DIR = "romfs"

CODE_BIN_PATH = "code.bin"


def fs_std_exefs_path(
    path: str | os.PathLike[str],
    data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH,
) -> pathlib.Path:
    return pathlib.Path(data_dir, EXEFS_DIR, path)


def fs_std_code_bin_path(
    data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH,
) -> pathlib.Path:
    return fs_std_exefs_path(CODE_BIN_PATH, data_dir=data_dir)


def fs_std_romfs_path(
    path: str | os.PathLike[str],
    data_dir: str | os.PathLike[str] = DEFAULT_DATA_DIR_PATH,
) -> pathlib.Path:
    return pathlib.Path(data_dir, ROMFS_DIR, path)
