"""GUI regression tests for wiring editor_modules/events.py's
load_event_mapdata/save_event_mapdata onto jamboree_board_studio.core.events.

Those two functions used to do their own ad hoc JSON file IO (including
the KoopaMass -> shared "Map00" file remapping); they now delegate to
core.events' parse_events/serialize_events while keeping their exact
original signatures and return shapes, so EventDataManager/EventEditor
(the live cross-map sync + rate-sum validation gate, both intentionally
left untouched) needed no changes.

This is the riskiest of the four adapter-wiring passes so far because
EventDataManager.get_events_status() gates the *entire app's* save, and
KoopaMass's shared-file behavior is exactly the kind of cross-cutting
detail a refactor could quietly break — so these tests check both
specifically, not just "did it start."
"""

import json
import os


def _listbox_items(listbox):
    return [listbox.get(i) for i in range(listbox.size())]


def test_lucky_and_unlucky_events_load_into_the_real_widget(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])

    lucky_items = _listbox_items(first_tab.lucky_events.listbox)
    unlucky_items = _listbox_items(first_tab.unlucky_events.listbox)

    assert any("7Coin" in text for text in lucky_items)
    assert any("Rob3Coin" in text for text in unlucky_items)


def test_koopa_mass_loads_the_same_shared_data_on_every_non_map06_tab(tk_app):
    app = tk_app

    for tab_id in app.notebook.tabs()[:5]:  # Map01..Map05, all non-Map06
        map_tab = app.notebook.nametowidget(tab_id)
        koopa_items = _listbox_items(map_tab.koopa_mass_events.listbox)
        assert any("Rob10Coin" in text for text in koopa_items)


def test_koopa_mass_on_map06_uses_its_own_data_not_the_shared_file(tk_app):
    app = tk_app
    map06_tab = app.notebook.nametowidget(app.notebook.tabs()[5])  # Map06

    koopa_items = _listbox_items(map06_tab.koopa_mass_events.listbox)

    assert any("Get1000Coin" in text for text in koopa_items)
    assert not any("Rob10Coin" in text for text in koopa_items)


def test_events_rate_status_gate_allows_save_with_the_fixtures_full_rates(tk_app):
    # EventDataManager.get_events_status() blocks the *entire* app's save
    # if any registered event pool has a rate column summing to zero.
    # The fixture uses full (100/100/100/100) rates for exactly this
    # reason: this test would silently no-op save_data() otherwise,
    # masking real regressions in every other save-path test.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])

    assert first_tab.event_data_manager.get_events_status() is True


def test_save_round_trips_lucky_unlucky_and_shared_koopa_mass_to_disk(
    tk_app, full_workspace
):
    app = tk_app

    app.save_data()
    app.update()

    data_dir = os.path.join(full_workspace, "bd~bd00.nx", "bd", "bd00", "data")

    with open(
        os.path.join(data_dir, "bd00_LuckyMass_Map01.json"), "r", encoding="utf-8-sig"
    ) as f:
        lucky = json.load(f)["Map01"]
    assert any(e["Result"] == "7Coin" for e in lucky)

    with open(
        os.path.join(data_dir, "bd00_KoopaMass_Map00.json"), "r", encoding="utf-8-sig"
    ) as f:
        koopa_shared = json.load(f)["Map00"]
    assert any(e["Result"] == "Rob10Coin" for e in koopa_shared)

    with open(
        os.path.join(data_dir, "bd00_KoopaMass_Map06.json"), "r", encoding="utf-8-sig"
    ) as f:
        koopa_map06 = json.load(f)["Map06"]
    assert any(e["Result"] == "Get1000Coin" for e in koopa_map06)
