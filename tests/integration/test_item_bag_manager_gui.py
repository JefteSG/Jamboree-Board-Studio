"""GUI tests for ItemBagDataManager and the refactored ItemBagEditor.

Before this, ItemBagEditor kept no live model of its own — its listbox
display *was* the state, and save_items() reconstructed entries by
parsing that display text back out. That made it unsafe to ever add a
second view over the same data (an edit there would be silently lost on
save, since the legacy widget's save always re-derives from its own,
unrelated listbox). This refactor gives it a real ItemBagDataManager,
matching the listener pattern HiddenBlockDataManager/EventDataManager
already use, so a future board-vocabulary panel can share state safely.

These tests specifically exercise add/remove/randomize through the
manager (not just load/save, which were already covered before this
refactor) and prove a second registered listener actually gets notified
-- the entire point of introducing the manager in the first place.
"""

import json
import os


def _listbox_items(listbox):
    return [listbox.get(i) for i in range(listbox.size())]


def test_add_item_updates_both_the_manager_and_the_listbox(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    editor = first_tab.item_bag

    editor.entry.set("GoldPipe")
    editor.phase_combobox.set("Standard")
    editor.unique_var.set(1)
    editor.add_item()
    app.update()

    manager_entries = first_tab.item_bag_data_manager.get_item_bag_data(first_tab.map_name)
    assert any(e["Item"] == "GoldPipe" and e["Phase"] == 0 and e["Unique"] == 1 for e in manager_entries)
    assert "GoldPipe - Unique" in _listbox_items(editor.phase_frames[0].listbox)


def test_remove_item_from_phase_1_works(tk_app):
    # Regression check for a fixed off-by-one (the original loop was
    # `for phase in range(3)` against a 2-phase dict -- harmless as long
    # as phase 0 or 1 had a selection, since it broke out early, but
    # would KeyError on self.phase_frames[2] if neither did. Exercising
    # phase 1 (index 1, the last real phase) specifically here.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    editor = first_tab.item_bag

    editor.entry.set("Kinoko")
    editor.phase_combobox.set("Standard (5 Last Turns)")
    editor.unique_var.set(0)
    editor.add_item()
    app.update()

    listbox = editor.phase_frames[1].listbox
    assert "Kinoko - Not Unique" in _listbox_items(listbox)
    index = _listbox_items(listbox).index("Kinoko - Not Unique")
    listbox.selection_set(index)

    editor.remove_item()
    app.update()

    assert "Kinoko - Not Unique" not in _listbox_items(listbox)
    manager_entries = first_tab.item_bag_data_manager.get_item_bag_data(first_tab.map_name)
    assert not any(e["Item"] == "Kinoko" and e["Phase"] == 1 for e in manager_entries)


def test_randomize_items_updates_the_manager(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    editor = first_tab.item_bag

    editor.randomize_items()
    app.update()

    manager_entries = first_tab.item_bag_data_manager.get_item_bag_data(first_tab.map_name)
    listbox_total = sum(editor.phase_frames[p].listbox.size() for p in range(2))
    assert len(manager_entries) == listbox_total
    assert listbox_total > 0


def test_a_second_registered_listener_gets_notified(tk_app):
    # The actual point of the manager: any future view registered on it
    # must be told when ItemBagEditor's own UI actions change the data,
    # without ItemBagEditor needing to know that view exists.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    editor = first_tab.item_bag

    class DummyListener:
        def __init__(self):
            self.refresh_count = 0

        def refresh_data(self):
            self.refresh_count += 1

    listener = DummyListener()
    first_tab.item_bag_data_manager.register_listener(listener)

    editor.entry.set("Stone")
    editor.phase_combobox.set("Standard")
    editor.unique_var.set(0)
    editor.add_item()
    app.update()

    assert listener.refresh_count >= 1


def test_save_persists_an_added_item_to_disk(tk_app, full_workspace):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    editor = first_tab.item_bag

    editor.entry.set("WarpBox")
    editor.phase_combobox.set("Standard")
    editor.unique_var.set(1)
    editor.add_item()
    app.update()

    app.save_data()
    app.update()

    data_dir = os.path.join(full_workspace, "bd~bd00.nx", "bd", "bd00", "data")
    with open(os.path.join(data_dir, "bd00_ItemBag_Map01.json"), "r", encoding="utf-8-sig") as f:
        item_bag = json.load(f)["Map01"]

    assert any(e["Item"] == "WarpBox" and e["Phase"] == 0 and e["Unique"] == 1 for e in item_bag)
    # "Stone" was added deterministically by
    # test_a_second_registered_listener_gets_notified, which runs earlier
    # in this module-scoped session -- it must still be there, confirming
    # this was an addition, not a silent replacement. (The original
    # Kinoko/Stone fixture entries aren't a safe thing to assert on here:
    # test_randomize_items_updates_the_manager runs before this test too,
    # and randomize_items() replaces the whole list with a random
    # selection, so whether the *fixture's* Kinoko survives is down to
    # chance, not this test's own behavior.)
    assert any(e["Item"] == "Stone" for e in item_bag)
