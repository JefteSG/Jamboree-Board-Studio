"""Property inspector for a selected BoardSpace.

Shows known fields (id, editable type) using plain board vocabulary, and
puts everything this project does not yet interpret behind an
"Advanced / Raw Game Data" read-only view, per the project's UX goal of
not exposing raw JSON as the primary interface.

Edits are written directly onto the selected ``BoardSpace``. Since
``BoardSpace.game_data`` is the *same* dict object already referenced by
the workspace data the legacy editor loaded (see
``jamboree_board_studio.core.board.parser`` / how this panel is wired in
``editor.py``), an edit here is visible to the existing "Save Map Data"
button with no extra syncing code — this project deliberately avoids a
second, parallel copy of edit state.
"""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk

from jamboree_board_studio.legacy.editor_modules.map_layout import mass_attr_list
from jamboree_board_studio.core.board.models import Board, BoardConnection, BoardSpace

# Mirrors jamboree_board_studio.legacy.editor_modules.map_layout.MapLayoutEditor.on_click's own safety
# rule: on Map07, NodeNo 59-66 are rewritten by the game itself (Wiggler
# path) and must stay read-only. Duplicated here (rather than imported)
# because it is a small, UI-level safety gate, not domain data; see
# docs/research/board-format.md for why this special case exists.
_WIGGLER_RESERVED_MAP = "Map07"
_WIGGLER_RESERVED_NODE_RANGE = range(59, 67)


def _is_reserved_id(board_id: str, node_id: str) -> bool:
    if board_id != _WIGGLER_RESERVED_MAP:
        return False
    try:
        node_no = int(node_id)
    except ValueError:
        return False
    return node_no in _WIGGLER_RESERVED_NODE_RANGE


def _is_reserved(board_id: str, space: BoardSpace) -> bool:
    return _is_reserved_id(board_id, space.id)


