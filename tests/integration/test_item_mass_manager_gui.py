"""GUI tests for ItemMassDataManager and the refactored ItemMassEditor.

Same motivation as test_item_bag_manager_gui.py: before this refactor,
ItemMassEditor kept no live model of its own -- each lot's listbox
display *was* the state, and save_items() reconstructed entries by
reading that display text back out. That made it unsafe to ever add a
second view over the same data. This gives it a real
ItemMassDataManager, matching the listener pattern every other
manager in this codebase already uses.

These tests exercise add/remove/randomize through the manager and prove
a second registered listener actually gets notified -- the entire point
of introducing the manager in the first place.
"""

import json
import os


def _listbox_items(listbox):
    return [listbox.get(i) for i in range(listbox.size())]


def test_add_item_updates_both_the_manager_and_the_listbox(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    editor = first_tab.item_mass

    editor.lots[0]["entry"].set("GoldPipe")
    editor.add_item(0, editor.lots[0]["entry"])
    app.update()

    manager_entries = first_tab.item_mass_data_manager.get_item_mass_data(first_tab.map_name)
    assert any(e["Item"] == "GoldPipe" and e["No"] == 0 for e in manager_entries)
    assert "GoldPipe" in _listbox_items(editor.lots[0]["listbox"])


def test_remove_item_from_a_specific_lot_works(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    editor = first_tab.item_mass

    editor.lots[3]["entry"].set("Kinoko")
    editor.add_item(3, editor.lots[3]["entry"])
    app.update()

    listbox = editor.lots[3]["listbox"]
    assert "Kinoko" in _listbox_items(listbox)
    index = _listbox_items(listbox).index("Kinoko")
    listbox.selection_set(index)

    editor.remove_item(3)
    app.update()

    assert "Kinoko" not in _listbox_items(listbox)
    manager_entries = first_tab.item_mass_data_manager.get_item_mass_data(first_tab.map_name)
    assert not any(e["Item"] == "Kinoko" and e["No"] == 3 for e in manager_entries)


def test_randomize_items_updates_the_manager(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    editor = first_tab.item_mass

    editor.randomize_items(probability=1.0)
    app.update()

    manager_entries = first_tab.item_mass_data_manager.get_item_mass_data(first_tab.map_name)
    listbox_total = sum(widgets["listbox"].size() for widgets in editor.lots.values())
    assert len(manager_entries) == listbox_total
    assert listbox_total > 0


def test_a_second_registered_listener_gets_notified(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    editor = first_tab.item_mass

    class DummyListener:
        def __init__(self):
            self.refresh_count = 0

        def refresh_data(self):
            self.refresh_count += 1

    listener = DummyListener()
    first_tab.item_mass_data_manager.register_listener(listener)

    editor.lots[0]["entry"].set("Stone")
    editor.add_item(0, editor.lots[0]["entry"])
    app.update()

    assert listener.refresh_count >= 1


def test_save_persists_an_added_item_to_disk(tk_app, full_workspace):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    editor = first_tab.item_mass

    editor.lots[1]["entry"].set("WarpBox")
    editor.add_item(1, editor.lots[1]["entry"])
    app.update()

    app.save_data()
    app.update()

    data_dir = os.path.join(full_workspace, "bd~bd00.nx", "bd", "bd00", "data")
    with open(os.path.join(data_dir, "bd00_ItemMass_Map01.json"), "r", encoding="utf-8-sig") as f:
        item_mass = json.load(f)["Map01"]

    assert any(e["Item"] == "WarpBox" and e["No"] == 1 for e in item_mass)
