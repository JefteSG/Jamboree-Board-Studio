"""Shared fixtures for GUI integration tests.

These tests exercise the real Tkinter editor (``editor.py``), not just
the domain layer, so they need a synthetic on-disk workspace with valid
data for every file type ``editor.py``'s ``load_data()`` checks, plus
non-empty Lucky/Unlucky/Koopa event rates — otherwise
``JamboreeMapEditor.save_data()`` refuses to save anything at all (a
pre-existing, unrelated safety gate:
``EventDataManager.get_events_status()``). Without that, a save-path
assertion here would fail for a reason that has nothing to do with what
the test is actually checking.
"""

import json
import os

import pytest


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as f:
        json.dump(data, f)


def _bd00_path(workspace_path, name):
    return os.path.join(workspace_path, "bd~bd00.nx", "bd", "bd00", "data", name)


def _bdxx_path(workspace_path, i, name):
    return os.path.join(
        workspace_path, f"bd~bd{i:02d}.nx", "bd", f"bd{i:02d}", "data", name
    )


def _sample_map_node(offset=0):
    types = ["Lucky", "Unlucky", "Chance", "Item", "Plus", "Minus"]
    return [
        {"NodeNo": n, "MassAttr": types[n % len(types)], "NpcNodeNo0": -1}
        for n in range(offset, offset + 6)
    ]


def _sample_map_path(offset=0):
    # Simple chain 0->1->2->3->4->5, plus one branch (1->3) so the fixture
    # exercises multi-segment Path entries too.
    entries = []
    chain = list(range(offset, offset + 6))
    for idx in range(len(chain) - 1):
        src, tgt = chain[idx], chain[idx + 1]
        entries.append(
            {
                "NodeNo": src,
                "Path": [
                    {
                        "NodeNo": tgt,
                        "Bezier": [
                            {
                                "Position0X": float(idx),
                                "Position0Z": 0.0,
                                "Position1X": float(idx + 1),
                                "Position1Z": 0.0,
                            }
                        ],
                    }
                ],
            }
        )
    entries[1]["Path"].append(
        {
            "NodeNo": chain[3],
            "Bezier": [
                {
                    "Position0X": 1.0,
                    "Position0Z": 0.0,
                    "Position1X": 3.0,
                    "Position1Z": 1.0,
                }
            ],
        }
    )
    return entries


def _full_rate_entry(result):
    return {"Rate0": 100, "Rate1": 100, "Rate2": 100, "Rate3": 100, "Result": result}


def build_full_workspace(workspace_path: str) -> None:
    """Write a complete, valid, synthetic 7-board workspace to workspace_path.

    No real Super Mario Party Jamboree dump is bundled with (or
    available to) this project — see README/docs/research — so this is
    built only from field names/shapes already confirmed by the existing
    parsers, the same way the unit-test fixtures in
    ``tests/core/board/`` are.
    """
    for i in range(1, 8):
        xx = f"Map{i:02d}"
        _write_json(_bd00_path(workspace_path, f"bd00_ItemBag_{xx}.json"), {xx: []})
        _write_json(_bd00_path(workspace_path, f"bd00_ItemMass_{xx}.json"), {xx: []})
        _write_json(_bd00_path(workspace_path, f"bd00_ItemShop_{xx}.json"), {xx: []})
        _write_json(
            _bd00_path(workspace_path, f"bd00_LuckyMass_{xx}.json"),
            {xx: [_full_rate_entry("7Coin")]},
        )
        _write_json(
            _bd00_path(workspace_path, f"bd00_UnluckyMass_{xx}.json"),
            {xx: [_full_rate_entry("Rob3Coin")]},
        )
        _write_json(
            _bdxx_path(workspace_path, i, f"bd{i:02d}_MapNode.json"),
            {"MapNode": _sample_map_node()},
        )
        _write_json(
            _bdxx_path(workspace_path, i, f"bd{i:02d}_MapPath.json"),
            {"MapPath": _sample_map_path()},
        )

    _write_json(
        _bd00_path(workspace_path, "bd00_KoopaMass_Map00.json"),
        {"Map00": [_full_rate_entry("Rob10Coin")]},
    )
    _write_json(
        _bd00_path(workspace_path, "bd00_KoopaMass_Map06.json"),
        {"Map06": [_full_rate_entry("Rob10Coin")]},
    )
    _write_json(_bd00_path(workspace_path, "bd00_HiddenBlock.json"), {"HiddenBlock": []})
    _write_json(
        _bd00_path(workspace_path, "bd00_PlayerMove.json"),
        {"PlayerMove": [{"MaxSpeed": 10, "CircuitSpeed": 10, "MachSpeed": 10}]},
    )


@pytest.fixture(scope="module")
def full_workspace(tmp_path_factory):
    workspace_path = str(tmp_path_factory.mktemp("workspace"))
    build_full_workspace(workspace_path)
    return workspace_path


@pytest.fixture(scope="module")
def tk_app(full_workspace):
    """A live ``JamboreeMapEditor`` instance over a synthetic workspace.

    Module-scoped deliberately: creating and destroying multiple
    ``tk.Tk()`` roots in sequence within one process is fragile (it hung
    a test run outright during development, on the second root created).
    One shared app per test module, mutated across tests in file-definition
    order (pytest's default), matches the single-root pattern already
    proven stable in manual verification and avoids that.

    Skips (doesn't fail) when Tkinter isn't importable, or when a Tk
    root can't be created (no display, e.g. Linux/macOS without Xvfb) —
    these tests document/protect real GUI behavior when a display *is*
    available (Windows, where Tk doesn't need one; or Linux/macOS dev
    with Xvfb), and must not break a plain ``pytest tests/`` for anyone
    without one.
    """
    tkinter = pytest.importorskip("tkinter")

    try:
        probe = tkinter.Tk()
        probe.destroy()
    except tkinter.TclError as error:
        pytest.skip(f"No usable Tk display available: {error}")

    import editor as editor_module

    # Avoid blocking on modal dialogs (messagebox.* opens a real modal
    # event loop via wait_window) since nothing will click them here.
    editor_module.messagebox.showinfo = lambda *a, **k: None
    editor_module.messagebox.showerror = lambda *a, **k: None
    editor_module.messagebox.showwarning = lambda *a, **k: None

    from editor import JamboreeMapEditor

    app = JamboreeMapEditor(full_workspace)
    for _ in range(5):
        app.update()

    yield app

    app.destroy()
