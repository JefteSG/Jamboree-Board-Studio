"""Lucky/Unlucky/Bowser(Koopa) Mass events: format-independent model + adapter.

``bd00_{LuckyMass,UnluckyMass,KoopaMass}_<map-or-Map00>.json`` each hold
a list of weighted-random event entries: four independent rate columns
(``Rate0``-``Rate3``, one per turn-count bracket) and a ``Result`` drawn
from a fixed list per event type (e.g. "7Coin", "Rob3Coin" — see
``jamboree_board_studio.legacy.editor_modules.events.result_options``, unchanged/still the source of
truth for that list).

KoopaMass ("Bowser Events") is special: every board except Map06 (King
Bowser's Keep) shares the *same* file, keyed "Map00" rather than its own
map name. ``jamboree_board_studio.legacy.editor_modules.events.EventDataManager`` keeps those boards'
in-memory copies in sync live at runtime as the user edits — that's UI
orchestration behavior, not file structure, so it stays there untouched;
this module only knows about the on-disk file-sharing convention
(``effective_map_name``), which both this adapter and that manager's
own remapping already independently agreed on.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

KNOWN_MAP_NAMES = tuple(f"Map{i:02d}" for i in range(1, 8))
DATA_TYPES = ("LuckyMass", "UnluckyMass", "KoopaMass")


class EventParseError(Exception):
    """Raised when an event file can't be read or is structurally invalid."""


@dataclass
class EventEntry:
    rate0: float
    rate1: float
    rate2: float
    rate3: float
    result: str
    game_data: dict = field(default_factory=dict)


def effective_map_name(map_name: str, data_type: str) -> str:
    """The map name actually used in the file path/JSON key for this event type.

    KoopaMass is shared across every board except Map06, stored under
    "Map00" instead of each board's own name — mirrors
    ``jamboree_board_studio.legacy.editor_modules.events.load_event_mapdata``'s own remapping.
    """
    if data_type == "KoopaMass" and map_name != "Map06":
        return "Map00"
    return map_name


def _file_path(workspace_path: str, map_name: str, data_type: str) -> str:
    effective = effective_map_name(map_name, data_type)
    return os.path.join(
        workspace_path, "bd~bd00.nx", "bd", "bd00", "data", f"bd00_{data_type}_{effective}.json"
    )


def parse_events(workspace_path: str, map_name: str, data_type: str) -> list[EventEntry]:
    if map_name not in KNOWN_MAP_NAMES:
        raise EventParseError(f"Unknown map name: {map_name!r}")
    if data_type not in DATA_TYPES:
        raise EventParseError(f"Unknown event data type: {data_type!r}")

    effective = effective_map_name(map_name, data_type)
    path = _file_path(workspace_path, map_name, data_type)
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            raw_entries = json.load(f)[effective]
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as error:
        raise EventParseError(
            f"Could not read {data_type} data for {map_name} from {workspace_path}: {error}"
        ) from error

    entries = []
    for entry in raw_entries:
        if not all(key in entry for key in ("Rate0", "Rate1", "Rate2", "Rate3", "Result")):
            continue  # matches jamboree_board_studio.legacy.editor_modules.events.process_event_data
        entries.append(
            EventEntry(
                rate0=entry["Rate0"],
                rate1=entry["Rate1"],
                rate2=entry["Rate2"],
                rate3=entry["Rate3"],
                result=entry["Result"],
                game_data=entry,
            )
        )
    return entries


def serialize_events(
    entries: list[EventEntry], workspace_path: str, map_name: str, data_type: str
) -> None:
    effective = effective_map_name(map_name, data_type)
    raw_entries = []
    for entry in entries:
        data = dict(entry.game_data)
        data["Rate0"] = entry.rate0
        data["Rate1"] = entry.rate1
        data["Rate2"] = entry.rate2
        data["Rate3"] = entry.rate3
        data["Result"] = entry.result
        raw_entries.append(data)

    with open(_file_path(workspace_path, map_name, data_type), "w", encoding="utf-8-sig") as f:
        json.dump({effective: raw_entries}, f, indent=4)
