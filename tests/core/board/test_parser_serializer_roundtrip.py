"""Round-trip tests for the Board parser/serializer adapter.

No real Super Mario Party Jamboree dump is available in this environment
(the project never bundles game files — see README). These fixtures are
*synthetic*, built only from the field names/shapes already confirmed by
the existing ``editor_modules.map_layout`` loader (``NodeNo``, ``MassAttr``,
``NpcNodeNo0``, and the ``MapPath`` -> ``Path`` -> ``Bezier`` structure).
They intentionally include fields this parser does not interpret
("UnknownNodeField", "SomeExtraPathField") to prove those are preserved
by a parse -> serialize cycle, not dropped.
"""

import json
import os

import pytest

from jamboree_board_studio.core.board.parser import BoardParseError, parse_board
from jamboree_board_studio.core.board.serializer import serialize_board

MAP_NODE_FIXTURE = {
    "MapNode": [
        {"NodeNo": 0, "MassAttr": "Lucky", "NpcNodeNo0": -1, "UnknownNodeField": 42},
        {"NodeNo": 1, "MassAttr": "Unlucky", "NpcNodeNo0": -1},
        {"NodeNo": 2, "MassAttr": "", "NpcNodeNo0": 5},
    ]
}

MAP_PATH_FIXTURE = {
    "MapPath": [
        {
            "NodeNo": 0,
            "Path": [
                {
                    "NodeNo": 1,
                    "Bezier": [
                        {
                            "Position0X": 0.0,
                            "Position0Z": 0.0,
                            "Position1X": 1.0,
                            "Position1Z": 0.0,
                        }
                    ],
                }
            ],
        },
        {
            "NodeNo": 1,
            "SomeExtraPathField": "keep-me",
            "Path": [
                {
                    "NodeNo": 2,
                    "Bezier": [
                        {
                            "Position0X": 1.0,
                            "Position0Z": 0.0,
                            "Position1X": 2.0,
                            "Position1Z": 0.0,
                        }
                    ],
                }
            ],
        },
    ]
}


def _write_workspace_fixture(workspace_path):
    data_dir = os.path.join(workspace_path, "bd~bd01.nx", "bd", "bd01", "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(
        os.path.join(data_dir, "bd01_MapNode.json"), "w", encoding="utf-8-sig"
    ) as f:
        json.dump(MAP_NODE_FIXTURE, f)
    with open(
        os.path.join(data_dir, "bd01_MapPath.json"), "w", encoding="utf-8-sig"
    ) as f:
        json.dump(MAP_PATH_FIXTURE, f)
    return data_dir


def test_parse_board_extracts_known_fields(tmp_path):
    _write_workspace_fixture(str(tmp_path))

    board = parse_board(str(tmp_path), "Map01")

    assert board.id == "Map01"
    assert [s.id for s in board.spaces] == ["0", "1", "2"]
    assert [s.type for s in board.spaces] == ["Lucky", "Unlucky", ""]


def test_parse_board_does_not_invent_positions(tmp_path):
    _write_workspace_fixture(str(tmp_path))

    board = parse_board(str(tmp_path), "Map01")

    assert all(space.position is None for space in board.spaces)
    assert all(space.visual_position is None for space in board.spaces)


def test_parse_board_populates_connections_from_map_path(tmp_path):
    _write_workspace_fixture(str(tmp_path))

    board = parse_board(str(tmp_path), "Map01")

    pairs = {(c.source, c.target) for c in board.connections}
    assert pairs == {("0", "1"), ("1", "2")}


def test_parse_board_preserves_unknown_node_field_in_game_data(tmp_path):
    _write_workspace_fixture(str(tmp_path))

    board = parse_board(str(tmp_path), "Map01")

    assert board.get_space("0").game_data["UnknownNodeField"] == 42


def test_parse_board_preserves_unknown_path_entry_field_in_metadata(tmp_path):
    _write_workspace_fixture(str(tmp_path))

    board = parse_board(str(tmp_path), "Map01")

    assert board.metadata["map_path_extra"]["1"] == {
        "SomeExtraPathField": "keep-me"
    }


def test_round_trip_preserves_all_data_with_no_edits(tmp_path):
    _write_workspace_fixture(str(tmp_path))

    board = parse_board(str(tmp_path), "Map01")
    serialize_board(board, str(tmp_path))

    data_dir = os.path.join(str(tmp_path), "bd~bd01.nx", "bd", "bd01", "data")
    with open(
        os.path.join(data_dir, "bd01_MapNode.json"), "r", encoding="utf-8-sig"
    ) as f:
        node_result = json.load(f)
    with open(
        os.path.join(data_dir, "bd01_MapPath.json"), "r", encoding="utf-8-sig"
    ) as f:
        path_result = json.load(f)

    assert node_result == MAP_NODE_FIXTURE
    assert path_result == MAP_PATH_FIXTURE


def test_round_trip_preserves_data_after_editing_a_space_type(tmp_path):
    _write_workspace_fixture(str(tmp_path))

    board = parse_board(str(tmp_path), "Map01")
    board.get_space("2").type = "Chance"
    serialize_board(board, str(tmp_path))

    data_dir = os.path.join(str(tmp_path), "bd~bd01.nx", "bd", "bd01", "data")
    with open(
        os.path.join(data_dir, "bd01_MapNode.json"), "r", encoding="utf-8-sig"
    ) as f:
        node_result = json.load(f)

    changed_node = next(n for n in node_result["MapNode"] if n["NodeNo"] == 2)
    assert changed_node["MassAttr"] == "Chance"
    assert changed_node["NpcNodeNo0"] == 5

    unchanged_node = next(n for n in node_result["MapNode"] if n["NodeNo"] == 0)
    assert unchanged_node["UnknownNodeField"] == 42

    with open(
        os.path.join(data_dir, "bd01_MapPath.json"), "r", encoding="utf-8-sig"
    ) as f:
        path_result = json.load(f)
    assert path_result == MAP_PATH_FIXTURE


def test_parse_board_missing_files_raises_board_parse_error(tmp_path):
    with pytest.raises(BoardParseError):
        parse_board(str(tmp_path), "Map01")


def test_parse_board_rejects_unknown_map_name(tmp_path):
    _write_workspace_fixture(str(tmp_path))

    with pytest.raises(BoardParseError):
        parse_board(str(tmp_path), "Map99")
