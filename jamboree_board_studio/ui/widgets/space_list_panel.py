"""Sidebar list of a Board's spaces.

Lets the user pick a space by id/type from a list instead of having to
hit a (possibly small, overlapping) node on the canvas — the "Spaces"
part of the Board Workspace's left sidebar. Kept in sync bidirectionally
with ``BoardCanvas``'s own selection by the caller (see how both are
wired together in ``editor.py``): selecting a row here should highlight
the matching canvas node, and selecting a canvas node should highlight
the matching row here.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from jamboree_board_studio.core.board.models import Board, BoardSpace


def _sort_key(space: BoardSpace):
    try:
        return (0, int(space.id))
    except ValueError:
        return (1, space.id)


class SpaceListPanel(ttk.Frame):
    def __init__(self, parent, on_select=None):
        super().__init__(parent)
        self.on_select = on_select
        self.board: Board | None = None
        self._row_by_space_id: dict[str, str] = {}
        self._suppress_event = False

        ttk.Label(self, text="Spaces", font=("Arial", 10, "bold")).pack(
            anchor="w", padx=6, pady=(6, 2)
        )

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self.tree = ttk.Treeview(
            tree_frame, columns=("type",), show="tree headings", selectmode="browse"
        )
        self.tree.heading("#0", text="ID")
        self.tree.heading("type", text="Type")
        self.tree.column("#0", width=60, anchor="w", stretch=False)
        self.tree.column("type", width=110, anchor="w")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def load_board(self, board: Board) -> None:
        self.board = board
        self.tree.delete(*self.tree.get_children())
        self._row_by_space_id = {}

        for space in sorted(board.spaces, key=_sort_key):
            row_id = self.tree.insert("", "end", text=space.id, values=(space.type or "-",))
            self._row_by_space_id[space.id] = row_id

    def select_space(self, space_id: str | None) -> None:
        """Programmatically highlight a row without firing on_select.

        ``<<TreeviewSelect>>`` is queued by Tk rather than dispatched
        synchronously from ``selection_set``, so clearing the suppress
        flag right after this call (e.g. in a plain ``finally``) would
        clear it *before* the queued event is actually delivered — the
        handler would then see suppression already off and treat this
        programmatic change as a user click, re-selecting and re-queuing
        forever. Deferring the reset with ``after_idle`` keeps the flag
        set until the queued event has been processed.
        """
        self._suppress_event = True
        try:
            self.tree.selection_remove(self.tree.selection())
            row_id = self._row_by_space_id.get(space_id) if space_id else None
            if row_id:
                self.tree.selection_set(row_id)
                self.tree.see(row_id)
        finally:
            self.after_idle(self._clear_suppress)

    def _clear_suppress(self) -> None:
        self._suppress_event = False

    def refresh_space(self, space: BoardSpace) -> None:
        """Update a row's displayed values after an edit, without rebuilding the list."""
        row_id = self._row_by_space_id.get(space.id)
        if row_id:
            self.tree.item(row_id, values=(space.type or "-",))

    def _on_tree_select(self, event) -> None:
        if self._suppress_event or not self.board:
            return
        selection = self.tree.selection()
        if not selection:
            return
        space_id = self.tree.item(selection[0], "text")
        space = self.board.get_space(space_id)
        if space and self.on_select:
            self.on_select(space)
