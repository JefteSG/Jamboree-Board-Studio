"""Hidden Block panel in board vocabulary (reward name + rate, not raw codes).

Hidden Block data is global (shared across every board, not per-map), and
the legacy ``HiddenBlockEditor`` widget already coordinates that sharing
through ``HiddenBlockDataManager`` (register as a listener, edit through
``update_hiddenblock_data``/``sync_with_linked_maps``, get notified via
``refresh_data()`` when anything — including this panel itself — changes
it). This panel plugs into that exact same protocol rather than keeping
a second copy of the data or its sync rules: it is another *view* over
the manager's state, not a second source of truth.

Scope for this first pass: view and edit existing entries (reward, rate)
in friendly names instead of raw ``Result`` codes. Add/remove entries
still happens on the original "Hidden Block" tab — this isn't a
replacement for it yet, just a first alternate view built on the same
model+adapter pattern as the Board Workspace tab.
"""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk

from jamboree_board_studio.core.items.hidden_block import HiddenBlockEntry
from jamboree_board_studio.legacy.editor_modules.hidden_block import (
    LOTS,
    get_lot_data_by_name,
    get_lot_name_by_data,
)

_LOT_NAMES = [lot["name"] for lot in LOTS]


def _entries_from_raw(raw_entries: list[dict]) -> list[HiddenBlockEntry]:
    """Same shape as core.items.hidden_block.parse_hidden_blocks, but over
    an already-loaded list (HiddenBlockDataManager's live data) instead of
    re-reading a file — mirrors core.board.parser.build_board_from_raw's
    reasoning: game_data stays the *same* dict object, so an edit here is
    the same edit the manager (and the legacy widget) already sees.
    """
    entries = []
    for entry in raw_entries:
        if not all(key in entry for key in ("No", "Result", "Rate")):
            continue
        entries.append(
            HiddenBlockEntry(
                lot=entry["No"], reward=entry["Result"], rate=entry["Rate"], game_data=entry
            )
        )
    return entries


