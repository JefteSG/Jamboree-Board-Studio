"""GUI tests for the new "Events (Preview)" panel.

EventDataManager already had a fully live shared model before this
panel existed (unlike Item Bag/Item Mass/Item Shop before their own
managers were added) -- every EventEditor already reads/writes through
it. What this panel needed was for that sharing to actually be
bidirectional and pool-agnostic: before, only KoopaMass editors on
non-Map06 maps registered as listeners at all, and
sync_with_linked_maps() only ever broadcast a redraw for that same
case, so a Lucky/Unlucky edit never reached a second view. Both of
those were widened (see legacy/editor_modules/events.py) as part of
adding this panel. These tests prove the widening actually works: edits
flow in both directions for all three pools, KoopaMass still broadcasts
across maps, and the save-gate rate-status recalculation still happens
correctly when the edit comes from this panel instead of the legacy
widget.
"""

import json
import os


def _listbox_items(listbox):
    return [listbox.get(i) for i in range(listbox.size())]


def test_event_panel_loads_entries_from_all_three_pools(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.event_panel

    rows = panel.tree.get_children()
    values = [panel.tree.item(r, "values") for r in rows]

    assert any(v[0] == "Lucky" and v[5] == "7Coin" for v in values)
    assert any(v[0] == "Unlucky" and v[5] == "Rob3Coin" for v in values)
    assert any(v[0] == "KoopaMass" and v[5] == "Rob10Coin" for v in values)


def test_selecting_a_row_shows_it_in_the_inspector(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.event_panel

    row = next(r for r in panel.tree.get_children() if panel.tree.item(r, "values")[0] == "Lucky")
    panel.tree.selection_set(row)
    app.update()

    assert panel.selected is not None
    assert str(panel.apply_button["state"]) == "normal"
    data_type, entry = panel.selected
    assert data_type == "LuckyMass"
    assert panel.result_combobox.get() == entry["Result"]


def test_applying_an_edit_updates_the_legacy_widgets_listbox_too(tk_app):
    # The real point of the widened sharing: an edit made in the new
    # panel to a Lucky entry must show up in the *original* "Lucky" tab's
    # listbox without any extra glue code.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.event_panel

    row = next(
        r for r in panel.tree.get_children()
        if panel.tree.item(r, "values")[0] == "Lucky" and panel.tree.item(r, "values")[5] == "7Coin"
    )
    panel.tree.selection_set(row)
    app.update()

    panel.rate_spinboxes["Rate0"].delete(0, "end")
    panel.rate_spinboxes["Rate0"].insert(0, "55")
    panel.result_combobox.set("WarpBox")
    panel._apply()
    app.update()

    lucky_items = _listbox_items(first_tab.lucky_events.listbox)
    assert any("WarpBox" in text and "55" in text for text in lucky_items)
    assert not any("7Coin" in text for text in lucky_items)


def test_editing_from_the_legacy_widget_refreshes_the_panel(tk_app):
    # And the other direction: an add via the legacy "Unlucky" tab must
    # show up in the new panel's tree too.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    editor = first_tab.unlucky_events
    panel = first_tab.event_panel

    editor.entries["Rate0"].delete(0, "end")
    editor.entries["Rate0"].insert(0, "20")
    editor.entries["Rate1"].delete(0, "end")
    editor.entries["Rate1"].insert(0, "20")
    editor.entries["Rate2"].delete(0, "end")
    editor.entries["Rate2"].insert(0, "20")
    editor.entries["Rate3"].delete(0, "end")
    editor.entries["Rate3"].insert(0, "20")
    editor.result_combobox.set("GetStone")
    editor.add_event_entry()
    app.update()

    rows = panel.tree.get_children()
    values = [panel.tree.item(r, "values") for r in rows]
    assert any(v[0] == "Unlucky" and v[5] == "GetStone" and float(v[1]) == 20 for v in values)


def test_applying_a_koopamass_edit_broadcasts_to_every_other_map(tk_app):
    # KoopaMass is shared across every board except Map06 -- editing it
    # from Map01's new panel must propagate to every other non-Map06
    # map's tab too, exactly like the legacy widget's own edits do.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    other_tab = app.notebook.nametowidget(app.notebook.tabs()[3])  # Map04
    panel = first_tab.event_panel

    row = next(
        r for r in panel.tree.get_children()
        if panel.tree.item(r, "values")[0] == "KoopaMass"
        and panel.tree.item(r, "values")[5] == "Rob10Coin"
    )
    panel.tree.selection_set(row)
    app.update()

    panel.rate_spinboxes["Rate0"].delete(0, "end")
    panel.rate_spinboxes["Rate0"].insert(0, "33")
    panel.result_combobox.set("Shuffle")
    panel._apply()
    app.update()

    other_koopa_items = _listbox_items(other_tab.koopa_mass_events.listbox)
    assert any("Shuffle" in text and "33" in text for text in other_koopa_items)


def test_save_persists_the_panels_edit_to_disk(tk_app, full_workspace):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.event_panel

    row = next(
        r for r in panel.tree.get_children()
        if panel.tree.item(r, "values")[0] == "Unlucky" and panel.tree.item(r, "values")[5] == "Rob3Coin"
    )
    panel.tree.selection_set(row)
    app.update()
    panel.rate_spinboxes["Rate0"].delete(0, "end")
    panel.rate_spinboxes["Rate0"].insert(0, "90")
    panel.result_combobox.set("Rob5Coin")
    panel._apply()
    app.update()

    app.save_data()
    app.update()

    data_dir = os.path.join(full_workspace, "bd~bd00.nx", "bd", "bd00", "data")
    with open(os.path.join(data_dir, "bd00_UnluckyMass_Map01.json"), "r", encoding="utf-8-sig") as f:
        unlucky = json.load(f)["Map01"]

    assert any(e["Result"] == "Rob5Coin" and e["Rate0"] == 90.0 for e in unlucky)


def test_editing_from_the_panel_keeps_the_rate_status_gate_correct(tk_app):
    # get_events_status() blocks the *entire app's* save if any pool's
    # rates sum to zero. Zeroing out Lucky's only entry from the panel
    # must be reflected in the gate, exactly as if it had been done from
    # the legacy "Lucky" tab.
    #
    # This runs last in the module-scoped session on purpose: it leaves
    # Map01's LuckyMass status permanently False (nothing un-zeroes it),
    # which would otherwise make app.save_data() silently no-op for
    # every test after it -- exactly the flakiness bug already fixed
    # once in test_item_bag_manager_gui.py for a different reason (an
    # earlier test's side effect leaking into a later one).
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    panel = first_tab.event_panel

    assert first_tab.event_data_manager.get_events_status() is True

    row = next(r for r in panel.tree.get_children() if panel.tree.item(r, "values")[0] == "Lucky")
    panel.tree.selection_set(row)
    app.update()
    for rate_key in ("Rate0", "Rate1", "Rate2", "Rate3"):
        panel.rate_spinboxes[rate_key].delete(0, "end")
        panel.rate_spinboxes[rate_key].insert(0, "0")
    panel._apply()
    app.update()

    assert first_tab.event_data_manager.get_events_status() is False
