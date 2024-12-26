import os
import io
import pathlib
import itertools
import typing

import pytest

import mnllib


os.chdir(pathlib.Path(__file__).parent)


def open_or_skip(*args: typing.Any, **kwargs: typing.Any) -> typing.IO[typing.Any]:
    try:
        return typing.cast(typing.IO[typing.Any], open(*args, **kwargs))
    except FileNotFoundError:
        pytest.skip("file not present")


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
    with open_or_skip(path, "rb") as orig_file:
        orig_data = orig_file.read()
    language_table = mnllib.LanguageTable.from_bytes(orig_data, is_dialog=False)
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
    with open(f"data/data/{mnllib.FEVENT_FILE_NAME}", "rb") as orig_file:
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


def test_rebuild_overlay14(battle_manager: mnllib.BattleScriptManager) -> None:
    with open("data/overlay.dec/overlay_0014.dec.bin", "rb") as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO(orig_data)
    battle_manager.save_overlay14(file)
    assert file.getvalue() == orig_data


@pytest.mark.parametrize(
    "address",
    mnllib.BATTLE_SCRIPTS_FILES_METADATA.keys(),
    ids=lambda address: f"0x{address:04X}",
)
def test_rebuild_battle_scripts_file(
    battle_manager: mnllib.BattleScriptManager, address: int
) -> None:
    with open_or_skip(
        f"data/data/{mnllib.BATTLE_SCRIPTS_DIRECTORY_NAME}/{
            mnllib.BATTLE_SCRIPTS_FILES_METADATA[address].filename
        }",
        "rb",
    ) as orig_file:
        orig_data = orig_file.read()
    file = io.BytesIO()
    battle_manager.save_battle_scripts_file(address, file)
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
