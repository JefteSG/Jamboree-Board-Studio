import json
import os

from jamboree_board_studio.core.board.parser import KNOWN_MAP_NAMES
from jamboree_board_studio.core.board.workspace_validation import (
    validate_workspace_boards,
)

VALID_NODE = {"MapNode": [{"NodeNo": 0, "MassAttr": "Lucky", "NpcNodeNo0": -1}]}
VALID_PATH = {"MapPath": []}


def _data_dir(workspace_path, map_index):
    return os.path.join(
        workspace_path, f"bd~bd{map_index:02d}.nx", "bd", f"bd{map_index:02d}", "data"
    )


def _write_map(workspace_path, map_index, node_data, path_data):
    data_dir = _data_dir(workspace_path, map_index)
    os.makedirs(data_dir, exist_ok=True)
    with open(
        os.path.join(data_dir, f"bd{map_index:02d}_MapNode.json"),
        "w",
        encoding="utf-8-sig",
    ) as f:
        json.dump(node_data, f)
    with open(
        os.path.join(data_dir, f"bd{map_index:02d}_MapPath.json"),
        "w",
        encoding="utf-8-sig",
    ) as f:
        json.dump(path_data, f)


def _write_all_valid(workspace_path):
    for i in range(1, 8):
        _write_map(workspace_path, i, VALID_NODE, VALID_PATH)


def test_all_valid_workspace_returns_no_results(tmp_path):
    _write_all_valid(str(tmp_path))

    results = validate_workspace_boards(str(tmp_path))

    assert results == []


def test_missing_board_files_are_reported(tmp_path):
    _write_all_valid(str(tmp_path))
    # Remove Map03's files entirely.
    data_dir = _data_dir(str(tmp_path), 3)
    os.remove(os.path.join(data_dir, "bd03_MapNode.json"))
    os.remove(os.path.join(data_dir, "bd03_MapPath.json"))

    results = validate_workspace_boards(str(tmp_path))

    assert len(results) == 1
    assert results[0].map_name == "Map03"
    assert "Could not read board data" in results[0].messages[0]


def test_structural_issue_is_reported(tmp_path):
    _write_all_valid(str(tmp_path))
    duplicate_node = {
        "MapNode": [
            {"NodeNo": 0, "MassAttr": "Lucky", "NpcNodeNo0": -1},
            {"NodeNo": 0, "MassAttr": "Unlucky", "NpcNodeNo0": -1},
        ]
    }
    _write_map(str(tmp_path), 5, duplicate_node, VALID_PATH)

    results = validate_workspace_boards(str(tmp_path))

    assert len(results) == 1
    assert results[0].map_name == "Map05"
    assert any("Duplicate space id" in m for m in results[0].messages)


def test_checks_every_known_map(tmp_path):
    _write_all_valid(str(tmp_path))
    # Delete only bd07's files; every other map stays valid.
    data_dir = _data_dir(str(tmp_path), 7)
    os.remove(os.path.join(data_dir, "bd07_MapNode.json"))
    os.remove(os.path.join(data_dir, "bd07_MapPath.json"))

    results = validate_workspace_boards(str(tmp_path))

    assert {r.map_name for r in results} == {"Map07"}
    assert len(KNOWN_MAP_NAMES) == 7
