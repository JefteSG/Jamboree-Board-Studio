import json
import os

import pytest

from jamboree_board_studio.core.items.item_shop import (
    PHASES,
    SHOPS,
    SLOTS,
    ItemShopParseError,
    empty_item_shop,
    parse_item_shop,
    serialize_item_shop,
)

# Every (shop, phase) group has exactly 2 real, non-"Stone" entries, so a
# no-edit round trip is unambiguous (doesn't happen to also exercise the
# "all empty -> Stone fallback" behavior, which has its own dedicated test).
FULLY_STOCKED_FIXTURE = {
    "Map01": [
        entry
        for type_value, shop in ((0, "Koopa"), (1, "Kamek"))
        for phase in (0, 1, 2)
        for entry in (
            {
                "Phase": phase,
                "Type": type_value,
                "Item": f"{shop}Item{phase}Slot1",
                "Count": 1,
                "Price": 10,
            },
            {
                "Phase": phase,
                "Type": type_value,
                "Item": f"{shop}Item{phase}Slot2",
                "Count": 2,
                "Price": 20,
            },
        )
    ]
}
# Tag exactly one entry with an unknown field, to test preservation.
FULLY_STOCKED_FIXTURE["Map01"][0]["UnknownField"] = "keep-me"


def _write_fixture(workspace_path, fixture, map_name="Map01"):
    data_dir = os.path.join(workspace_path, "bd~bd00.nx", "bd", "bd00", "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(
        os.path.join(data_dir, f"bd00_ItemShop_{map_name}.json"), "w", encoding="utf-8-sig"
    ) as f:
        json.dump(fixture, f)
    return data_dir


def _read_result(workspace_path, map_name="Map01"):
    data_dir = os.path.join(workspace_path, "bd~bd00.nx", "bd", "bd00", "data")
    with open(
        os.path.join(data_dir, f"bd00_ItemShop_{map_name}.json"), "r", encoding="utf-8-sig"
    ) as f:
        return json.load(f)


def test_empty_item_shop_has_36_slots_all_empty():
    entries = empty_item_shop()

    assert len(entries) == len(SHOPS) * len(PHASES) * len(list(SLOTS))
    assert all(e.item == "Empty" for e in entries)


def test_parse_infers_slot_position_from_file_order(tmp_path):
    _write_fixture(str(tmp_path), FULLY_STOCKED_FIXTURE)

    entries = parse_item_shop(str(tmp_path), "Map01")

    koopa_p0 = [e for e in entries if e.shop == "Koopa" and e.phase == 0]
    assert len(koopa_p0) == 6  # full grid, unused slots filled as Empty
    slot1 = next(e for e in koopa_p0 if e.slot == 1)
    slot2 = next(e for e in koopa_p0 if e.slot == 2)
    slot3 = next(e for e in koopa_p0 if e.slot == 3)
    assert slot1.item == "KoopaItem0Slot1"
    assert slot2.item == "KoopaItem0Slot2"
    assert slot3.item == "Empty"


def test_parse_preserves_unknown_field(tmp_path):
    _write_fixture(str(tmp_path), FULLY_STOCKED_FIXTURE)

    entries = parse_item_shop(str(tmp_path), "Map01")

    slot1 = next(e for e in entries if e.shop == "Koopa" and e.phase == 0 and e.slot == 1)
    assert slot1.game_data["UnknownField"] == "keep-me"


def test_round_trip_preserves_data_with_no_edits(tmp_path):
    _write_fixture(str(tmp_path), FULLY_STOCKED_FIXTURE)

    entries = parse_item_shop(str(tmp_path), "Map01")
    serialize_item_shop(entries, str(tmp_path), "Map01")

    assert _read_result(str(tmp_path)) == FULLY_STOCKED_FIXTURE


def test_round_trip_preserves_data_after_editing_an_item(tmp_path):
    _write_fixture(str(tmp_path), FULLY_STOCKED_FIXTURE)

    entries = parse_item_shop(str(tmp_path), "Map01")
    slot2 = next(e for e in entries if e.shop == "Koopa" and e.phase == 0 and e.slot == 2)
    slot2.item = "GoldPipe"
    serialize_item_shop(entries, str(tmp_path), "Map01")

    result = _read_result(str(tmp_path))["Map01"]
    changed = next(
        e for e in result if e["Type"] == 0 and e["Phase"] == 0 and e["Item"] == "GoldPipe"
    )
    assert changed["Count"] == 2
    assert changed["Price"] == 20

    unchanged = next(
        e for e in result if e["Type"] == 0 and e["Phase"] == 0 and e["Item"] == "KoopaItem0Slot1"
    )
    assert unchanged["UnknownField"] == "keep-me"


def test_serialize_fills_a_fully_empty_group_with_stone_placeholder(tmp_path, capsys):
    entries = empty_item_shop()  # every group empty
    data_dir = os.path.join(str(tmp_path), "bd~bd00.nx", "bd", "bd00", "data")
    os.makedirs(data_dir, exist_ok=True)

    serialize_item_shop(entries, str(tmp_path), "Map01")

    result = _read_result(str(tmp_path))["Map01"]
    assert len(result) == len(SHOPS) * len(PHASES)  # exactly one Stone entry per group
    assert all(e["Item"] == "Stone" and e["Count"] == 1 and e["Price"] == 0 for e in result)
    assert "Replacing 1st empty slot with 'Stone'" in capsys.readouterr().out


def test_missing_file_raises_parse_error(tmp_path):
    with pytest.raises(ItemShopParseError):
        parse_item_shop(str(tmp_path), "Map01")


def test_unknown_map_name_raises_parse_error(tmp_path):
    _write_fixture(str(tmp_path), FULLY_STOCKED_FIXTURE)

    with pytest.raises(ItemShopParseError):
        parse_item_shop(str(tmp_path), "Map99")
