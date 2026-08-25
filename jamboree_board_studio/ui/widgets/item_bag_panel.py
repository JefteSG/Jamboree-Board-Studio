"""Item Bag panel in board vocabulary (phase name, not raw index).

Item Bag data is per-map (unlike Hidden Block, there is no cross-map
sharing here), and the legacy ``ItemBagEditor`` widget already keeps its
live entries in ``ItemBagDataManager`` (register as a listener, edit
through ``update_item_bag_data``, get notified via ``refresh_data()``
when anything -- including this panel itself -- changes it). This panel
plugs into that exact same protocol rather than keeping a second copy of
the data: it is another *view* over the manager's state, not a second
source of truth.

Scope for this first pass: view and edit existing entries (item, phase,
unique) using the same phase names the legacy tab shows. Add/remove
entries still happens on the original "Item Bag" tab -- this isn't a
replacement for it yet, just a first alternate view built on the same
model+adapter pattern as the Hidden Block preview panel.
"""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk

from jamboree_board_studio.core.items.item_bag import ItemBagEntry

_PHASE_NAMES = ["Standard", "Standard (5 Last Turns)"]


def _entries_from_raw(raw_entries: list[dict]) -> list[ItemBagEntry]:
    """Same shape as core.items.item_bag.parse_item_bag, but over an
    already-loaded list (ItemBagDataManager's live data) instead of
    re-reading a file -- mirrors hidden_block_panel._entries_from_raw's
    reasoning: game_data stays the *same* dict object, so an edit here is
    the same edit the manager (and the legacy widget) already sees.
    """
    entries = []
    for entry in raw_entries:
        if not all(key in entry for key in ("Item", "Phase", "Unique")):
            continue
        entries.append(
            ItemBagEntry(
                item=entry["Item"],
                phase=entry["Phase"],
                unique=bool(entry["Unique"]),
                game_data=entry,
            )
        )
    return entries


class ItemBagPanel(ttk.Frame):
    def __init__(self, parent, map_name: str, data_manager, general_items, map_items):
        super().__init__(parent)
        self.map_name = map_name
        self.data_manager = data_manager
        self.entries: list[ItemBagEntry] = []
        self.selected_entry: ItemBagEntry | None = None

        map_specific_items = map_items[self.map_name]["items"]
        self.combined_items = map_specific_items + general_items

        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        table_frame = ttk.Frame(self)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ttk.Label(table_frame, text="Item Bag", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(0, 4)
        )

        tree_container = ttk.Frame(table_frame)
        tree_container.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(
            tree_container,
            columns=("item", "phase", "unique"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("item", text="Item")
        self.tree.heading("phase", text="Phase")
        self.tree.heading("unique", text="Unique")
        self.tree.column("item", width=120, anchor="w")
        self.tree.column("phase", width=150, anchor="w")
        self.tree.column("unique", width=60, anchor="center", stretch=False)

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        note = ttk.Label(
            table_frame,
            text="Add/remove items on the “Item Bag” tab; edit existing ones here.",
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

        item_frame = ttk.Frame(inspector_frame)
        item_frame.pack(fill="x", pady=2)
        ttk.Label(item_frame, text="Item").pack(side="left")
        self.item_combobox = ttk.Combobox(
            item_frame, values=self.combined_items, state="disabled", width=16
        )
        self.item_combobox.pack(side="right")

        phase_frame = ttk.Frame(inspector_frame)
        phase_frame.pack(fill="x", pady=2)
        ttk.Label(phase_frame, text="Phase").pack(side="left")
        self.phase_combobox = ttk.Combobox(
            phase_frame, values=_PHASE_NAMES, state="disabled", width=16
        )
        self.phase_combobox.pack(side="right")

        unique_frame = ttk.Frame(inspector_frame)
        unique_frame.pack(fill="x", pady=2)
        ttk.Label(unique_frame, text="Unique").pack(side="left")
        self.unique_var = tk.IntVar()
        self.unique_checkbutton = tk.Checkbutton(
            unique_frame, variable=self.unique_var, state="disabled"
        )
        self.unique_checkbutton.pack(side="right")

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
        """Listener protocol expected by ItemBagDataManager.notify_listeners()."""
        raw_entries = self.data_manager.get_item_bag_data(self.map_name)
        self.entries = _entries_from_raw(raw_entries)

        selected_game_data_id = (
            id(self.selected_entry.game_data) if self.selected_entry else None
        )

        self.tree.delete(*self.tree.get_children())
        row_to_select = None
        for index, entry in enumerate(self.entries):
            phase_name = (
                _PHASE_NAMES[entry.phase]
                if 0 <= entry.phase < len(_PHASE_NAMES)
                else str(entry.phase)
            )
            row_id = self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(entry.item, phase_name, "Yes" if entry.unique else "No"),
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

    def _show_entry(self, entry: ItemBagEntry | None) -> None:
        self.selected_entry = entry
        if entry is None:
            self.title_label.config(text="Nothing selected")
            self.item_combobox.config(state="disabled")
            self.item_combobox.set("")
            self.phase_combobox.config(state="disabled")
            self.phase_combobox.set("")
            self.unique_checkbutton.config(state="disabled")
            self.unique_var.set(0)
            self.apply_button.config(state="disabled")
            self._set_raw_text("")
            return

        self.title_label.config(text=entry.item)
        self.item_combobox.config(state="normal")
        self.item_combobox.set(entry.item)
        self.phase_combobox.config(state="readonly")
        self.phase_combobox.set(
            _PHASE_NAMES[entry.phase] if 0 <= entry.phase < len(_PHASE_NAMES) else ""
        )
        self.unique_checkbutton.config(state="normal")
        self.unique_var.set(1 if entry.unique else 0)
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

        item_name = self.item_combobox.get()
        if not item_name:
            return
        phase_name = self.phase_combobox.get()
        if phase_name not in _PHASE_NAMES:
            return
        phase_idx = _PHASE_NAMES.index(phase_name)
        unique = bool(self.unique_var.get())

        entry = self.selected_entry
        entry.item = item_name
        entry.phase = phase_idx
        entry.unique = unique
        entry.game_data["Item"] = item_name
        entry.game_data["Phase"] = phase_idx
        entry.game_data["Unique"] = int(unique)

        # Push through the manager (not just the local dict), the same way
        # HiddenBlockPanel._apply() does: re-set the same list object so
        # every registered listener -- including the legacy "Item Bag"
        # tab -- gets refresh_data() called. Item Bag has no cross-map
        # sync (unlike Hidden Block), so that's the whole story here.
        current_raw = self.data_manager.get_item_bag_data(self.map_name)
        self.data_manager.update_item_bag_data(self.map_name, current_raw)
