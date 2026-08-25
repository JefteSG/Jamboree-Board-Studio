"""Item Mass (Item Case) loot table: format-independent model + adapter.

``bd00_ItemMass_MapXX.json`` holds a per-map list of items obtainable
from Item Cases, grouped by lot number (``No``) — see
``jamboree_board_studio/legacy/editor_modules/item_mass.py`` for the existing widget.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

KNOWN_MAP_NAMES = tuple(f"Map{i:02d}" for i in range(1, 8))


class ItemMassParseError(Exception):
    """Raised when a map's Item Mass data can't be read or is structurally invalid."""


@dataclass
class ItemMassEntry:
    item: str
    lot: int
    game_data: dict = field(default_factory=dict)


def _file_path(workspace_path: str, map_name: str) -> str:
    return os.path.join(
        workspace_path, "bd~bd00.nx", "bd", "bd00", "data", f"bd00_ItemMass_{map_name}.json"
    )


def parse_item_mass(workspace_path: str, map_name: str) -> list[ItemMassEntry]:
    if map_name not in KNOWN_MAP_NAMES:
        raise ItemMassParseError(f"Unknown map name: {map_name!r}")

    path = _file_path(workspace_path, map_name)
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            raw_entries = json.load(f)[map_name]
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as error:
        raise ItemMassParseError(
            f"Could not read Item Mass data for {map_name} from {workspace_path}: {error}"
        ) from error

    entries = []
    for entry in raw_entries:
        if not all(key in entry for key in ("Item", "No")):
            continue  # matches jamboree_board_studio.legacy.editor_modules.item_mass.process_itemmass_data
        entries.append(ItemMassEntry(item=entry["Item"], lot=entry["No"], game_data=entry))
    return entries


def serialize_item_mass(
    entries: list[ItemMassEntry], workspace_path: str, map_name: str
) -> None:
    raw_entries = []
    for entry in entries:
        data = dict(entry.game_data)
        data["Item"] = entry.item
        data["No"] = entry.lot
        raw_entries.append(data)

    with open(_file_path(workspace_path, map_name), "w", encoding="utf-8-sig") as f:
        json.dump({map_name: raw_entries}, f, indent=4)
