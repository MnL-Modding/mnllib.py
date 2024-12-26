import struct

from .misc import BattleScriptsFileMetadata


MNL_ENCODING = "cp1252"
MNL_NOTE_ENCODING = "shift_jis"
COMMAND_PARAMETER_STRUCT_MAP = [struct.Struct(f"<{x}") for x in "BHIbhihi"]


FEVENT_FILE_NAME = "FEvent/FEvent.dat"
FEVENT_SCRIPT_ALIGNMENT = 4
FEVENT_LANGUAGE_TABLE_ALIGNMENT = 512
FEVENT_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS = 0x14B08
FEVENT_NUMBER_OF_COMMANDS = 0x01E5
FEVENT_OFFSET_TABLE_LENGTH_ADDRESS = 0x0C8AC
FEVENT_OFFSET_TABLE_ADDRESS = FEVENT_OFFSET_TABLE_LENGTH_ADDRESS + 4
FEVENT_PADDING_TEXT_TABLE_ID = 0x49

BATTLE_SCRIPTS_DIRECTORY_NAME = "BAI"
BATTLE_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS = 0x13478
BATTLE_NUMBER_OF_COMMANDS = 0x0224
BATTLE_SCRIPTS_FILES_METADATA: dict[int, BattleScriptsFileMetadata] = {
    0x1000: BattleScriptsFileMetadata("BAI_scn_yo.dat", 0x8998),
    0x2000: BattleScriptsFileMetadata("BAI_mon_yo.dat", 0x8210),
    0x3000: BattleScriptsFileMetadata("BAI_scn_ji.dat", 0x82A4),
    0x4000: BattleScriptsFileMetadata("BAI_mon_ji.dat", 0x8480),
    0x5000: BattleScriptsFileMetadata("BAI_item_ji.dat", 0x7C6C),
    0x6000: BattleScriptsFileMetadata("BAI_scn_cf.dat", 0x7C84),
    0x7000: BattleScriptsFileMetadata("BAI_mon_cf.dat", 0x7D7C),
    0xA000: BattleScriptsFileMetadata("BAI_atk_nh.dat", 0x834C),
    0xC000: BattleScriptsFileMetadata("BAI_atk_yy.dat", 0x7D40),
    0xD000: BattleScriptsFileMetadata("BAI_atk_hk.dat", 0x875C),
    # `BAI_atk_mt.dat` is unknown.
}

MENU_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS = 0x2F37C
MENU_NUMBER_OF_COMMANDS = 0x00B0

SHOP_COMMAND_PARAMETER_METADATA_TABLE_ADDRESS = 0x2B728
SHOP_NUMBER_OF_COMMANDS = 0x00B8
