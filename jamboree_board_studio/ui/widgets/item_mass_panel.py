"""Item Mass panel in board vocabulary (a table + inspector, not raw lots).

Item Mass data is per-map (no cross-map sharing, like Item Bag), and the
legacy ``ItemMassEditor`` widget already keeps its live entries in
``ItemMassDataManager`` (register as a listener, edit through
``update_item_mass_data``, get notified via ``refresh_data()`` when
anything -- including this panel itself -- changes it). This panel plugs
into that exact same protocol rather than keeping a second copy of the
data: it is another *view* over the manager's state, not a second source
of truth.

Scope for this first pass: view and edit existing entries (item, lot).
Add/remove entries still happens on the original "Item Mass" tab -- this
isn't a replacement for it yet, just a first alternate view built on the
same model+adapter pattern as the Item Bag preview panel.
"""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk

from jamboree_board_studio.core.items.item_mass import ItemMassEntry

_LOT_NUMBERS = [0, 1, 2, 3, 5, 7, 8]


def _entries_from_raw(raw_entries: list[dict]) -> list[ItemMassEntry]:
    """Same shape as core.items.item_mass.parse_item_mass, but over an
    already-loaded list (ItemMassDataManager's live data) instead of
    re-reading a file -- mirrors item_bag_panel._entries_from_raw's
    reasoning: game_data stays the *same* dict object, so an edit here is
    the same edit the manager (and the legacy widget) already sees.
    """
    entries = []
    for entry in raw_entries:
        if not all(key in entry for key in ("Item", "No")):
            continue
        entries.append(ItemMassEntry(item=entry["Item"], lot=entry["No"], game_data=entry))
    return entries


class ItemMassPanel(ttk.Frame):
    def __init__(self, parent, map_name: str, data_manager, general_items, map_items):
        super().__init__(parent)
        self.map_name = map_name
        self.data_manager = data_manager
        self.entries: list[ItemMassEntry] = []
        self.selected_entry: ItemMassEntry | None = None

        map_specific_items = map_items[self.map_name]["items"]
        self.combined_items = map_specific_items + general_items

        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        table_frame = ttk.Frame(self)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ttk.Label(table_frame, text="Item Mass", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(0, 4)
        )

        tree_container = ttk.Frame(table_frame)
        tree_container.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(
            tree_container,
            columns=("item", "lot"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("item", text="Item")
        self.tree.heading("lot", text="Lot")
        self.tree.column("item", width=150, anchor="w")
        self.tree.column("lot", width=60, anchor="center", stretch=False)

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        note = ttk.Label(
            table_frame,
            text="Add/remove items on the “Item Mass” tab; edit existing ones here.",
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

        lot_frame = ttk.Frame(inspector_frame)
        lot_frame.pack(fill="x", pady=2)
        ttk.Label(lot_frame, text="Lot").pack(side="left")
        self.lot_combobox = ttk.Combobox(
            lot_frame, values=_LOT_NUMBERS, state="disabled", width=16
        )
        self.lot_combobox.pack(side="right")

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
        """Listener protocol expected by ItemMassDataManager.notify_listeners()."""
        raw_entries = self.data_manager.get_item_mass_data(self.map_name)
        self.entries = _entries_from_raw(raw_entries)

        selected_game_data_id = (
            id(self.selected_entry.game_data) if self.selected_entry else None
        )

        self.tree.delete(*self.tree.get_children())
        row_to_select = None
        for index, entry in enumerate(self.entries):
            row_id = self.tree.insert(
                "", "end", iid=str(index), values=(entry.item, entry.lot)
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

    def _show_entry(self, entry: ItemMassEntry | None) -> None:
        self.selected_entry = entry
        if entry is None:
            self.title_label.config(text="Nothing selected")
            self.item_combobox.config(state="disabled")
            self.item_combobox.set("")
            self.lot_combobox.config(state="disabled")
            self.lot_combobox.set("")
            self.apply_button.config(state="disabled")
            self._set_raw_text("")
            return

        self.title_label.config(text=entry.item)
        self.item_combobox.config(state="normal")
        self.item_combobox.set(entry.item)
        self.lot_combobox.config(state="readonly")
        self.lot_combobox.set(entry.lot)
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
        try:
            lot = int(self.lot_combobox.get())
        except ValueError:
            return
        if lot not in _LOT_NUMBERS:
            return

        entry = self.selected_entry
        entry.item = item_name
        entry.lot = lot
        entry.game_data["Item"] = item_name
        entry.game_data["No"] = lot

        # Push through the manager (not just the local dict), the same
        # way ItemBagPanel._apply() does: re-set the same list object so
        # every registered listener -- including the legacy "Item Mass"
        # tab -- gets refresh_data() called. Item Mass has no cross-map
        # sync (like Item Bag, unlike Hidden Block), so that's it.
        current_raw = self.data_manager.get_item_mass_data(self.map_name)
        self.data_manager.update_item_mass_data(self.map_name, current_raw)
