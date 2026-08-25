"""GUI tests for ItemShopDataManager and the new "Item Shop (Preview)" panel.

Item Shop's ItemShopEditor already had a real live data object before
this (a nested {"KoopaShop": {...}, "KamekShop": {...}} dict shared by
both shop editors for a map) -- it just wasn't reachable outside them,
and wasn't updated until save_shop_data()/randomize_shop_data() wrote to
it. ItemShopDataManager makes that dict reachable by a second view (this
panel) and keeps it live: save/randomize now push into the manager
immediately, the same way ItemBagEditor.add_item() does for Item Bag.

These tests prove sharing works in both directions (panel -> legacy
"Koopa Shop"/"Kamek Shop" tabs' widgets, and legacy widgets -> panel),
not just that the new panel renders, plus a disk round trip.
"""

import json
import os


def test_item_shop_panel_loads_entries_from_the_shared_manager(tk_app):
    # The fixture workspace's Map01 has one entry per shop in Phase 0:
    # KoopaShop slot 1 = Kinoko, KamekShop slot 1 = Stone -- see
    # tests/integration/conftest.py.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.item_shop_panel

    rows = panel.tree.get_children()
    values = [panel.tree.item(r, "values") for r in rows]

    assert len(values) == 36  # 2 shops x 3 phases x 6 slots, always all present
    assert any(
        v[0] == "Koopa"
        and v[1] == "Standard"
        and int(v[2]) == 1
        and v[3] == "Kinoko"
        and int(v[4]) == 1
        and int(v[5]) == 10
        for v in values
    )
    assert any(
        v[0] == "Kamek"
        and v[1] == "Standard"
        and int(v[2]) == 1
        and v[3] == "Stone"
        and int(v[4]) == 2
        and int(v[5]) == 20
        for v in values
    )
    # Every other slot is the "nothing here" default.
    assert any(v[3] == "Empty" for v in values)


def test_selecting_a_row_shows_it_in_the_inspector(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.item_shop_panel

    row = next(
        r
        for r in panel.tree.get_children()
        if panel.tree.item(r, "values")[3] == "Kinoko"
    )
    panel.tree.selection_set(row)
    app.update()

    assert panel.selected_entry is not None
    assert str(panel.apply_button["state"]) == "normal"
    assert panel.item_combobox.get() == "Kinoko"


def test_applying_an_edit_updates_the_legacy_widgets_too(tk_app):
    # The real point of sharing ItemShopDataManager: an edit made in the
    # new panel must show up in the *original* "Koopa Shop" tab's slot 1
    # widgets without any extra glue code, because both are views over
    # the same manager.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.item_shop_panel

    row = next(
        r
        for r in panel.tree.get_children()
        if panel.tree.item(r, "values")[0] == "Koopa"
        and panel.tree.item(r, "values")[1] == "Standard"
        and int(panel.tree.item(r, "values")[2]) == 1
    )
    panel.tree.selection_set(row)
    app.update()

    panel.item_combobox.set("GoldPipe")
    panel.count_combobox.set(2)
    panel.price_spinbox.delete(0, "end")
    panel.price_spinbox.insert(0, "77")
    panel._apply()
    app.update()

    koopa_slot1 = first_tab.koopa_shop.widgets["P0"]["slot1"]
    assert koopa_slot1["item"].get() == "GoldPipe"
    assert str(koopa_slot1["count"].get()) == "2"
    assert koopa_slot1["price"].get() == "77"


def test_editing_from_the_legacy_widget_refreshes_the_panel(tk_app):
    # And the other direction: a save via the legacy ItemShopEditor
    # (Kamek Shop this time) must show up in the new panel's tree too.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    kamek_shop = first_tab.kamek_shop
    panel = first_tab.item_shop_panel

    kamek_shop.widgets["P1"]["slot3"]["item"].set("WarpBox")
    kamek_shop.widgets["P1"]["slot3"]["count"].set(1)
    kamek_shop.widgets["P1"]["slot3"]["price"].delete(0, "end")
    kamek_shop.widgets["P1"]["slot3"]["price"].insert(0, "15")
    kamek_shop.save_shop_data("P1")
    app.update()

    rows = panel.tree.get_children()
    values = [panel.tree.item(r, "values") for r in rows]
    assert any(
        v[0] == "Kamek"
        and v[1] == "Standard (5 Last Turns)"
        and int(v[2]) == 3
        and v[3] == "WarpBox"
        and int(v[4]) == 1
        and int(v[5]) == 15
        for v in values
    )


def test_randomize_on_the_legacy_widget_also_refreshes_the_panel(tk_app):
    # randomize_shop_data() previously only touched widgets, never
    # data_store, until the next explicit save -- confirms it now also
    # keeps the manager (and this panel) live.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    koopa_shop = first_tab.koopa_shop
    panel = first_tab.item_shop_panel

    koopa_shop.randomize_shop_data("P2")
    app.update()

    expected_slot5_item = koopa_shop.widgets["P2"]["slot5"]["item"].get()
    row = next(
        r
        for r in panel.tree.get_children()
        if panel.tree.item(r, "values")[0] == "Koopa"
        and panel.tree.item(r, "values")[1] == "Pro Mode"
        and int(panel.tree.item(r, "values")[2]) == 5
    )
    assert panel.tree.item(row, "values")[3] == expected_slot5_item


def test_save_persists_the_panels_edit_to_disk(tk_app, full_workspace):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.item_shop_panel

    row = next(
        r
        for r in panel.tree.get_children()
        if panel.tree.item(r, "values")[0] == "Koopa"
        and panel.tree.item(r, "values")[1] == "Standard"
        and int(panel.tree.item(r, "values")[2]) == 1
    )
    panel.tree.selection_set(row)
    app.update()
    panel.item_combobox.set("ShoppingPipe")
    panel.count_combobox.set(1)
    panel.price_spinbox.delete(0, "end")
    panel.price_spinbox.insert(0, "42")
    panel._apply()
    app.update()

    app.save_data()
    app.update()

    data_dir = os.path.join(full_workspace, "bd~bd00.nx", "bd", "bd00", "data")
    with open(os.path.join(data_dir, "bd00_ItemShop_Map01.json"), "r", encoding="utf-8-sig") as f:
        item_shop = json.load(f)["Map01"]

    koopa_phase0 = [e for e in item_shop if e["Type"] == 0 and e["Phase"] == 0]
    assert any(
        e["Item"] == "ShoppingPipe" and e["Count"] == 1 and e["Price"] == 42
        for e in koopa_phase0
    )
