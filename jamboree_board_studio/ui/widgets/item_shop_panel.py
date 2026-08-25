"""Item Shop panel in board vocabulary (a table across both shops/phases,
not six separate slot columns per phase).

Item Shop data is per-map (no cross-map sharing, like Item Bag/Item
Mass), and the legacy ``ItemShopEditor`` widgets (one per shop: Koopa,
Kamek) already keep their live grid in ``ItemShopDataManager`` (register
as a listener, edit through ``update_item_shop_data``, get notified via
``refresh_data()`` when anything -- including this panel itself --
changes it). This panel plugs into that exact same protocol rather than
keeping a second copy of the data: it is another *view* over the
manager's state, not a second source of truth. Unlike the other preview
panels, this one covers *both* shop editors at once, since the manager's
per-map data already spans both.

Scope for this first pass: view and edit existing slots (item, count,
price) for all 36 (shop, phase, slot) combinations. Slots always exist
(there's no add/remove -- "Empty" is itself a valid item, same as the
legacy tab).
"""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk

from jamboree_board_studio.core.items.item_shop import PHASES, SHOPS, SLOTS, ShopSlotEntry

_PHASE_LABELS = {0: "Standard", 1: "Standard (5 Last Turns)", 2: "Pro Mode"}
_COUNT_VALUES = [1, 2]


def _entries_from_raw(shop_data: dict) -> list[ShopSlotEntry]:
    """shop_data is the manager's whole per-map nested dict
    ({"KoopaShop": {"P0": {"slot1": {...}, ...}, ...}, "KamekShop": {...}}).
    Builds one ShopSlotEntry per (shop, phase, slot), with game_data set
    to the actual slot dict object from that structure -- same reasoning
    as every other panel's _entries_from_raw: an edit here mutates the
    same dict the manager (and the legacy widgets) already see.
    """
    entries = []
    for shop in SHOPS:
        shop_key = f"{shop}Shop"
        phases = shop_data.get(shop_key, {})
        for phase in PHASES:
            slots = phases.get(f"P{phase}", {})
            for slot_no in SLOTS:
                slot_data = slots.get(f"slot{slot_no}")
                if not slot_data:
                    continue
                try:
                    count = int(slot_data.get("count") or 0)
                except (TypeError, ValueError):
                    count = 0
                try:
                    price = int(slot_data.get("price") or 0)
                except (TypeError, ValueError):
                    price = 0
                entries.append(
                    ShopSlotEntry(
                        shop=shop,
                        phase=phase,
                        slot=slot_no,
                        item=slot_data.get("item", "Empty"),
                        count=count,
                        price=price,
                        game_data=slot_data,
                    )
                )
    return entries


class ItemShopPanel(ttk.Frame):
    def __init__(self, parent, map_name: str, data_manager, general_items, map_items):
        super().__init__(parent)
        self.map_name = map_name
        self.data_manager = data_manager
        self.entries: list[ShopSlotEntry] = []
        self.selected_entry: ShopSlotEntry | None = None

        map_specific_items = map_items[self.map_name]["items"]
        # Not restricting Pro Mode's item list the way the legacy tab
        # does (it excludes "ItemBag") -- this is a view/edit panel over
        # existing slots, not a stricter gatekeeper than the model itself.
        self.combined_items = ["Empty"] + map_specific_items + general_items

        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        table_frame = ttk.Frame(self)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ttk.Label(table_frame, text="Item Shop", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(0, 4)
        )

        tree_container = ttk.Frame(table_frame)
        tree_container.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(
            tree_container,
            columns=("shop", "phase", "slot", "item", "count", "price"),
            show="headings",
            selectmode="browse",
        )
        for col, label, width in (
            ("shop", "Shop", 60),
            ("phase", "Phase", 150),
            ("slot", "Slot", 40),
            ("item", "Item", 120),
            ("count", "Count", 50),
            ("price", "Price", 50),
        ):
            self.tree.heading(col, text=label)
            self.tree.column(
                col, width=width, anchor="center" if col != "item" else "w", stretch=col == "item"
            )

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        note = ttk.Label(
            table_frame,
            text="Every slot always exists (“Empty” is a valid item); "
            "edit item/count/price here or on the “Koopa Shop”/“Kamek Shop” tabs.",
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

        count_frame = ttk.Frame(inspector_frame)
        count_frame.pack(fill="x", pady=2)
        ttk.Label(count_frame, text="Count").pack(side="left")
        self.count_combobox = ttk.Combobox(
            count_frame, values=_COUNT_VALUES, state="disabled", width=16
        )
        self.count_combobox.pack(side="right")

        price_frame = ttk.Frame(inspector_frame)
        price_frame.pack(fill="x", pady=2)
        ttk.Label(price_frame, text="Price").pack(side="left")
        self.price_spinbox = ttk.Spinbox(price_frame, from_=0, to=999, width=16, state="disabled")
        self.price_spinbox.pack(side="right")

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
        """Listener protocol expected by ItemShopDataManager.notify_listeners()."""
        shop_data = self.data_manager.get_item_shop_data(self.map_name)
        self.entries = _entries_from_raw(shop_data)

        selected_game_data_id = (
            id(self.selected_entry.game_data) if self.selected_entry else None
        )

        self.tree.delete(*self.tree.get_children())
        row_to_select = None
        for index, entry in enumerate(self.entries):
            row_id = self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    entry.shop,
                    _PHASE_LABELS.get(entry.phase, entry.phase),
                    entry.slot,
                    entry.item,
                    entry.count,
                    entry.price,
                ),
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

    def _show_entry(self, entry: ShopSlotEntry | None) -> None:
        self.selected_entry = entry
        if entry is None:
            self.title_label.config(text="Nothing selected")
            self.item_combobox.config(state="disabled")
            self.item_combobox.set("")
            self.count_combobox.config(state="disabled")
            self.count_combobox.set("")
            self.price_spinbox.config(state="disabled")
            self.price_spinbox.delete(0, "end")
            self.apply_button.config(state="disabled")
            self._set_raw_text("")
            return

        self.title_label.config(
            text=f"{entry.shop} Shop – {_PHASE_LABELS.get(entry.phase, entry.phase)} – Slot {entry.slot}"
        )
        self.item_combobox.config(state="normal")
        self.item_combobox.set(entry.item)
        self.count_combobox.config(state="readonly")
        self.count_combobox.set(entry.count)
        self.price_spinbox.config(state="normal")
        self.price_spinbox.delete(0, "end")
        self.price_spinbox.insert(0, str(entry.price))
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
            count = int(self.count_combobox.get())
        except ValueError:
            return
        try:
            price = int(self.price_spinbox.get())
        except ValueError:
            return

        entry = self.selected_entry
        entry.item = item_name
        entry.count = count
        entry.price = price
        # count/price are stored as strings in this layer (mirroring what
        # the legacy ttk widgets' .get() returns) -- see
        # _entries_to_nested_dict in legacy/editor_modules/item_shop.py.
        entry.game_data["item"] = item_name
        entry.game_data["count"] = str(count)
        entry.game_data["price"] = str(price)

        # Push through the manager (not just the local dict), the same
        # way ItemMassPanel._apply() does: re-set the same nested dict
        # object so every registered listener -- including both the
        # "Koopa Shop" and "Kamek Shop" legacy tabs -- gets refresh_data()
        # called. Item Shop has no cross-map sync (like Item Bag/Item
        # Mass, unlike Hidden Block), so that's the whole story here.
        current_raw = self.data_manager.get_item_shop_data(self.map_name)
        self.data_manager.update_item_shop_data(self.map_name, current_raw)
