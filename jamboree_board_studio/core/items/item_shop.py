"""Item Shop (Koopa/Kamek): format-independent model + adapter.

``bd00_ItemShop_MapXX.json`` holds a per-map *flat* list of shop slot
entries — ``{"Phase": 0-2, "Type": 0|1, "Item": str, "Count": int,
"Price": int}``. Slot position (1-6) is **not** stored explicitly in the
file: it is implied by an entry's position within its own (Type, Phase)
group, in file order. This mirrors
``editor_modules.item_shop.read_itemshops``'s own ``slot_tracker`` logic
exactly, so parsing here produces the identical slot assignment the
existing widget already shows — see that function if this ever needs
re-verifying against the original.

Two shops (Koopa: Type 0, Kamek: Type 1) x three phases (0 = Standard,
1 = Standard/5 Last Turns, 2 = Pro Mode) x six slots = 36 conceptual
slots per map. A slot with no entry in the file is represented here as
item ``"Empty"``, matching the widget's own default
(``init_itemshop_slots``).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

KNOWN_MAP_NAMES = tuple(f"Map{i:02d}" for i in range(1, 8))
SHOPS = ("Koopa", "Kamek")
PHASES = (0, 1, 2)
SLOTS = range(1, 7)
_TYPE_BY_SHOP = {"Koopa": 0, "Kamek": 1}
_SHOP_BY_TYPE = {0: "Koopa", 1: "Kamek"}


class ItemShopParseError(Exception):
    """Raised when a map's Item Shop data can't be read or is structurally invalid."""


@dataclass
class ShopSlotEntry:
    shop: str  # "Koopa" or "Kamek"
    phase: int  # 0, 1, or 2
    slot: int  # 1-6, inferred from file order within (shop, phase)
    item: str  # "Empty" if this slot is unused
    count: int
    price: int
    game_data: dict = field(default_factory=dict)


def _file_path(workspace_path: str, map_name: str) -> str:
    return os.path.join(
        workspace_path, "bd~bd00.nx", "bd", "bd00", "data", f"bd00_ItemShop_{map_name}.json"
    )


def empty_item_shop() -> list[ShopSlotEntry]:
    """The full 36-slot grid with every slot empty — the "nothing loaded yet" state."""
    return [
        ShopSlotEntry(shop=shop, phase=phase, slot=slot_no, item="Empty", count=0, price=0)
        for shop in SHOPS
        for phase in PHASES
        for slot_no in SLOTS
    ]


def parse_item_shop(workspace_path: str, map_name: str) -> list[ShopSlotEntry]:
    """Read all 36 shop slots (2 shops x 3 phases x 6 slots) for a board.

    Raises ``ItemShopParseError`` on a missing/invalid file or malformed
    top-level data, matching the fail-fast contract of this project's
    other parsers (``core.board.parser``, the other ``core.items``
    modules) — callers that want the legacy tolerant behavior (treat a
    missing file as "everything empty") do so explicitly by catching
    this, the same way ``editor_modules.item_shop.load_itemshop_mapdata``
    does.
    """
    if map_name not in KNOWN_MAP_NAMES:
        raise ItemShopParseError(f"Unknown map name: {map_name!r}")

    path = _file_path(workspace_path, map_name)
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            raw_entries = json.load(f)[map_name]
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as error:
        raise ItemShopParseError(
            f"Could not read Item Shop data for {map_name} from {workspace_path}: {error}"
        ) from error

    if not isinstance(raw_entries, list):
        raise ItemShopParseError(
            f"Item Shop data for {map_name} is not a list: {raw_entries!r}"
        )

    slot_counters: dict[tuple[str, int], int] = {}
    by_position: dict[tuple[str, int, int], ShopSlotEntry] = {}

    for entry in raw_entries:
        if not all(key in entry for key in ("Phase", "Type", "Item", "Count", "Price")):
            continue
        shop = _SHOP_BY_TYPE.get(entry["Type"])
        phase = entry["Phase"]
        if shop is None or phase not in PHASES:
            continue

        key = (shop, phase)
        slot_no = slot_counters.get(key, 0) + 1
        slot_counters[key] = slot_no
        if slot_no > 6:
            continue  # more entries than the UI has slots for: ignore overflow

        by_position[(shop, phase, slot_no)] = ShopSlotEntry(
            shop=shop,
            phase=phase,
            slot=slot_no,
            item=entry["Item"],
            count=int(entry["Count"]),
            price=int(entry["Price"]),
            game_data=entry,
        )

    return [
        by_position.get((shop, phase, slot_no))
        or ShopSlotEntry(shop=shop, phase=phase, slot=slot_no, item="Empty", count=0, price=0)
        for shop in SHOPS
        for phase in PHASES
        for slot_no in SLOTS
    ]


def serialize_item_shop(
    entries: list[ShopSlotEntry], workspace_path: str, map_name: str
) -> None:
    """Write shop slot entries back to bd00_ItemShop_MapXX.json.

    Empty slots are simply omitted (slot position is positional in this
    format, not stored). If every slot in a (shop, phase) group is
    empty, a single "Stone" placeholder entry is written instead —
    mirrors ``editor_modules.item_shop.save_itemshop_mapdata``'s own
    fallback exactly, including its printed message; apparently an
    entirely empty shop/phase isn't a state the game handles cleanly.
    """
    by_position = {(e.shop, e.phase, e.slot): e for e in entries}

    raw_entries = []
    for shop in SHOPS:
        type_value = _TYPE_BY_SHOP[shop]
        for phase in PHASES:
            slots = [by_position.get((shop, phase, slot_no)) for slot_no in SLOTS]
            non_empty = [s for s in slots if s and s.item != "Empty"]

            if not non_empty:
                print(
                    f"No Item in {map_name} {shop}Shop in Phase {phase}, "
                    "Replacing 1st empty slot with 'Stone'"
                )
                raw_entries.append(
                    {"Phase": phase, "Type": type_value, "Item": "Stone", "Count": 1, "Price": 0}
                )
                continue

            for slot in non_empty:
                data = dict(slot.game_data)
                data["Phase"] = phase
                data["Type"] = type_value
                data["Item"] = slot.item
                data["Count"] = slot.count
                data["Price"] = slot.price
                raw_entries.append(data)

    with open(_file_path(workspace_path, map_name), "w", encoding="utf-8-sig") as f:
        json.dump({map_name: raw_entries}, f)
