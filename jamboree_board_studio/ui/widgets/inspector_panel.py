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
from tkinter import ttk

from editor_modules.map_layout import mass_attr_list
from jamboree_board_studio.core.board.models import BoardConnection, BoardSpace

# Mirrors editor_modules.map_layout.MapLayoutEditor.on_click's own safety
# rule: on Map07, NodeNo 59-66 are rewritten by the game itself (Wiggler
# path) and must stay read-only. Duplicated here (rather than imported)
# because it is a small, UI-level safety gate, not domain data; see
# docs/research/board-format.md for why this special case exists.
_WIGGLER_RESERVED_MAP = "Map07"
_WIGGLER_RESERVED_NODE_RANGE = range(59, 67)


def _is_reserved(board_id: str, space: BoardSpace) -> bool:
    if board_id != _WIGGLER_RESERVED_MAP:
        return False
    try:
        node_no = int(space.id)
    except ValueError:
        return False
    return node_no in _WIGGLER_RESERVED_NODE_RANGE


class InspectorPanel(ttk.Frame):
    def __init__(self, parent, on_apply=None):
        super().__init__(parent)
        self.on_apply = on_apply
        self.board_id: str | None = None
        self.space: BoardSpace | None = None

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

        advanced_frame = ttk.LabelFrame(self, text="Advanced / Raw Game Data")
        advanced_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.raw_text = tk.Text(
            advanced_frame, height=14, width=30, state="disabled", wrap="word"
        )
        self.raw_text.pack(fill="both", expand=True, padx=4, pady=4)

        self.clear()

    def clear(self) -> None:
        self.space = None
        self.title_label.config(text="Nothing selected")
        self.id_label.config(text="ID")
        self.id_value.config(text="-")
        self.type_combobox.config(state="disabled")
        self.type_combobox.set("")
        self.type_note.config(text="")
        self.apply_button.config(state="disabled")
        self._set_raw_text("")

    def show_space(self, board_id: str, space: BoardSpace) -> None:
        self.board_id = board_id
        self.space = space
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

    def show_connection(self, connection: BoardConnection) -> None:
        """Show a selected path/connection's known fields.

        Read-only: path editing isn't supported yet (see
        docs/research/board-format.md — Bezier segment meaning beyond
        the first control point is still unconfirmed), so this only
        displays what's known plus the raw segment data, the same way
        an unsupported space type is shown.
        """
        self.space = None  # not a space: _apply() must stay a no-op
        self.title_label.config(text=f"Path #{connection.source} -> #{connection.target}")
        self.id_label.config(text="Source -> Target")
        self.id_value.config(text=f"{connection.source} -> {connection.target}")

        self.type_combobox.config(state="disabled")
        self.type_combobox.set("")
        self.type_note.config(text="Connections aren't editable yet.")
        self.apply_button.config(state="disabled")

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
