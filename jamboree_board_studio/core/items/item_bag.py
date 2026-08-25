"""Item Bag loot table: format-independent model + adapter.

``bd00_ItemBag_MapXX.json`` holds a per-map list of items obtainable
from Item Bags, split into two "phases" (0 = Standard, 1 = Standard, 5
Last Turns) — see ``jamboree_board_studio/legacy/editor_modules/item_bag.py`` for the existing widget.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

KNOWN_MAP_NAMES = tuple(f"Map{i:02d}" for i in range(1, 8))


class ItemBagParseError(Exception):
    """Raised when a map's Item Bag data can't be read or is structurally invalid."""


@dataclass
class ItemBagEntry:
    item: str
    phase: int
    unique: bool
    game_data: dict = field(default_factory=dict)


def _file_path(workspace_path: str, map_name: str) -> str:
    return os.path.join(
        workspace_path, "bd~bd00.nx", "bd", "bd00", "data", f"bd00_ItemBag_{map_name}.json"
    )


def parse_item_bag(workspace_path: str, map_name: str) -> list[ItemBagEntry]:
    if map_name not in KNOWN_MAP_NAMES:
        raise ItemBagParseError(f"Unknown map name: {map_name!r}")

    path = _file_path(workspace_path, map_name)
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            raw_entries = json.load(f)[map_name]
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as error:
        raise ItemBagParseError(
            f"Could not read Item Bag data for {map_name} from {workspace_path}: {error}"
        ) from error

    entries = []
    for entry in raw_entries:
        if not all(key in entry for key in ("Item", "Phase", "Unique")):
            continue  # matches jamboree_board_studio.legacy.editor_modules.item_bag.process_itembag_data
        entries.append(
            ItemBagEntry(
                item=entry["Item"],
                phase=entry["Phase"],
                unique=bool(entry["Unique"]),
                game_data=entry,
            )
        )
    return entries


def serialize_item_bag(
    entries: list[ItemBagEntry], workspace_path: str, map_name: str
) -> None:
    raw_entries = []
    for entry in entries:
        data = dict(entry.game_data)
        data["Item"] = entry.item
        data["Phase"] = entry.phase
        data["Unique"] = int(entry.unique)
        raw_entries.append(data)

    with open(_file_path(workspace_path, map_name), "w", encoding="utf-8-sig") as f:
        json.dump({map_name: raw_entries}, f, indent=4)
