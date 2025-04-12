import io
import pathlib
import itertools

import pytest

import mnllib.bis
import mnllib.nds

from ..utils import (
    read_bytes_or_compressed,
    read_bytes_or_compressed_or_skip,
)


SCRIPT_DIR = pathlib.Path(__file__).parent


@pytest.fixture(scope="module")
def fevent_data() -> tuple[bytes, bytes, bytes, mnllib.bis.FEventScriptManager]:
    overlay3 = read_bytes_or_compressed(mnllib.nds.fs_std_overlay_path(3))
    overlay6 = read_bytes_or_compressed(mnllib.nds.fs_std_overlay_path(6))
    fevent = read_bytes_or_compressed(
        mnllib.nds.fs_std_data_path(mnllib.bis.FEVENT_PATH)
    )
    manager = mnllib.bis.FEventScriptManager(data_dir=None)
    manager.load_overlay3(io.BytesIO(overlay3))
    manager.load_overlay6(io.BytesIO(overlay6))
    manager.load_fevent(io.BytesIO(fevent))
    return overlay3, overlay6, fevent, manager


@pytest.fixture(scope="module")
def battle_data() -> tuple[bytes, bytes, mnllib.bis.BattleScriptManager]:
    overlay12 = read_bytes_or_compressed(mnllib.nds.fs_std_overlay_path(12))
    overlay14 = read_bytes_or_compressed(mnllib.nds.fs_std_overlay_path(14))
    manager = mnllib.bis.BattleScriptManager(data_dir=None)
    manager.load_overlay12(io.BytesIO(overlay12))
    manager.load_overlay14(io.BytesIO(overlay14))
    return overlay12, overlay14, manager


@pytest.fixture(scope="module")
def menu_data() -> tuple[bytes, mnllib.bis.MenuScriptManager]:
    overlay123 = read_bytes_or_compressed(mnllib.nds.fs_std_overlay_path(123))
    manager = mnllib.bis.MenuScriptManager(data_dir=None)
    manager.load_overlay123(io.BytesIO(overlay123))
    return overlay123, manager


@pytest.fixture(scope="module")
def shop_data() -> tuple[bytes, mnllib.bis.ShopScriptManager]:
    overlay124 = read_bytes_or_compressed(mnllib.nds.fs_std_overlay_path(124))
    manager = mnllib.bis.ShopScriptManager(data_dir=None)
    manager.load_overlay124(io.BytesIO(overlay124))
    return overlay124, manager


@pytest.mark.parametrize(
    "path",
    itertools.chain(
        [
            pathlib.Path(SCRIPT_DIR, x)
            for x in [
                mnllib.nds.fs_std_data_path("BAI/BMes_cf.dat"),
                mnllib.nds.fs_std_data_path("BAI/BMes_ji.dat"),
                mnllib.nds.fs_std_data_path("BAI/BMes_yo.dat"),
                mnllib.nds.fs_std_data_path("MAI/MMes_yo.dat"),
                mnllib.nds.fs_std_data_path("SAI/SMes_yo.dat"),
            ]
        ],
        set(
            path.with_suffix(path.suffix.removesuffix(".xz"))
            for path in pathlib.Path(
                SCRIPT_DIR, mnllib.nds.DEFAULT_DATA_DIR_PATH, mnllib.nds.DATA_DIR
            ).rglob("mfset_*.dat*")
        ),
    ),
    ids=lambda path: path.relative_to(SCRIPT_DIR).as_posix(),
)
def test_rebuild_language_table_file(path: pathlib.Path) -> None:
    orig_data = read_bytes_or_compressed_or_skip(path)
    language_table = mnllib.bis.LanguageTable.from_bytes(orig_data, is_dialog=False)
    data = language_table.to_bytes()
    assert data == orig_data


def test_rebuild_fevent(
    fevent_data: tuple[bytes, bytes, bytes, mnllib.bis.FEventScriptManager],
) -> None:
    file = io.BytesIO()
    fevent_data[3].save_fevent(file)
    assert file.getvalue() == fevent_data[2]


def test_rebuild_overlay6(
    fevent_data: tuple[bytes, bytes, bytes, mnllib.bis.FEventScriptManager],
) -> None:
    file = io.BytesIO(fevent_data[1])
    fevent_data[3].save_overlay6(file)
    assert file.getvalue() == fevent_data[1]


def test_rebuild_overlay3(
    fevent_data: tuple[bytes, bytes, bytes, mnllib.bis.FEventScriptManager],
) -> None:
    file = io.BytesIO(fevent_data[0])
    fevent_data[3].save_overlay3(file)
    assert file.getvalue() == fevent_data[0]


@pytest.mark.parametrize(
    "address",
    mnllib.bis.BATTLE_SCRIPTS_FILES_METADATA.keys(),
    ids=lambda address: f"0x{address:04X}",
)
def test_rebuild_battle_scripts_file(
    battle_data: tuple[bytes, bytes, mnllib.bis.BattleScriptManager], address: int
) -> None:
    orig_data = read_bytes_or_compressed_or_skip(
        mnllib.nds.fs_std_data_path(
            f"{mnllib.bis.BATTLE_SCRIPTS_DIRECTORY_NAME}/{
                mnllib.bis.BATTLE_SCRIPTS_FILES_METADATA[address].filename
            }"
        )
    )
    battle_data[2].load_battle_scripts_file(address, io.BytesIO(orig_data))
    file = io.BytesIO()
    battle_data[2].save_battle_scripts_file(address, file)
    assert file.getvalue() == orig_data


def test_rebuild_overlay14(
    battle_data: tuple[bytes, bytes, mnllib.bis.BattleScriptManager],
) -> None:
    file = io.BytesIO(battle_data[1])
    battle_data[2].save_overlay14(file)
    assert file.getvalue() == battle_data[1]


def test_rebuild_overlay12(
    battle_data: tuple[bytes, bytes, mnllib.bis.BattleScriptManager],
) -> None:
    file = io.BytesIO(battle_data[0])
    battle_data[2].save_overlay12(file)
    assert file.getvalue() == battle_data[0]


def test_rebuild_overlay123(
    menu_data: tuple[bytes, mnllib.bis.MenuScriptManager],
) -> None:
    file = io.BytesIO(menu_data[0])
    menu_data[1].save_overlay123(file)
    assert file.getvalue() == menu_data[0]


def test_rebuild_overlay124(
    shop_data: tuple[bytes, mnllib.bis.ShopScriptManager],
) -> None:
    file = io.BytesIO(shop_data[0])
    shop_data[1].save_overlay124(file)
    assert file.getvalue() == shop_data[0]
