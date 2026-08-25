"""Hidden Block loot table: format-independent model + adapter.

``bd00_HiddenBlock.json`` holds a single global (not per-map) list of
loot entries, each assigned to one of 6 "lots" (``No`` 0-5), shared
across every board — see ``editor_modules/hidden_block.py``'s ``LOTS``
table for the known ``Result`` code -> friendly name mapping (unchanged,
still the source of truth for that; not duplicated here).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

_RELATIVE_PATH = ("bd~bd00.nx", "bd", "bd00", "data", "bd00_HiddenBlock.json")


class HiddenBlockParseError(Exception):
    """Raised when bd00_HiddenBlock.json can't be read or is structurally invalid."""


@dataclass
class HiddenBlockEntry:
    lot: int
    reward: int  # game's numeric reward code: -1 = 1 Star, positive = coin amount
    rate: int
    game_data: dict = field(default_factory=dict)


def _file_path(workspace_path: str) -> str:
    return os.path.join(workspace_path, *_RELATIVE_PATH)


def parse_hidden_blocks(workspace_path: str) -> list[HiddenBlockEntry]:
    """Read every hidden block entry from a workspace.

    Raises ``HiddenBlockParseError`` if the file is missing or invalid,
    rather than silently returning an empty list (the legacy loader's
    behavior) — same fail-fast philosophy as
    ``core.board.parser.parse_board``, so a broken workspace can't be
    mistaken for a genuinely empty one.
    """
    path = _file_path(workspace_path)
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            raw_entries = json.load(f)["HiddenBlock"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as error:
        raise HiddenBlockParseError(
            f"Could not read hidden block data from {workspace_path}: {error}"
        ) from error

    entries = []
    for entry in raw_entries:
        if not all(key in entry for key in ("No", "Result", "Rate")):
            continue  # matches editor_modules.hidden_block.process_hiddenblock_data
        entries.append(
            HiddenBlockEntry(
                lot=entry["No"],
                reward=entry["Result"],
                rate=entry["Rate"],
                game_data=entry,
            )
        )
    return entries


def serialize_hidden_blocks(entries: list[HiddenBlockEntry], workspace_path: str) -> None:
    """Write hidden block entries back to bd00_HiddenBlock.json."""
    raw_entries = []
    for entry in entries:
        data = dict(entry.game_data)
        data["No"] = entry.lot
        data["Result"] = entry.reward
        data["Rate"] = entry.rate
        raw_entries.append(data)

    with open(_file_path(workspace_path), "w", encoding="utf-8-sig") as f:
        json.dump({"HiddenBlock": raw_entries}, f, indent=4)
