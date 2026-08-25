"""Adapter: game workspace JSON -> internal Board model.

This reads the same files and expects the same shape as the existing
``editor_modules.map_layout.load_map_layout_mapdata`` (``bdXX_MapNode.json``
/ ``bdXX_MapPath.json``), but does not import that module directly: it is
a Tkinter/matplotlib UI widget module, and the domain layer must stay
free of UI dependencies so it can be used and tested headlessly. If
``editor_modules`` is ever split into UI-only code, this small
duplication (~file path + JSON load) should be collapsed in favour of a
single shared loader.

Round-trip contract: every ``MapNode``/``MapPath`` entry is kept, in full,
as ``game_data`` on the resulting ``BoardSpace``/``BoardConnection``
objects, so fields this parser does not interpret are not lost. See
``serializer.py`` for the inverse operation.
"""

from __future__ import annotations

import json

from jamboree_board_studio.core.board.models import Board, BoardConnection, BoardSpace
from jamboree_board_studio.core.board.paths import map_layout_file_path

KNOWN_MAP_NAMES = tuple(f"Map{i:02d}" for i in range(1, 8))


class BoardParseError(Exception):
    """Raised when a board's game data cannot be read or is structurally invalid."""


def load_raw_map_layout(workspace_path: str, map_name: str) -> dict:
    """Read MapNode + MapPath JSON for a map, without transforming them.

    Returns ``{"MapNode": [...], "MapPath": [...]}``.

    Unlike the legacy loader (which silently falls back to empty lists on
    a missing/invalid file), this raises ``BoardParseError`` so callers
    can distinguish "board has no paths" from "board data could not be
    read" — important once this feeds a UI that shouldn't silently show
    an empty board for what is actually a broken workspace.
    """
    node_path = map_layout_file_path(workspace_path, map_name, "MapNode")
    path_path = map_layout_file_path(workspace_path, map_name, "MapPath")

    try:
        with open(node_path, "r", encoding="utf-8-sig") as f:
            nodes = json.load(f)["MapNode"]
        with open(path_path, "r", encoding="utf-8-sig") as f:
            paths = json.load(f)["MapPath"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as error:
        raise BoardParseError(
            f"Could not read board layout for {map_name} from {workspace_path}: {error}"
        ) from error

    return {"MapNode": nodes, "MapPath": paths}


def parse_board(
    workspace_path: str, map_name: str, board_name: str | None = None
) -> Board:
    """Parse a single board's spaces and connections from a workspace on disk.

    Space positions are intentionally left as ``None`` (see
    ``BoardSpace.position``): no confirmed, authoritative per-space
    transform has been identified in this format yet — see
    ``docs/research/board-format.md``. Connections *are* populated, from
    ``MapPath``, which is a confirmed adjacency structure already used by
    the legacy Map Layout viewer.
    """
    if map_name not in KNOWN_MAP_NAMES:
        raise BoardParseError(f"Unknown map name: {map_name!r}")

    raw = load_raw_map_layout(workspace_path, map_name)
    return build_board_from_raw(raw, map_name, board_name=board_name)


def build_board_from_raw(
    raw: dict, map_name: str, board_name: str | None = None
) -> Board:
    """Build a Board from an already-loaded ``{"MapNode": [...], "MapPath": [...]}`` dict.

    This is the pure transform used by ``parse_board`` after reading the
    files from disk, but it is also the entry point the UI layer uses to
    build a ``Board`` directly from data the legacy editor already has in
    memory (``editor_modules.map_layout.MapLayoutEditor.map_layout_data``),
    instead of re-reading files. That matters for round-trip safety: it
    keeps a single in-memory copy of each node/segment dict, so an edit
    made through the new ``Board``-based UI is the same object the legacy
    save path serializes — there is no second copy that could go stale or
    be silently overwritten by the other on save.
    """
    spaces = [
        BoardSpace(
            id=str(node["NodeNo"]),
            type=node.get("MassAttr", ""),
            game_data=node,
        )
        for node in raw["MapNode"]
    ]

    connections: list[BoardConnection] = []
    path_entry_extra: dict[str, dict] = {}

    for path_entry in raw["MapPath"]:
        source_id = str(path_entry["NodeNo"])
        extra = {k: v for k, v in path_entry.items() if k not in ("NodeNo", "Path")}
        if extra:
            path_entry_extra[source_id] = extra

        for segment in path_entry.get("Path", []):
            connections.append(
                BoardConnection(
                    source=source_id,
                    target=str(segment.get("NodeNo")),
                    game_data=segment,
                )
            )

    return Board(
        id=map_name,
        name=board_name or map_name,
        spaces=spaces,
        connections=connections,
        metadata={"map_path_extra": path_entry_extra},
    )
