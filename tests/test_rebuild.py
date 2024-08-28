import os
import pathlib
import io

import pytest

import mnllib


os.chdir(pathlib.Path(__file__).parent)


@pytest.fixture
def manager() -> mnllib.MnLScriptManager:
    return mnllib.MnLScriptManager()


@pytest.mark.parametrize(
    "path",
    pathlib.Path("data/data").rglob("mfset_*.dat"),
    ids=lambda path: path.as_posix(),
)
def test_mfset(path: pathlib.Path) -> None:
    with path.open("rb") as orig_file:
        orig_data = orig_file.read()
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