class HiddenBlockPanel(ttk.Frame):
    def __init__(self, parent, map_name: str, data_manager):
        super().__init__(parent)
        self.map_name = map_name
        self.data_manager = data_manager
        self.entries: list[HiddenBlockEntry] = []
        self.selected_entry: HiddenBlockEntry | None = None

        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        table_frame = ttk.Frame(self)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ttk.Label(table_frame, text="Hidden Blocks", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(0, 4)
        )

        tree_container = ttk.Frame(table_frame)
        tree_container.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(
            tree_container,
            columns=("lot", "reward", "rate"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("lot", text="Lot")
        self.tree.heading("reward", text="Reward")
        self.tree.heading("rate", text="Rate")
        self.tree.column("lot", width=50, anchor="center", stretch=False)
        self.tree.column("reward", width=120, anchor="w")
        self.tree.column("rate", width=70, anchor="center", stretch=False)

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        note = ttk.Label(
            table_frame,
            text="Add/remove blocks on the “Hidden Block” tab; edit existing ones here.",
            foreground="gray",
            wraplength=260,
        )
        note.pack(anchor="w", pady=(4, 0))

        inspector_frame = ttk.Frame(self)
        inspector_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.title_label = ttk.Label(
            inspector_frame, text="Nothing selected", font=("Arial", 11, "bold")
        )
        self.title_label.pack(anchor="w", pady=(0, 8))

        reward_frame = ttk.Frame(inspector_frame)
        reward_frame.pack(fill="x", pady=2)
        ttk.Label(reward_frame, text="Reward").pack(side="left")
        self.reward_combobox = ttk.Combobox(
            reward_frame, values=_LOT_NAMES, state="disabled", width=14
        )
        self.reward_combobox.pack(side="right")

        rate_frame = ttk.Frame(inspector_frame)
        rate_frame.pack(fill="x", pady=2)
        ttk.Label(rate_frame, text="Rate").pack(side="left")
        self.rate_spinbox = ttk.Spinbox(rate_frame, from_=0, to=999, width=16, state="disabled")
        self.rate_spinbox.pack(side="right")

        self.apply_button = ttk.Button(
            inspector_frame, text="Apply", command=self._apply, state="disabled"
        )
        self.apply_button.pack(fill="x", pady=(8, 8))

        advanced_frame = ttk.LabelFrame(inspector_frame, text="Advanced / Raw Game Data")
        advanced_frame.pack(fill="both", expand=True)
        self.raw_text = tk.Text(
            advanced_frame, height=10, width=26, state="disabled", wrap="word"
        )
        self.raw_text.pack(fill="both", expand=True, padx=4, pady=4)

        self.data_manager.register_listener(self)
        self.refresh_data()

    def refresh_data(self) -> None:
        """Listener protocol expected by HiddenBlockDataManager.notify_listeners()."""
        raw_entries = self.data_manager.get_hiddenblock_data(self.map_name)
        self.entries = _entries_from_raw(raw_entries)

        selected_game_data_id = (
            id(self.selected_entry.game_data) if self.selected_entry else None
        )

        self.tree.delete(*self.tree.get_children())
        row_to_select = None
        for index, entry in enumerate(self.entries):
            row_id = self.tree.insert(
                "", "end", iid=str(index), values=(entry.lot, get_lot_name_by_data(entry.reward), entry.rate)
            )
            if id(entry.game_data) == selected_game_data_id:
                row_to_select = row_id

        if row_to_select is not None:
            self.tree.selection_set(row_to_select)
        else:
            self._show_entry(None)

    def _on_tree_select(self, event) -> None:
        selection = self.tree.selection()
        if not selection:
            self._show_entry(None)
            return
        index = int(selection[0])
        self._show_entry(self.entries[index])

    def _show_entry(self, entry: HiddenBlockEntry | None) -> None:
        self.selected_entry = entry
        if entry is None:
            self.title_label.config(text="Nothing selected")
            self.reward_combobox.config(state="disabled")
            self.reward_combobox.set("")
            self.rate_spinbox.config(state="disabled")
            self.rate_spinbox.delete(0, "end")
            self.apply_button.config(state="disabled")
            self._set_raw_text("")
            return

        self.title_label.config(text=f"Lot {entry.lot}")
        self.reward_combobox.config(state="readonly")
        self.reward_combobox.set(get_lot_name_by_data(entry.reward))
        self.rate_spinbox.config(state="normal")
        self.rate_spinbox.delete(0, "end")
        self.rate_spinbox.insert(0, str(entry.rate))
        self.apply_button.config(state="normal")
        self._set_raw_text(json.dumps(entry.game_data, indent=2, ensure_ascii=False))

    def _set_raw_text(self, text: str) -> None:
        self.raw_text.config(state="normal")
        self.raw_text.delete("1.0", tk.END)
        self.raw_text.insert("1.0", text)
        self.raw_text.config(state="disabled")

    def _apply(self) -> None:
        if not self.selected_entry:
            return

        reward_name = self.reward_combobox.get()
        reward_data = get_lot_data_by_name(reward_name)
        if reward_data is None:
            return
        try:
            rate = int(self.rate_spinbox.get())
        except ValueError:
            return

        entry = self.selected_entry
        entry.reward = reward_data
        entry.rate = rate
        entry.game_data["Result"] = reward_data
        entry.game_data["Rate"] = rate

        # Push through the manager, not just the local dict, so this
        # follows the exact same propagation the legacy widget uses:
        # broadcast to every other (non-Map06... there is no Map06
        # exception for Hidden Block, it's shared by all 7 maps) map's
        # in-memory copy, and notify every registered listener --
        # including the legacy "Hidden Block" tab -- to refresh.
        current_raw = self.data_manager.get_hiddenblock_data(self.map_name)
        self.data_manager.update_hiddenblock_data(self.map_name, current_raw)
        self.data_manager.sync_with_linked_maps(self.map_name)
