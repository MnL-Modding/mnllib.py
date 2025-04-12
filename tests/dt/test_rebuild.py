import io
import pathlib

import pytest

import mnllib.dt
import mnllib.n3ds

from ..utils import read_bytes_or_compressed, read_bytes_or_compressed_or_skip


SCRIPT_DIR = pathlib.Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"


@pytest.fixture(
    scope="module",
    params=(path for path in DATA_DIR.iterdir() if path.is_dir()),
    ids=lambda path: path.name,
)
def fevent_data(
    request: pytest.FixtureRequest,
) -> tuple[bytes, bytes, mnllib.dt.FEventScriptManager]:
    data_dir: pathlib.Path = request.param

    code_bin = read_bytes_or_compressed(
        mnllib.n3ds.fs_std_code_bin_path(data_dir=data_dir)
    )
    fevent = read_bytes_or_compressed(
        mnllib.n3ds.fs_std_romfs_path(mnllib.dt.FEVENT_PATH, data_dir=data_dir)
    )
    manager = mnllib.dt.FEventScriptManager(data_dir=None)
    manager.load_code_bin(io.BytesIO(code_bin))
    manager.load_fevent(io.BytesIO(fevent), parse_all=True)
    return code_bin, fevent, manager


def test_rebuild_fevent(
    fevent_data: tuple[bytes, bytes, mnllib.dt.FEventScriptManager],
) -> None:
    file = io.BytesIO()
    fevent_data[2].save_fevent(file)
    assert file.getvalue() == fevent_data[1]


def test_rebuild_code_bin(
    fevent_data: tuple[bytes, bytes, mnllib.dt.FEventScriptManager],
) -> None:
    file = io.BytesIO(fevent_data[0])
    fevent_data[2].save_code_bin(file)
    assert file.getvalue() == fevent_data[0]


@pytest.mark.parametrize(
    "path",
    set(
        path.with_suffix(path.suffix.removesuffix(".xz"))
        for path in DATA_DIR.glob(f"*/{mnllib.n3ds.ROMFS_DIR}/Message/*/[FB]Mes.dat*")
    ),
    ids=lambda path: path.relative_to(DATA_DIR).as_posix(),
)
def test_rebuild_text_archive(path: pathlib.Path) -> None:
    orig_offset_table = read_bytes_or_compressed_or_skip(path.with_suffix(".bin"))
    orig_archive = read_bytes_or_compressed_or_skip(path)
    text_chunks = mnllib.dt.read_msbt_archive(
        io.BytesIO(orig_archive),
        io.BytesIO(orig_offset_table),
        language=path.parent.name,
    )
    offset_table = io.BytesIO()
    archive = io.BytesIO()
    mnllib.dt.write_msbt_archive(
        text_chunks, archive, offset_table, is_battle=path.stem == "BMes"
    )
    assert offset_table.getvalue() == orig_offset_table
    assert archive.getvalue() == orig_archive
