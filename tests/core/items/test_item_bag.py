import json
import os

import pytest

from jamboree_board_studio.core.items.item_bag import (
    ItemBagParseError,
    parse_item_bag,
    serialize_item_bag,
)

FIXTURE = {
    "Map01": [
        {"Item": "Kinoko", "Phase": 0, "Unique": 1, "UnknownField": "keep-me"},
        {"Item": "Stone", "Phase": 0, "Unique": 0},
        {"Item": "DoubleDice", "Phase": 1, "Unique": 0},
    ]
}


def _write_fixture(workspace_path, map_name="Map01"):
    data_dir = os.path.join(workspace_path, "bd~bd00.nx", "bd", "bd00", "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(
        os.path.join(data_dir, f"bd00_ItemBag_{map_name}.json"), "w", encoding="utf-8-sig"
    ) as f:
        json.dump(FIXTURE, f)
    return data_dir


def test_parse_extracts_known_fields(tmp_path):
    _write_fixture(str(tmp_path))

    entries = parse_item_bag(str(tmp_path), "Map01")

    assert [e.item for e in entries] == ["Kinoko", "Stone", "DoubleDice"]
    assert [e.phase for e in entries] == [0, 0, 1]
    assert [e.unique for e in entries] == [True, False, False]


def test_parse_preserves_unknown_field(tmp_path):
    _write_fixture(str(tmp_path))

    entries = parse_item_bag(str(tmp_path), "Map01")

    assert entries[0].game_data["UnknownField"] == "keep-me"


def test_round_trip_preserves_data_with_no_edits(tmp_path):
    _write_fixture(str(tmp_path))

    entries = parse_item_bag(str(tmp_path), "Map01")
    serialize_item_bag(entries, str(tmp_path), "Map01")

    data_dir = os.path.join(str(tmp_path), "bd~bd00.nx", "bd", "bd00", "data")
    with open(os.path.join(data_dir, "bd00_ItemBag_Map01.json"), "r", encoding="utf-8-sig") as f:
        result = json.load(f)

    assert result == FIXTURE


def test_round_trip_preserves_data_after_toggling_unique(tmp_path):
    _write_fixture(str(tmp_path))

    entries = parse_item_bag(str(tmp_path), "Map01")
    entries[1].unique = True
    serialize_item_bag(entries, str(tmp_path), "Map01")

    data_dir = os.path.join(str(tmp_path), "bd~bd00.nx", "bd", "bd00", "data")
    with open(os.path.join(data_dir, "bd00_ItemBag_Map01.json"), "r", encoding="utf-8-sig") as f:
        result = json.load(f)

    changed = result["Map01"][1]
    assert changed["Item"] == "Stone"
    assert changed["Unique"] == 1

    unchanged = result["Map01"][0]
    assert unchanged["UnknownField"] == "keep-me"


def test_missing_file_raises_parse_error(tmp_path):
    with pytest.raises(ItemBagParseError):
        parse_item_bag(str(tmp_path), "Map01")


def test_unknown_map_name_raises_parse_error(tmp_path):
    _write_fixture(str(tmp_path))

    with pytest.raises(ItemBagParseError):
        parse_item_bag(str(tmp_path), "Map99")
