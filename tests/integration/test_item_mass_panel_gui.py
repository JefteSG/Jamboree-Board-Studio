"""GUI tests for the new "Item Mass (Preview)" panel.

Like ItemBagPanel, this panel keeps no data of its own -- it registers
as a listener on the same ItemMassDataManager the original "Item Mass"
tab's ItemMassEditor uses, and edits go back through that manager's
update_item_mass_data, exactly like the legacy widget's own edits do.
These tests prove that sharing works in both directions (new panel ->
legacy widget's listboxes, and legacy widget -> new panel's tree), not
just that the new panel renders.
"""

import json
import os


def _listbox_items(listbox):
    return [listbox.get(i) for i in range(listbox.size())]


def test_item_mass_panel_loads_entries_from_the_shared_manager(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.item_mass_panel

    rows = panel.tree.get_children()
    values = [panel.tree.item(r, "values") for r in rows]

    assert any(v[0] == "Kinoko" and int(v[1]) == 0 for v in values)
    assert any(v[0] == "GoldPipe" and int(v[1]) == 1 for v in values)


def test_selecting_a_row_shows_it_in_the_inspector(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.item_mass_panel

    first_row = panel.tree.get_children()[0]
    panel.tree.selection_set(first_row)
    app.update()

    assert panel.selected_entry is not None
    assert str(panel.apply_button["state"]) == "normal"
    assert panel.item_combobox.get() == panel.selected_entry.item


def test_applying_an_edit_updates_the_legacy_widgets_listbox_too(tk_app):
    # The real point of sharing ItemMassDataManager: an edit made in the
    # new panel must show up in the *original* "Item Mass" tab's
    # listboxes without any extra glue code, because both are views over
    # the same manager.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.item_mass_panel

    kinoko_row = next(
        r for r in panel.tree.get_children() if panel.tree.item(r, "values")[0] == "Kinoko"
    )
    panel.tree.selection_set(kinoko_row)
    app.update()

    panel.item_combobox.set("GoldDoubleDice")
    panel.lot_combobox.set("2")
    panel._apply()
    app.update()

    lot2_legacy_items = _listbox_items(first_tab.item_mass.lots[2]["listbox"])
    assert "GoldDoubleDice" in lot2_legacy_items
    lot0_legacy_items = _listbox_items(first_tab.item_mass.lots[0]["listbox"])
    assert "Kinoko" not in lot0_legacy_items


def test_editing_from_the_legacy_widget_refreshes_the_panel(tk_app):
    # And the other direction: an add via the legacy ItemMassEditor must
    # show up in the new panel's tree too.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    editor = first_tab.item_mass
    panel = first_tab.item_mass_panel

    editor.lots[3]["entry"].set("WarpBox")
    editor.add_item(3, editor.lots[3]["entry"])
    app.update()

    rows = panel.tree.get_children()
    values = [panel.tree.item(r, "values") for r in rows]
    assert any(v[0] == "WarpBox" and int(v[1]) == 3 for v in values)


def test_save_persists_the_panels_edit_to_disk(tk_app, full_workspace):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.item_mass_panel

    goldpipe_row = next(
        r for r in panel.tree.get_children() if panel.tree.item(r, "values")[0] == "GoldPipe"
    )
    panel.tree.selection_set(goldpipe_row)
    app.update()
    panel.item_combobox.set("ShoppingPipe")
    panel.lot_combobox.set("5")
    panel._apply()
    app.update()

    app.save_data()
    app.update()

    data_dir = os.path.join(full_workspace, "bd~bd00.nx", "bd", "bd00", "data")
    with open(os.path.join(data_dir, "bd00_ItemMass_Map01.json"), "r", encoding="utf-8-sig") as f:
        item_mass = json.load(f)["Map01"]

    assert any(e["Item"] == "ShoppingPipe" and e["No"] == 5 for e in item_mass)
    assert not any(e["Item"] == "GoldPipe" for e in item_mass)
    # Entries added/edited by earlier tests in this module-scoped session
    # must still be there -- confirms this save was an edit, not a
    # silent full replacement.
    assert any(e["Item"] == "GoldDoubleDice" for e in item_mass)
    assert any(e["Item"] == "WarpBox" for e in item_mass)
