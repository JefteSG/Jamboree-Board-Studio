"""GUI tests for the new "Hidden Block (Preview)" panel.

This is the first panel built in board vocabulary for something other
than the Board Workspace tab, and it deliberately does *not* keep its
own copy of the data or sync rules — it registers as a listener on the
same HiddenBlockDataManager the original "Hidden Block" tab uses, and
edits go back through that manager's update_hiddenblock_data/
sync_with_linked_maps, exactly like the legacy widget's own edits do.
These tests exist to prove that sharing actually works in both
directions (new panel -> legacy widget, and the cross-map broadcast),
not just that the new panel renders.
"""

import json
import os

import pytest

# hidden_block.py imports tkinter at module scope; guard this import the
# same way conftest.py's tk_app fixture does, so this file still collects
# (and its tests still skip cleanly via tk_app) on a Python without
# Tkinter installed, instead of failing collection for the whole suite.
pytest.importorskip("tkinter")
from jamboree_board_studio.legacy.editor_modules.hidden_block import get_lot_name_by_data


def _listbox_items(listbox):
    return [listbox.get(i) for i in range(listbox.size())]


def test_hidden_block_panel_loads_entries_from_the_shared_manager(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])

    rows = first_tab.hidden_block_panel.tree.get_children()
    values = [first_tab.hidden_block_panel.tree.item(r, "values") for r in rows]
    rows_by_lot = {int(v[0]): v for v in values}

    assert rows_by_lot[0][1] == get_lot_name_by_data(-1)
    assert int(rows_by_lot[0][2]) == 10
    assert rows_by_lot[1][1] == get_lot_name_by_data(5)
    assert int(rows_by_lot[1][2]) == 20


def test_selecting_a_row_shows_it_in_the_inspector(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.hidden_block_panel

    first_row = panel.tree.get_children()[0]
    panel.tree.selection_set(first_row)
    app.update()

    assert panel.selected_entry is not None
    assert str(panel.apply_button["state"]) == "normal"
    assert panel.reward_combobox.get() == get_lot_name_by_data(panel.selected_entry.reward)


def test_applying_an_edit_updates_the_legacy_widgets_listbox_too(tk_app):
    # The real point of sharing HiddenBlockDataManager: an edit made in
    # the new panel must show up in the *original* "Hidden Block" tab's
    # listboxes without any extra glue code, because both are views over
    # the same manager.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.hidden_block_panel

    lot0_row = next(
        r for r in panel.tree.get_children() if int(panel.tree.item(r, "values")[0]) == 0
    )
    panel.tree.selection_set(lot0_row)
    app.update()

    panel.reward_combobox.set("10 Coins")
    panel.rate_spinbox.delete(0, "end")
    panel.rate_spinbox.insert(0, "77")
    panel._apply()
    app.update()

    lot0_legacy_items = _listbox_items(first_tab.hidden_block.lots[0]["listbox"])
    assert any("10 Coins" in text and "Rate: 77" in text for text in lot0_legacy_items)


def test_applying_an_edit_broadcasts_to_every_other_map(tk_app):
    # Hidden Block is shared across all 7 boards (no Map06 exception,
    # unlike KoopaMass) -- editing it from Map01's new panel must be
    # visible on every other map's tab too.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    other_tab = app.notebook.nametowidget(app.notebook.tabs()[3])
    panel = first_tab.hidden_block_panel

    lot1_row = next(
        r for r in panel.tree.get_children() if int(panel.tree.item(r, "values")[0]) == 1
    )
    panel.tree.selection_set(lot1_row)
    app.update()

    panel.reward_combobox.set("30 Coins")
    panel.rate_spinbox.delete(0, "end")
    panel.rate_spinbox.insert(0, "42")
    panel._apply()
    app.update()

    other_lot1_items = _listbox_items(other_tab.hidden_block.lots[1]["listbox"])
    assert any("30 Coins" in text and "Rate: 42" in text for text in other_lot1_items)


def test_save_persists_the_panels_edit_to_disk(tk_app, full_workspace):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.hidden_block_panel

    lot0_row = next(
        r for r in panel.tree.get_children() if int(panel.tree.item(r, "values")[0]) == 0
    )
    panel.tree.selection_set(lot0_row)
    app.update()
    panel.reward_combobox.set("12 Coins")
    panel.rate_spinbox.delete(0, "end")
    panel.rate_spinbox.insert(0, "5")
    panel._apply()
    app.update()

    app.save_data()
    app.update()

    data_dir = os.path.join(full_workspace, "bd~bd00.nx", "bd", "bd00", "data")
    with open(os.path.join(data_dir, "bd00_HiddenBlock.json"), "r", encoding="utf-8-sig") as f:
        hidden_block = json.load(f)["HiddenBlock"]

    lot0 = next(e for e in hidden_block if e["No"] == 0)
    assert lot0["Result"] == 12
    assert lot0["Rate"] == 5
