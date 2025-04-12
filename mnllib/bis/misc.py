import dataclasses


@dataclasses.dataclass
class BattleScriptsFileMetadata:
    filename: str
    offset_table_address: int
