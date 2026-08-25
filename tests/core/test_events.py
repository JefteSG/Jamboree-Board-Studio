import json
import os

import pytest

from jamboree_board_studio.core.events import (
    EventParseError,
    effective_map_name,
    parse_events,
    serialize_events,
)

LUCKY_FIXTURE = {
    "Map01": [
        {"Rate0": 25.0, "Rate1": 25.0, "Rate2": 25.0, "Rate3": 25.0, "Result": "7Coin", "UnknownField": "keep-me"},
        {"Rate0": 75.0, "Rate1": 75.0, "Rate2": 75.0, "Rate3": 75.0, "Result": "10Coin"},
    ]
}

KOOPA_FIXTURE = {
    "Map00": [
        {"Rate0": 50.0, "Rate1": 50.0, "Rate2": 50.0, "Rate3": 50.0, "Result": "Rob10Coin"},
    ]
}

KOOPA_MAP06_FIXTURE = {
    "Map06": [
        {"Rate0": 10.0, "Rate1": 10.0, "Rate2": 10.0, "Rate3": 10.0, "Result": "Get1000Coin"},
    ]
}


def _write(workspace_path, filename, data):
    data_dir = os.path.join(workspace_path, "bd~bd00.nx", "bd", "bd00", "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, filename), "w", encoding="utf-8-sig") as f:
        json.dump(data, f)
    return data_dir


def _read(workspace_path, filename):
    data_dir = os.path.join(workspace_path, "bd~bd00.nx", "bd", "bd00", "data")
    with open(os.path.join(data_dir, filename), "r", encoding="utf-8-sig") as f:
        return json.load(f)


def test_effective_map_name_shares_koopa_mass_except_map06():
    assert effective_map_name("Map01", "KoopaMass") == "Map00"
    assert effective_map_name("Map05", "KoopaMass") == "Map00"
    assert effective_map_name("Map06", "KoopaMass") == "Map06"
    assert effective_map_name("Map01", "LuckyMass") == "Map01"
    assert effective_map_name("Map01", "UnluckyMass") == "Map01"


def test_parse_extracts_known_fields(tmp_path):
    _write(str(tmp_path), "bd00_LuckyMass_Map01.json", LUCKY_FIXTURE)

    entries = parse_events(str(tmp_path), "Map01", "LuckyMass")

    assert [e.result for e in entries] == ["7Coin", "10Coin"]
    assert entries[0].rate0 == 25.0
    assert entries[1].rate3 == 75.0


def test_parse_preserves_unknown_field(tmp_path):
    _write(str(tmp_path), "bd00_LuckyMass_Map01.json", LUCKY_FIXTURE)

    entries = parse_events(str(tmp_path), "Map01", "LuckyMass")

    assert entries[0].game_data["UnknownField"] == "keep-me"


def test_parse_koopa_mass_reads_shared_map00_file_for_non_map06(tmp_path):
    _write(str(tmp_path), "bd00_KoopaMass_Map00.json", KOOPA_FIXTURE)

    for map_name in ("Map01", "Map02", "Map05", "Map07"):
        entries = parse_events(str(tmp_path), map_name, "KoopaMass")
        assert [e.result for e in entries] == ["Rob10Coin"]


def test_parse_koopa_mass_reads_its_own_file_for_map06(tmp_path):
    _write(str(tmp_path), "bd00_KoopaMass_Map06.json", KOOPA_MAP06_FIXTURE)

    entries = parse_events(str(tmp_path), "Map06", "KoopaMass")

    assert [e.result for e in entries] == ["Get1000Coin"]


def test_round_trip_preserves_data_with_no_edits(tmp_path):
    _write(str(tmp_path), "bd00_LuckyMass_Map01.json", LUCKY_FIXTURE)

    entries = parse_events(str(tmp_path), "Map01", "LuckyMass")
    serialize_events(entries, str(tmp_path), "Map01", "LuckyMass")

    assert _read(str(tmp_path), "bd00_LuckyMass_Map01.json") == LUCKY_FIXTURE


def test_round_trip_preserves_data_after_editing_a_rate(tmp_path):
    _write(str(tmp_path), "bd00_LuckyMass_Map01.json", LUCKY_FIXTURE)

    entries = parse_events(str(tmp_path), "Map01", "LuckyMass")
    entries[1].rate0 = 999.0
    serialize_events(entries, str(tmp_path), "Map01", "LuckyMass")

    result = _read(str(tmp_path), "bd00_LuckyMass_Map01.json")["Map01"]
    changed = next(e for e in result if e["Result"] == "10Coin")
    assert changed["Rate0"] == 999.0

    unchanged = next(e for e in result if e["Result"] == "7Coin")
    assert unchanged["UnknownField"] == "keep-me"


def test_round_trip_koopa_mass_writes_back_to_shared_map00_file(tmp_path):
    _write(str(tmp_path), "bd00_KoopaMass_Map00.json", KOOPA_FIXTURE)

    entries = parse_events(str(tmp_path), "Map03", "KoopaMass")
    serialize_events(entries, str(tmp_path), "Map03", "KoopaMass")

    assert _read(str(tmp_path), "bd00_KoopaMass_Map00.json") == KOOPA_FIXTURE


def test_missing_file_raises_parse_error(tmp_path):
    with pytest.raises(EventParseError):
        parse_events(str(tmp_path), "Map01", "LuckyMass")


def test_unknown_map_name_raises_parse_error(tmp_path):
    _write(str(tmp_path), "bd00_LuckyMass_Map01.json", LUCKY_FIXTURE)

    with pytest.raises(EventParseError):
        parse_events(str(tmp_path), "Map99", "LuckyMass")


def test_unknown_data_type_raises_parse_error(tmp_path):
    _write(str(tmp_path), "bd00_LuckyMass_Map01.json", LUCKY_FIXTURE)

    with pytest.raises(EventParseError):
        parse_events(str(tmp_path), "Map01", "BogusMass")
