import json
import os

import pytest

from jamboree_board_studio.core.items.item_mass import (
    ItemMassParseError,
    parse_item_mass,
    serialize_item_mass,
)

FIXTURE = {
    "Map01": [
        {"Item": "Kinoko", "No": 0, "UnknownField": "keep-me"},
        {"Item": "Stone", "No": 1},
        {"Item": "10CoinTakeMass", "No": 5},
    ]
}


def _write_fixture(workspace_path, map_name="Map01"):
    data_dir = os.path.join(workspace_path, "bd~bd00.nx", "bd", "bd00", "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(
        os.path.join(data_dir, f"bd00_ItemMass_{map_name}.json"), "w", encoding="utf-8-sig"
    ) as f:
        json.dump(FIXTURE, f)
    return data_dir


def test_parse_extracts_known_fields(tmp_path):
    _write_fixture(str(tmp_path))

    entries = parse_item_mass(str(tmp_path), "Map01")

    assert [e.item for e in entries] == ["Kinoko", "Stone", "10CoinTakeMass"]
    assert [e.lot for e in entries] == [0, 1, 5]


def test_parse_preserves_unknown_field(tmp_path):
    _write_fixture(str(tmp_path))

    entries = parse_item_mass(str(tmp_path), "Map01")

    assert entries[0].game_data["UnknownField"] == "keep-me"


def test_round_trip_preserves_data_with_no_edits(tmp_path):
    _write_fixture(str(tmp_path))

    entries = parse_item_mass(str(tmp_path), "Map01")
    serialize_item_mass(entries, str(tmp_path), "Map01")

    data_dir = os.path.join(str(tmp_path), "bd~bd00.nx", "bd", "bd00", "data")
    with open(os.path.join(data_dir, "bd00_ItemMass_Map01.json"), "r", encoding="utf-8-sig") as f:
        result = json.load(f)

    assert result == FIXTURE


def test_round_trip_preserves_data_after_editing_item(tmp_path):
    _write_fixture(str(tmp_path))

    entries = parse_item_mass(str(tmp_path), "Map01")
    entries[1].item = "GoldPipe"
    serialize_item_mass(entries, str(tmp_path), "Map01")

    data_dir = os.path.join(str(tmp_path), "bd~bd00.nx", "bd", "bd00", "data")
    with open(os.path.join(data_dir, "bd00_ItemMass_Map01.json"), "r", encoding="utf-8-sig") as f:
        result = json.load(f)

    changed = result["Map01"][1]
    assert changed["Item"] == "GoldPipe"
    assert changed["No"] == 1

    unchanged = result["Map01"][0]
    assert unchanged["UnknownField"] == "keep-me"


def test_missing_file_raises_parse_error(tmp_path):
    with pytest.raises(ItemMassParseError):
        parse_item_mass(str(tmp_path), "Map01")


def test_unknown_map_name_raises_parse_error(tmp_path):
    _write_fixture(str(tmp_path))

    with pytest.raises(ItemMassParseError):
        parse_item_mass(str(tmp_path), "Map99")
