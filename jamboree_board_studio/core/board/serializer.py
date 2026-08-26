"""Adapter: internal Board model -> game workspace JSON.

Writes the same files/shape ``parser.py`` reads, mirroring
``jamboree_board_studio.legacy.editor_modules.map_layout.save_map_layout_mapdata``'s conventions (see
``parser.py`` for why this does not import that module directly).
"""

from __future__ import annotations

import json
from collections import OrderedDict

from jamboree_board_studio.core.board.models import Board
from jamboree_board_studio.core.board.paths import map_layout_file_path


def board_to_raw_map_layout(board: Board) -> dict:
    """Rebuild the ``{"MapNode": [...], "MapPath": [...]}`` structure from a Board.

    Each space's ``game_data`` is written back as-is, with ``NodeNo`` and
    ``MassAttr`` kept in sync with ``id``/``type``, so fields this model
    does not interpret are preserved. Connections are regrouped by source
    space into ``MapPath`` entries, restoring any per-entry extra fields
    that were recorded in ``board.metadata["map_path_extra"]`` at parse
    time (see ``parser.parse_board``).
    """
    map_nodes = []
    for space in board.spaces:
        node = dict(space.game_data)
        node["NodeNo"] = int(space.id)
        node["MassAttr"] = space.type
        map_nodes.append(node)

    path_entry_extra = board.metadata.get("map_path_extra", {})
    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    for connection in board.connections:
        grouped.setdefault(connection.source, []).append(dict(connection.game_data))

    # Restore dead-end nodes' {"NodeNo": X, "Path": []} entries (see
    # parser.build_board_from_raw) that would otherwise vanish because they
    # produce zero BoardConnections. Appended after the real paths: original
    # MapPath order isn't known to matter (entries are matched by NodeNo,
    # not position), but this is what's confirmed, not assumed.
    for source_id in board.metadata.get("map_path_empty_sources", []):
        grouped.setdefault(source_id, [])

    map_paths = []
    for source_id, segments in grouped.items():
        entry = dict(path_entry_extra.get(source_id, {}))
        entry["NodeNo"] = int(source_id)
        entry["Path"] = segments
        map_paths.append(entry)

    return {"MapNode": map_nodes, "MapPath": map_paths}


def serialize_board(board: Board, workspace_path: str) -> None:
    """Write a Board's layout back into its workspace's MapNode/MapPath JSON files."""
    raw = board_to_raw_map_layout(board)
    node_path = map_layout_file_path(workspace_path, board.id, "MapNode")
    path_path = map_layout_file_path(workspace_path, board.id, "MapPath")

    with open(node_path, "w", encoding="utf-8-sig") as f:
        json.dump({"MapNode": raw["MapNode"]}, f, ensure_ascii=False, indent=4)

    with open(path_path, "w", encoding="utf-8-sig") as f:
        json.dump({"MapPath": raw["MapPath"]}, f, ensure_ascii=False, indent=4)