class InspectorPanel(ttk.Frame):
    def __init__(self, parent, on_apply=None, on_retarget_connection=None, on_delete_connection=None):
        super().__init__(parent)
        self.on_apply = on_apply
        self.on_retarget_connection = on_retarget_connection
        self.on_delete_connection = on_delete_connection
        self.board_id: str | None = None
        self.board: Board | None = None
        self.space: BoardSpace | None = None
        self.connection: BoardConnection | None = None

        self.title_label = ttk.Label(self, text="No space selected", font=("Arial", 11, "bold"))
        self.title_label.pack(anchor="w", padx=8, pady=(8, 4))

        id_frame = ttk.Frame(self)
        id_frame.pack(fill="x", padx=8, pady=2)
        self.id_label = ttk.Label(id_frame, text="ID")
        self.id_label.pack(side="left")
        self.id_value = ttk.Label(id_frame, text="-")
        self.id_value.pack(side="right")

        type_frame = ttk.Frame(self)
        type_frame.pack(fill="x", padx=8, pady=2)
        ttk.Label(type_frame, text="Type").pack(side="left")
        self.type_combobox = ttk.Combobox(
            type_frame, values=list(mass_attr_list), state="disabled", width=18
        )
        self.type_combobox.pack(side="right")

        self.type_note = ttk.Label(self, text="", foreground="gray", wraplength=220)
        self.type_note.pack(anchor="w", padx=8, pady=(0, 4))

        self.apply_button = ttk.Button(
            self, text="Apply", command=self._apply, state="disabled"
        )
        self.apply_button.pack(fill="x", padx=8, pady=(4, 8))

        target_frame = ttk.Frame(self)
        target_frame.pack(fill="x", padx=8, pady=2)
        ttk.Label(target_frame, text="Target").pack(side="left")
        self.target_combobox = ttk.Combobox(target_frame, state="disabled", width=18)
        self.target_combobox.pack(side="right")

        self.retarget_button = ttk.Button(
            self, text="Change Target", command=self._retarget, state="disabled"
        )
        self.retarget_button.pack(fill="x", padx=8, pady=(4, 2))

        self.delete_connection_button = ttk.Button(
            self, text="Delete Connection", command=self._delete_connection, state="disabled"
        )
        self.delete_connection_button.pack(fill="x", padx=8, pady=(2, 8))

        advanced_frame = ttk.LabelFrame(self, text="Advanced / Raw Game Data")
        advanced_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.raw_text = tk.Text(
            advanced_frame, height=14, width=30, state="disabled", wrap="word"
        )
        self.raw_text.pack(fill="both", expand=True, padx=4, pady=4)

        self.clear()

    def set_board(self, board: Board) -> None:
        """Give the panel the current Board, so it can offer valid connection targets."""
        self.board = board

    def clear(self) -> None:
        self.space = None
        self.connection = None
        self.title_label.config(text="Nothing selected")
        self.id_label.config(text="ID")
        self.id_value.config(text="-")
        self.type_combobox.config(state="disabled")
        self.type_combobox.set("")
        self.type_note.config(text="")
        self.apply_button.config(state="disabled")
        self.target_combobox.config(state="disabled", values=())
        self.target_combobox.set("")
        self.retarget_button.config(state="disabled")
        self.delete_connection_button.config(state="disabled")
        self._set_raw_text("")

    def show_space(self, board_id: str, space: BoardSpace) -> None:
        self.board_id = board_id
        self.space = space
        self.connection = None
        self.target_combobox.config(state="disabled", values=())
        self.target_combobox.set("")
        self.retarget_button.config(state="disabled")
        self.delete_connection_button.config(state="disabled")
        self.title_label.config(text=f"Space #{space.id}")
        self.id_label.config(text="ID")
        self.id_value.config(text=space.id)

        reserved = _is_reserved(board_id, space)
        editable = (not reserved) and space.type in mass_attr_list

        self.type_combobox.set(space.type)
        if editable:
            self.type_combobox.config(state="readonly")
            self.type_note.config(text="")
            self.apply_button.config(state="normal")
        else:
            self.type_combobox.config(state="disabled")
            self.apply_button.config(state="disabled")
            if reserved:
                self.type_note.config(
                    text=(
                        f"Space #{space.id} is rewritten by the game itself "
                        "(Wiggler path) and can't be edited."
                    )
                )
            elif space.type:
                self.type_note.config(
                    text=f"Type '{space.type}' is not confirmed safe to edit yet."
                )
            else:
                self.type_note.config(text="Type is unknown/empty for this space.")

        self._set_raw_text(json.dumps(space.game_data, indent=2, ensure_ascii=False))

    def show_connection(self, board_id: str, connection: BoardConnection) -> None:
        """Show a selected path/connection: retarget or delete it.

        What's still *not* supported: changing the curve itself (the
        ``Bezier`` control points) — see docs/research/board-format.md,
        the meaning of those fields beyond "some kind of 3D point" isn't
        confirmed yet, so this project doesn't synthesize new curve
        geometry. Retargeting reuses the existing ``Bezier`` unchanged
        (the curve will visually still bend toward the *old* target's
        position — a known, acceptable limitation, not a bug), and
        deleting just removes the edge outright. Both are safe because
        neither invents unconfirmed data.
        """
        self.board_id = board_id
        self.space = None  # not a space: _apply() must stay a no-op
        self.connection = connection
        self.title_label.config(text=f"Path #{connection.source} -> #{connection.target}")
        self.id_label.config(text="Source -> Target")
        self.id_value.config(text=f"{connection.source} -> {connection.target}")

        self.type_combobox.config(state="disabled")
        self.type_combobox.set("")
        self.apply_button.config(state="disabled")

        reserved = _is_reserved_id(board_id, connection.source)
        other_ids = sorted(
            (s.id for s in (self.board.spaces if self.board else []) if s.id != connection.source),
            key=lambda i: (0, int(i)) if i.isdigit() else (1, i),
        )

        if reserved:
            self.type_note.config(
                text=(
                    f"Path from #{connection.source} is rewritten by the game itself "
                    "(Wiggler path) and can't be edited."
                )
            )
            self.target_combobox.config(state="disabled", values=())
            self.retarget_button.config(state="disabled")
            self.delete_connection_button.config(state="disabled")
        else:
            self.type_note.config(text="Curve shape stays as-is; only its endpoint changes.")
            self.target_combobox.config(state="readonly", values=other_ids)
            self.target_combobox.set(connection.target)
            self.retarget_button.config(state="normal")
            self.delete_connection_button.config(state="normal")

        self._set_raw_text(json.dumps(connection.game_data, indent=2, ensure_ascii=False))

    def _set_raw_text(self, text: str) -> None:
        self.raw_text.config(state="normal")
        self.raw_text.delete("1.0", tk.END)
        self.raw_text.insert("1.0", text)
        self.raw_text.config(state="disabled")

    def _apply(self) -> None:
        if not self.space:
            return
        new_type = self.type_combobox.get()
        if new_type not in mass_attr_list:
            return
        self.space.type = new_type
        self.space.game_data["MassAttr"] = new_type
        self._set_raw_text(json.dumps(self.space.game_data, indent=2, ensure_ascii=False))
        if self.on_apply:
            self.on_apply(self.space)

    def _retarget(self) -> None:
        if not self.connection:
            return
        new_target = self.target_combobox.get()
        if not new_target or new_target == self.connection.target:
            return
        self.connection.target = new_target
        self.connection.game_data["NodeNo"] = int(new_target) if new_target.isdigit() else new_target
        self._set_raw_text(json.dumps(self.connection.game_data, indent=2, ensure_ascii=False))
        self.title_label.config(text=f"Path #{self.connection.source} -> #{self.connection.target}")
        self.id_value.config(text=f"{self.connection.source} -> {self.connection.target}")
        if self.on_retarget_connection:
            self.on_retarget_connection(self.connection)

    def _delete_connection(self) -> None:
        if not self.connection:
            return
        if not messagebox.askyesno(
            "Delete Connection",
            f"Delete the path from #{self.connection.source} to #{self.connection.target}?\n"
            "This can't be undone except by reloading the workspace without saving.",
        ):
            return
        connection = self.connection
        self.clear()
        if self.on_delete_connection:
            self.on_delete_connection(connection)
