import io

import pytest

import mnllib.dt


@pytest.fixture
def fevent_manager() -> mnllib.dt.FEventScriptManager:
    return mnllib.dt.FEventScriptManager()


def test_rebuild_code_bin(fevent_manager: mnllib.dt.FEventScriptManager) -> None:
    with open(f"data/{mnllib.dt.CODE_BIN_PATH}", "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO(orig_data)
    fevent_manager.save_code_bin(file)
    assert file.getvalue() == orig_data


def test_rebuild_fevent(fevent_manager: mnllib.dt.FEventScriptManager) -> None:
    with open(f"data/romfs/{mnllib.dt.FEVENT_FILE_NAME}", "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO()
    fevent_manager.save_fevent(file)
    assert file.getvalue() == orig_data
