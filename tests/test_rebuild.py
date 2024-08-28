import os
import io
import pathlib
import itertools

import pytest

import mnllib


os.chdir(pathlib.Path(__file__).parent)


@pytest.fixture
def manager() -> mnllib.MnLScriptManager:
    return mnllib.MnLScriptManager()


@pytest.mark.parametrize(
    "path",
    itertools.chain(
        [
            pathlib.Path(x)
            for x in [
                "data/data/BAI/BMes_cf.dat",
                "data/data/BAI/BMes_ji.dat",
                "data/data/BAI/BMes_yo.dat",
                "data/data/MAI/MMes_yo.dat",
                "data/data/SAI/SMes_yo.dat",
            ]
        ],
        pathlib.Path("data/data").rglob("mfset_*.dat"),
    ),
    ids=lambda path: path.as_posix(),
)
def test_rebuild_language_table(path: pathlib.Path) -> None:
    try:
        with path.open("rb") as orig_file:
            orig_data = orig_file.read()
    except FileNotFoundError:
        pytest.skip("file not present")
    language_table = mnllib.LanguageTable.from_bytes(orig_data, False)
    data = language_table.to_bytes()
    assert data == orig_data


def test_rebuild_overlay3(manager: mnllib.MnLScriptManager) -> None:
    with open("data/overlay.dec/overlay_0003.dec.bin", "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO(orig_data)
    manager.save_overlay3(file)
    assert file.getvalue() == orig_data


def test_rebuild_overlay6(manager: mnllib.MnLScriptManager) -> None:
    with open("data/overlay.dec/overlay_0006.dec.bin", "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO(orig_data)
    manager.save_overlay6(file)
    assert file.getvalue() == orig_data


def test_rebuild_fevent(manager: mnllib.MnLScriptManager) -> None:
    with open("data/data/FEvent/FEvent.dat", "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO()
    manager.save_fevent(file)
    assert file.getvalue() == orig_data
