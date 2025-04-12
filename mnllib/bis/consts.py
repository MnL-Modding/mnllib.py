import enum

from ..utils import VariableRangeEnum
from .misc import BattleScriptsFileMetadata


BIS_ENCODING = "cp1252"


SCRIPT_ALIGNMENT = 4
TEXT_TABLE_ALIGNMENT = 4
LANGUAGE_TABLE_ALIGNMENT = 512


FEVENT_PATH = "FEvent/FEvent.dat"
FEVENT_COMMAND_METADATA_TABLE_ADDRESS = 0x14B08  # Overlay 6
FEVENT_NUMBER_OF_COMMANDS = 0x01E5
FEVENT_OFFSET_TABLE_LENGTH_ADDRESS = 0x0C8AC  # Overlay 3
FEVENT_OFFSET_TABLE_ADDRESS = FEVENT_OFFSET_TABLE_LENGTH_ADDRESS + 4  # Overlay 3
FEVENT_PADDING_TEXT_TABLE_ID = 0x49

BATTLE_SCRIPTS_DIRECTORY_NAME = "BAI"
BATTLE_COMMAND_METADATA_TABLE_ADDRESS = 0x13478  # Overlay 12
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

MENU_COMMAND_METADATA_TABLE_ADDRESS = 0x2F37C  # Overlay 123
MENU_NUMBER_OF_COMMANDS = 0x00B0

SHOP_COMMAND_METADATA_TABLE_ADDRESS = 0x2B728  # Overlay 124
SHOP_NUMBER_OF_COMMANDS = 0x00B8


class ImportantFlags(enum.IntFlag):
    NONE = 0

    MINI_MARIO = 1 << 0x00
    HAMMER = 1 << 0x01
    SPIN_JUMP = 1 << 0x02
    DRILL_BROS = 1 << 0x03
    FIRE_BREATH_DISABLED = 1 << 0x04
    SLIDING_HAYMAKER = 1 << 0x05
    BODY_SLAM = 1 << 0x06
    SPIKE_BALL = 1 << 0x07
    PUMP_WORKS_FLOODED = 1 << 0x08
    ENERGY_HOLD_BOO_RAY = 1 << 0x09
    AIRWAY_FROZEN = 1 << 0x0A
    BROS_ATTACKS = 1 << 0x0B
    BADGES = 1 << 0x0C
    BRAWL_ATTACKS = 1 << 0x0D
    VACUUM = 1 << 0x0E

    BROS_ATTACK_GREEN_SHELL = 1 << 0x10
    BROS_ATTACK_SPIN_PIPE = 1 << 0x11
    BROS_ATTACK_YOO_WHO_CANNON = 1 << 0x12
    BROS_ATTACK_FALLING_STAR = 1 << 0x13
    BROS_ATTACK_JUMP_HELMET = 1 << 0x16
    BROS_ATTACK_SUPER_BOUNCER = 1 << 0x17
    BROS_ATTACK_MIGHTY_METEOR = 1 << 0x18
    BROS_ATTACK_FIRE_FLOWER = 1 << 0x19
    BROS_ATTACK_SNACK_BASKET = 1 << 0x1A
    BROS_ATTACK_MAGIC_WINDOW = 1 << 0x1B
    BRAWL_ATTACK_GOOMBA_STORM = 1 << 0x1C
    BRAWL_ATTACK_BOB_OMB_BLITZ = 1 << 0x1D
    BRAWL_ATTACK_SHY_GUY_SQUAD = 1 << 0x1E
    BRAWL_ATTACK_KOOPA_CORPS = 1 << 0x1F

    BRAWL_ATTACK_MAGIKOOPA_MOB = 1 << 0x21
    BRAWL_ATTACK_BROGGY_BONKER = 1 << 0x22
    COUNTERATTACK_SHELL = 1 << 0x24
    BLUE_SHELL_BLOCKS = 1 << 0x25
    SHOP_UPGRADE_1 = 1 << 0x26
    SHOP_UPGRADE_2 = 1 << 0x27
    SHOP_UPGRADE_3 = 1 << 0x28
    SHOP_UPGRADE_4 = 1 << 0x29
    SHOP_UPGRADE_5 = 1 << 0x2A
    SHOP_UPGRADE_6 = 1 << 0x2B
    SHOP_UPGRADE_7 = 1 << 0x2C
    AIR_VENTS = 1 << 0x2D
    STAR_MENU_BOWSER = 1 << 0x2E
    BLOOPERS_WET = 1 << 0x2F


class VariableType(VariableRangeEnum):
    LOCAL = 0x1000
    IMPORTANT_FLAG = 0x2000
    SPECIAL = range(0x3000, 0x5000)
    # TODO: 0x5000
    IMPORTANT_VALUE = 0x6000
    GLOBAL = 0x9000
    LOCAL2 = 0xA000
    STACK_BITFIELD = 0xB000
    TEXT_SYSTEM = 0xC000
    MAP = 0xD000
    TREASURE = range(0xE000, 0xE400)
    ENEMY = range(0xE400, 0xE700)
    STORY = range(0xE700, 0x10000)
