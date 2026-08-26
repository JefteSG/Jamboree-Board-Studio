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


def test_selecting_a_connection_shows_it_editable_and_clears_space_selection(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    board = first_tab.board

    # Select a space first, so we can verify selecting a connection
    # afterwards actually clears the previous space selection.
    first_tab._on_board_space_selected(board.get_space("0"))
    app.update()

    connection = board.connections[0]
    first_tab._on_board_connection_selected(connection)
    app.update()

    assert first_tab.inspector_panel.space is None
    assert (
        connection.source in first_tab.inspector_panel.id_value["text"]
        and connection.target in first_tab.inspector_panel.id_value["text"]
    )
    # The space-type Apply button stays disabled -- a connection isn't a
    # space -- but retargeting/deleting the connection itself is enabled.
    assert str(first_tab.inspector_panel.apply_button["state"]) == "disabled"
    assert str(first_tab.inspector_panel.retarget_button["state"]) == "normal"
    assert str(first_tab.inspector_panel.delete_connection_button["state"]) == "normal"
    assert first_tab.board_canvas.selected_connection_key == (
        connection.source,
        connection.target,
    )
    assert first_tab.board_canvas.selected_space_id is None
    assert first_tab.space_list.tree.selection() == ()


def test_retargeting_a_connection_updates_data_and_canvas(tk_app):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    board = first_tab.board

    connection = next(c for c in board.connections if c.source == "0")
    old_target = connection.target
    new_target = next(s.id for s in board.spaces if s.id not in (connection.source, old_target))

    first_tab._on_board_connection_selected(connection)
    app.update()
    first_tab.inspector_panel.target_combobox.set(new_target)
    first_tab.inspector_panel._retarget()
    app.update()

    assert connection.target == new_target
    assert connection.game_data["NodeNo"] == int(new_target)
    # Redrawn at the new endpoint, not left pointing at the old one.
    assert any(
        entry["connection"] is connection for entry in first_tab.board_canvas._arrow_patches
    )


def test_deleting_a_connection_removes_it_from_board_and_raw_data(tk_app, monkeypatch):
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    board = first_tab.board

    # Node "1" has two outgoing edges in the fixture (to "2" and a branch
    # to "3") -- deleting one must not disturb the other.
    connection = next(c for c in board.connections if c.source == "1" and c.target == "3")
    surviving = next(c for c in board.connections if c.source == "1" and c.target == "2")

    from jamboree_board_studio.ui.widgets import inspector_panel as inspector_panel_module

    monkeypatch.setattr(inspector_panel_module.messagebox, "askyesno", lambda *a, **k: True)

    first_tab._on_board_connection_selected(connection)
    app.update()
    first_tab.inspector_panel._delete_connection()
    app.update()

    assert connection not in board.connections
    assert surviving in board.connections
    raw_path_entry = next(e for e in first_tab.map_layout_data["MapPath"] if e["NodeNo"] == 1)
    assert connection.game_data not in raw_path_entry["Path"]
    assert surviving.game_data in raw_path_entry["Path"]
    assert not any(entry["connection"] is connection for entry in first_tab.board_canvas._arrow_patches)


def test_save_persists_connection_retarget_to_disk(tk_app, full_workspace):
    # Note: this file's tk_app/full_workspace fixtures are module-scoped
    # (see conftest.py) -- every test in this module shares one live board
    # and one on-disk workspace, mutated incrementally in definition order.
    # By this point test_deleting_a_connection_removes_it_from_board_and_raw_data
    # has already removed node "1"'s branch to "3"; this test only checks
    # that a retarget survives a save, not any particular prior state.
    app = tk_app
    first_tab = app.notebook.nametowidget(app.notebook.tabs()[0])
    board = first_tab.board

    retargeted = next(c for c in board.connections if c.source == "0")
    new_target = next(
        s.id for s in board.spaces if s.id not in (retargeted.source, retargeted.target)
    )

    first_tab._on_board_connection_selected(retargeted)
    app.update()
    first_tab.inspector_panel.target_combobox.set(new_target)
    first_tab.inspector_panel._retarget()
    app.update()

    app.save_data()
    app.update()

    saved_path = json.load(
        open(
            os.path.join(
                full_workspace, "bd~bd01.nx", "bd", "bd01", "data", "bd01_MapPath.json"
            ),
            encoding="utf-8-sig",
        )
    )["MapPath"]
    entry_0 = next(e for e in saved_path if e["NodeNo"] == 0)
    assert entry_0["Path"][0]["NodeNo"] == int(new_target)


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
