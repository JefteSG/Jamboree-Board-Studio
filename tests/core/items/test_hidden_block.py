import json
import os

import pytest

from jamboree_board_studio.core.items.hidden_block import (
    HiddenBlockParseError,
    parse_hidden_blocks,
    serialize_hidden_blocks,
)

FIXTURE = {
    "HiddenBlock": [
        {"No": 0, "Result": -1, "Rate": 10, "UnknownField": "keep-me"},
        {"No": 1, "Result": 5, "Rate": 20},
        {"No": 5, "Result": 30, "Rate": 5},
    ]
}


def _write_fixture(workspace_path):
    data_dir = os.path.join(workspace_path, "bd~bd00.nx", "bd", "bd00", "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(
        os.path.join(data_dir, "bd00_HiddenBlock.json"), "w", encoding="utf-8-sig"
    ) as f:
        json.dump(FIXTURE, f)
    return data_dir


def test_parse_extracts_known_fields(tmp_path):
    _write_fixture(str(tmp_path))

    entries = parse_hidden_blocks(str(tmp_path))

    assert [e.lot for e in entries] == [0, 1, 5]
    assert [e.reward for e in entries] == [-1, 5, 30]
    assert [e.rate for e in entries] == [10, 20, 5]


def test_parse_preserves_unknown_field_in_game_data(tmp_path):
    _write_fixture(str(tmp_path))

    entries = parse_hidden_blocks(str(tmp_path))

    assert entries[0].game_data["UnknownField"] == "keep-me"


def test_round_trip_preserves_data_with_no_edits(tmp_path):
    _write_fixture(str(tmp_path))

    entries = parse_hidden_blocks(str(tmp_path))
    serialize_hidden_blocks(entries, str(tmp_path))

    data_dir = os.path.join(str(tmp_path), "bd~bd00.nx", "bd", "bd00", "data")
    with open(os.path.join(data_dir, "bd00_HiddenBlock.json"), "r", encoding="utf-8-sig") as f:
        result = json.load(f)

    assert result == FIXTURE


def test_round_trip_preserves_data_after_editing_rate(tmp_path):
    _write_fixture(str(tmp_path))

    entries = parse_hidden_blocks(str(tmp_path))
    entries[1].rate = 999
    serialize_hidden_blocks(entries, str(tmp_path))

    data_dir = os.path.join(str(tmp_path), "bd~bd00.nx", "bd", "bd00", "data")
    with open(os.path.join(data_dir, "bd00_HiddenBlock.json"), "r", encoding="utf-8-sig") as f:
        result = json.load(f)

    changed = next(e for e in result["HiddenBlock"] if e["No"] == 1)
    assert changed["Rate"] == 999

    unchanged = next(e for e in result["HiddenBlock"] if e["No"] == 0)
    assert unchanged["UnknownField"] == "keep-me"


def test_missing_file_raises_parse_error(tmp_path):
    with pytest.raises(HiddenBlockParseError):
        parse_hidden_blocks(str(tmp_path))


def test_malformed_entries_are_dropped(tmp_path):
    data_dir = os.path.join(str(tmp_path), "bd~bd00.nx", "bd", "bd00", "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "bd00_HiddenBlock.json"), "w", encoding="utf-8-sig") as f:
        json.dump({"HiddenBlock": [{"No": 0}, {"No": 1, "Result": 5, "Rate": 20}]}, f)

    entries = parse_hidden_blocks(str(tmp_path))

    assert len(entries) == 1
    assert entries[0].lot == 1
