"""GUI regression tests for wiring editor_modules/{hidden_block,item_bag,item_mass}.py
onto the new jamboree_board_studio.core.items adapters.

Those three modules' load_*/save_* functions used to do their own ad hoc
JSON file IO; they now delegate to core.items' parse_*/serialize_*
functions while keeping their exact original signatures and return
shapes, so the Tkinter widget classes (HiddenBlockEditor, ItemBagEditor,
ItemMassEditor) needed no changes at all. These tests exist to prove
that swap didn't change real, observable behavior: data loaded through
the actual widgets still shows correctly, and a save still round-trips
through the real widgets and back out to the same files on disk.
"""

import json
import os


def _listbox_items(listbox):
    return [listbox.get(i) for i in range(listbox.size())]


def test_hidden_block_loads_into_the_real_widget(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])

    lot0_items = _listbox_items(first_tab.hidden_block.lots[0]["listbox"])
    lot1_items = _listbox_items(first_tab.hidden_block.lots[1]["listbox"])

    assert any("1 Star" in text for text in lot0_items)
    assert any("Rate: 10" in text for text in lot0_items)
    assert any("5 Coins" in text for text in lot1_items)
    assert any("Rate: 20" in text for text in lot1_items)


def test_item_bag_loads_into_the_real_widget(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])

    phase0_items = _listbox_items(first_tab.item_bag.phase_frames[0].listbox)
    phase1_items = _listbox_items(first_tab.item_bag.phase_frames[1].listbox)

    assert "Kinoko - Unique" in phase0_items
    assert "Stone - Not Unique" in phase1_items


def test_item_mass_loads_into_the_real_widget(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])

    lot0_items = _listbox_items(first_tab.item_mass.lots[0]["listbox"])
    lot1_items = _listbox_items(first_tab.item_mass.lots[1]["listbox"])

    assert "Kinoko" in lot0_items
    assert "GoldPipe" in lot1_items


def test_save_round_trips_hidden_block_item_bag_and_item_mass_to_disk(
    tk_app, full_workspace
):
    app = tk_app

    app.save_data()
    app.update()

    data_dir = os.path.join(full_workspace, "bd~bd00.nx", "bd", "bd00", "data")

    with open(os.path.join(data_dir, "bd00_HiddenBlock.json"), "r", encoding="utf-8-sig") as f:
        hidden_block = json.load(f)["HiddenBlock"]
    assert {(e["No"], e["Result"], e["Rate"]) for e in hidden_block} >= {
        (0, -1, 10),
        (1, 5, 20),
    }

    with open(
        os.path.join(data_dir, "bd00_ItemBag_Map01.json"), "r", encoding="utf-8-sig"
    ) as f:
        item_bag = json.load(f)["Map01"]
    assert {(e["Item"], e["Phase"], e["Unique"]) for e in item_bag} == {
        ("Kinoko", 0, 1),
        ("Stone", 1, 0),
    }

    with open(
        os.path.join(data_dir, "bd00_ItemMass_Map01.json"), "r", encoding="utf-8-sig"
    ) as f:
        item_mass = json.load(f)["Map01"]
    assert {(e["Item"], e["No"]) for e in item_mass} == {("Kinoko", 0), ("GoldPipe", 1)}
