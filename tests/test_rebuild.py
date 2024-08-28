import pathlib
import io

import pytest

import mnllib


DATA_DIR = pathlib.Path(__file__).with_name("data")
OVERLAY3_PATH = DATA_DIR / "overlay_0003.dec.bin"
OVERLAY6_PATH = DATA_DIR / "overlay_0006.dec.bin"
FEVENT_PATH = DATA_DIR / "FEvent.dat"


@pytest.fixture
def manager() -> mnllib.MnLScriptManager:
    manager = mnllib.MnLScriptManager(load=False)
    manager.load_overlay3(OVERLAY3_PATH.as_posix())
    manager.load_overlay6(OVERLAY6_PATH.as_posix())
    manager.load_fevent(FEVENT_PATH.as_posix())
    return manager


def test_rebuild_overlay3(manager: mnllib.MnLScriptManager) -> None:
    with open(OVERLAY3_PATH, "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO(orig_data)
    manager.save_overlay3(file)
    assert file.getvalue() == orig_data


def test_rebuild_overlay6(manager: mnllib.MnLScriptManager) -> None:
    with open(OVERLAY6_PATH, "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO(orig_data)
    manager.save_overlay6(file)
    assert file.getvalue() == orig_data


def test_rebuild_fevent(manager: mnllib.MnLScriptManager) -> None:
    with open(FEVENT_PATH, "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO()
    manager.save_fevent(file)
    assert file.getvalue() == orig_data
