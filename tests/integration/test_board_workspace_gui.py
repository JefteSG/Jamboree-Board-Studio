"""GUI integration tests for the Board Workspace tab.

Exercises the real Tkinter editor end-to-end. This is what actually
caught a real bug during development: a ``<<TreeviewSelect>>``
event-queue race in ``space_list_panel.py`` where a boolean "suppress"
flag was cleared before Tk's *queued* selection event was delivered,
letting a programmatic selection re-trigger itself forever. No amount of
headless unit testing of the domain layer (``jamboree_board_studio.core``)
would have caught that — it's purely about Tk's own event-loop timing —
hence these tests exist alongside the domain-layer ones rather than
instead of them.

Needs a real Tk display; see ``tk_app`` in ``conftest.py`` for how that's
handled (skip, don't fail, when unavailable).
"""

import json
import os


def test_board_workspace_tab_present_for_every_map(tk_app):
    app = tk_app
    tabs = app.notebook.tabs()
    assert len(tabs) == 7

    for tab_id in tabs:
        map_tab = app.notebook.nametowidget(tab_id)
        sub_tab_labels = [
            map_tab.main_notebook.tab(t, "text") for t in map_tab.main_notebook.tabs()
        ]
        assert "Board Workspace (Preview)" in sub_tab_labels
        assert "Map Layout" in sub_tab_labels  # original tab must still exist


def test_board_workspace_loads_spaces_and_connections(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])

    board = first_tab.board
    assert board is not None
    assert len(board.spaces) == 6
    assert len(board.connections) > 0
    assert any(space.visual_position is not None for space in board.spaces)
    assert len(first_tab.space_list.tree.get_children()) == len(board.spaces)


def test_selecting_a_space_updates_inspector_and_canvas(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    board = first_tab.board

    target_space = board.get_space("0")
    first_tab._on_board_space_selected(target_space)
    app.update()

    assert first_tab.inspector_panel.space is target_space
    assert first_tab.board_canvas.selected_space_id == "0"


def test_selecting_via_the_space_list_stays_in_sync_and_does_not_hang(tk_app):
    # Regression test for the <<TreeviewSelect>> race described in the
    # module docstring: this used to hang indefinitely the first time a
    # selection was made through the tree widget.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    board = first_tab.board

    other_space = board.get_space("2")
    other_row = first_tab.space_list._row_by_space_id["2"]
    first_tab.space_list.tree.selection_set(other_row)
    app.update()

    assert first_tab.inspector_panel.space is other_space
    assert first_tab.board_canvas.selected_space_id == "2"


def test_applying_an_edit_updates_canvas_list_and_underlying_data(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    board = first_tab.board

    target_space = board.get_space("0")  # type "Lucky" in the fixture: editable
    first_tab._on_board_space_selected(target_space)
    app.update()

    assert str(first_tab.inspector_panel.apply_button["state"]) == "normal"
    first_tab.inspector_panel.type_combobox.set("Chance")
    first_tab.inspector_panel._apply()
    app.update()

    assert target_space.type == "Chance"
    assert target_space.game_data["MassAttr"] == "Chance"

    row_id = first_tab.space_list._row_by_space_id["0"]
    assert first_tab.space_list.tree.item(row_id, "values") == ("Chance",)


def test_save_persists_board_workspace_edits_to_disk(tk_app, full_workspace):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    board = first_tab.board

    target_space = board.get_space("0")
    first_tab._on_board_space_selected(target_space)
    app.update()
    first_tab.inspector_panel.type_combobox.set("Chance")
    first_tab.inspector_panel._apply()
    app.update()

    app.save_data()
    app.update()

    node_file = os.path.join(
        full_workspace, "bd~bd01.nx", "bd", "bd01", "data", "bd01_MapNode.json"
    )
    with open(node_file, "r", encoding="utf-8-sig") as f:
        saved = json.load(f)
    node0 = next(n for n in saved["MapNode"] if n["NodeNo"] == 0)
    assert node0["MassAttr"] == "Chance"

    # Single source of truth: the legacy Map Layout tab's own in-memory
    # data must reflect the same edit, since it's the same dict object
    # (see build_board_from_raw / core/board/parser.py).
    legacy_node0 = next(
        n for n in first_tab.map_layout_data["MapNode"] if n["NodeNo"] == 0
    )
    assert legacy_node0["MassAttr"] == "Chance"


def test_unmodified_app_still_starts_and_saves(tk_app):
    # Baseline regression check: the original functionality (7 map tabs,
    # shop/item/event editors, save) must keep working exactly as before
    # all the Board Workspace additions, independent of that new tab.
    app = tk_app
    assert str(app.save_button["state"]) == "normal"
    assert str(app.randomize_button["state"]) == "normal"

    app.save_data()  # must not raise
    app.update()
