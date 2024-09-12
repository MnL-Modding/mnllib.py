import os
import io
import pathlib
import itertools

import pytest

import mnllib


os.chdir(pathlib.Path(__file__).parent)


@pytest.fixture
def fevent_manager() -> mnllib.FEventScriptManager:
    return mnllib.FEventScriptManager()


@pytest.fixture
def battle_manager() -> mnllib.BattleScriptManager:
    return mnllib.BattleScriptManager()


@pytest.fixture
def menu_manager() -> mnllib.MenuScriptManager:
    return mnllib.MenuScriptManager()


@pytest.fixture
def shop_manager() -> mnllib.ShopScriptManager:
    return mnllib.ShopScriptManager()


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
def test_rebuild_language_table_file(path: pathlib.Path) -> None:
    try:
        with path.open("rb") as orig_file:
            orig_data = orig_file.read()
    except FileNotFoundError:
        pytest.skip("file not present")
    language_table = mnllib.LanguageTable.from_bytes(orig_data, False)
    data = language_table.to_bytes()
    assert data == orig_data


def test_rebuild_overlay3(fevent_manager: mnllib.FEventScriptManager) -> None:
    with open("data/overlay.dec/overlay_0003.dec.bin", "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO(orig_data)
    fevent_manager.save_overlay3(file)
    assert file.getvalue() == orig_data


def test_rebuild_overlay6(fevent_manager: mnllib.FEventScriptManager) -> None:
    with open("data/overlay.dec/overlay_0006.dec.bin", "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO(orig_data)
    fevent_manager.save_overlay6(file)
    assert file.getvalue() == orig_data


def test_rebuild_fevent(fevent_manager: mnllib.FEventScriptManager) -> None:
    with open("data/data/FEvent/FEvent.dat", "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO()
    fevent_manager.save_fevent(file)
    assert file.getvalue() == orig_data


def test_rebuild_overlay12(battle_manager: mnllib.BattleScriptManager) -> None:
    with open("data/overlay.dec/overlay_0012.dec.bin", "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO(orig_data)
    battle_manager.save_overlay12(file)
    assert file.getvalue() == orig_data


def test_rebuild_overlay123(menu_manager: mnllib.MenuScriptManager) -> None:
    with open("data/overlay.dec/overlay_0123.dec.bin", "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO(orig_data)
    menu_manager.save_overlay123(file)
    assert file.getvalue() == orig_data


def test_rebuild_overlay124(shop_manager: mnllib.ShopScriptManager) -> None:
    with open("data/overlay.dec/overlay_0124.dec.bin", "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO(orig_data)
    shop_manager.save_overlay124(file)
    assert file.getvalue() == orig_data
