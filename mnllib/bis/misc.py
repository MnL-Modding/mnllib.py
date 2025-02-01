from __future__ import annotations

import abc
import dataclasses
import struct
import typing

if typing.TYPE_CHECKING:
    from .managers import FEventScriptManager


class FEventChunk(abc.ABC):
    @abc.abstractmethod
    def to_bytes(self, manager: FEventScriptManager) -> bytes:
        pass


@dataclasses.dataclass
class BattleScriptsFileMetadata:
    filename: str
    offset_table_address: int


def parse_fevent_chunk(
    manager: FEventScriptManager, data: bytes, index: int | None = None
) -> FEventChunk | None:
    from .script import FEventScript
    from .text import LanguageTable

    if len(data) == 0:
        return None
    elif struct.unpack_from("<I", data)[0] == 0x128:
        return LanguageTable.from_bytes(data, is_dialog=True, index=index)
    else:
        return FEventScript.from_bytes(manager, data, index=index)
