import lzma
import os
import pathlib
import typing

import pytest


REASON_FILE_NOT_PRESENT = "file not present"


def open_or_skip(*args: typing.Any, **kwargs: typing.Any) -> typing.IO[typing.Any]:
    try:
        return typing.cast(typing.IO[typing.Any], open(*args, **kwargs))
    except FileNotFoundError:
        pytest.skip(REASON_FILE_NOT_PRESENT)


def read_bytes_or_compressed(path: str | os.PathLike[str]) -> bytes:
    if not isinstance(path, pathlib.Path):
        path = pathlib.Path(path)

    try:
        return path.read_bytes()
    except FileNotFoundError:
        with lzma.open(path.with_suffix(path.suffix + ".xz")) as file:
            return file.read()


def read_bytes_or_compressed_or_skip(
    path: str | os.PathLike[str],
) -> bytes:
    try:
        return read_bytes_or_compressed(path)
    except FileNotFoundError:
        pytest.skip(REASON_FILE_NOT_PRESENT)
