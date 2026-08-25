import random
from tkinter import ttk
import tkinter as tk

from jamboree_board_studio.core.items.item_shop import (
    PHASES,
    SHOPS,
    SLOTS,
    ItemShopParseError,
    ShopSlotEntry,
    empty_item_shop,
    parse_item_shop,
    serialize_item_shop,
)


class ItemShopDataManager:
    """Holds each map's live Item Shop grid (both shops, all phases/slots)
    and notifies registered views (the "Koopa Shop"/"Kamek Shop"
    ``ItemShopEditor`` instances, and any future board-vocabulary panel)
    when it changes. Same listener protocol as ``ItemBagDataManager``/
    ``ItemMassDataManager`` -- no cross-map syncing, each map's shops are
    independent.

    Unlike Item Bag/Item Mass, ``ItemShopEditor`` already had a real
    live data object before this (``self.data_store``, the same nested
    {"KoopaShop": {...}, "KamekShop": {...}} dict shared by both shop
    editors for a map) -- it just wasn't reachable from outside them, and
    wasn't updated until ``save_shop_data()``/``randomize_shop_data()``
    explicitly wrote to it. This manager makes that same dict reachable
    by a second view (the preview panel) and keeps it live: every widget
    change that already called into ``save_shop_data``/
    ``randomize_shop_data`` now also pushes into the manager immediately,
    the same way ``ItemBagEditor.add_item`` does.
    """

    def __init__(self):
        self.item_shop_data = {}
        self.listeners = []

    def register_listener(self, listener):
        self.listeners.append(listener)

    def get_item_shop_data(self, map_name):
        return self.item_shop_data.setdefault(
            map_name, _entries_to_nested_dict(empty_item_shop())
        )

    def update_item_shop_data(self, map_name, data):
        self.item_shop_data[map_name] = data
        self.notify_listeners()

    def notify_listeners(self):
        for listener in self.listeners:
            listener.refresh_data()


class ItemShopEditor:
    def __init__(
        self, parent, shop_name, data_manager, map_name, general_items, map_items
    ):
        self.data_manager = data_manager
        self.map_name = map_name.replace(" ", "_")
        self.shop_name = shop_name

        map_specific_items = map_items[self.map_name]["items"]
        combined_items = ["Empty"] + map_specific_items + general_items
        combined_items_pro = ["Empty"] + map_specific_items + general_items
        combined_items_pro.remove("ItemBag")
        self.random_item_pack = combined_items
        self.random_item_pack_pro = combined_items_pro

        self.widgets = {"P0": {}, "P1": {}, "P2": {}}

        self.create_phase(parent, "Standard", "P0", combined_items)
        self.create_phase(parent, "Standard (5 Last Turns)", "P1", combined_items)
        self.create_phase(parent, "Pro Mode", "P2", combined_items_pro)

        self.data_manager.register_listener(self)

    def create_phase(self, parent, phase_label, phase_name, combined_items):
        phase_frame = ttk.LabelFrame(parent, text=phase_label)
        phase_frame.pack(fill="x", padx=5, pady=5)

        for i in range(1, 7):
            phase_frame.columnconfigure(i, weight=1)
            slot_frame = ttk.LabelFrame(phase_frame, text=f"Slot {i}")
            slot_frame.grid(row=0, column=i - 1, padx=5, pady=5, sticky="nsew")

            slot_frame.grid_columnconfigure(0, weight=1)

            self.widgets[phase_name][f"slot{i}"] = {
                "item": ttk.Combobox(
                    slot_frame, values=combined_items, width=18, justify="center"
                ),
                "count": ttk.Combobox(
                    slot_frame, values=[1, 2], width=18, justify="center"
                ),
                "price": tk.Spinbox(
                    slot_frame, from_=0, to=999, width=18, justify="center"
                ),
            }

            self.widgets[phase_name][f"slot{i}"]["item"].grid(
                row=0, column=0, padx=18, pady=5, sticky="ew"
            )
            self.widgets[phase_name][f"slot{i}"]["count"].grid(
                row=1, column=0, padx=18, pady=5, sticky="ew"
            )
            self.widgets[phase_name][f"slot{i}"]["price"].grid(
                row=2, column=0, padx=18, pady=5, sticky="ew"
            )

    def load_shop_data(self, phase_name, data):
        # `data` is the whole per-map nested dict (both shops) returned
        # by load_itemshop_mapdata; MapTab.load_data() calls this once
        # per phase, per shop editor, always with that same dict. Pushing
        # it through the manager (rather than just assigning it locally)
        # is what makes it reachable by the other shop editor and any
        # panel; refresh_data(), triggered by the update below, is what
        # actually populates this editor's own widgets from it.
        self.data_manager.update_item_shop_data(self.map_name, data)

    def randomize_shop_data(self, phase_name):
        for slot_num in range(1, 7):
            self.widgets[phase_name][f"slot{slot_num}"]["item"].set(
                random.choice(self.random_item_pack_pro if phase_name == "P2" else self.random_item_pack)
            )
            self.widgets[phase_name][f"slot{slot_num}"]["count"].set(
                random.choice([1,2])
            )
            self.widgets[phase_name][f"slot{slot_num}"]["price"].delete(0, "end")
            self.widgets[phase_name][f"slot{slot_num}"]["price"].insert(
                0,random.choice([1,5,10,15] if phase_name == "P2" else [1,5,10,15,20,25,30,50])
            )
        self._sync_phase_to_manager(phase_name)

    def save_shop_data(self, phase_name):
        return self._sync_phase_to_manager(phase_name)

    def _sync_phase_to_manager(self, phase_name):
        """Read this phase's current widget values and push them into the
        manager's live per-map dict (the same object shared with the
        other shop editor), returning that whole dict -- matches
        save_shop_data()'s original return shape exactly.
        """
        data = self.data_manager.get_item_shop_data(self.map_name)
        data.setdefault(self.shop_name, {})
        data[self.shop_name][phase_name] = {
            f"slot{slot_num}": {
                "item": self.widgets[phase_name][f"slot{slot_num}"]["item"].get(),
                "count": self.widgets[phase_name][f"slot{slot_num}"]["count"].get(),
                "price": self.widgets[phase_name][f"slot{slot_num}"]["price"].get(),
            }
            for slot_num in range(1, 7)
        }
        self.data_manager.update_item_shop_data(self.map_name, data)
        return data

    def refresh_data(self):
        """Listener protocol expected by ItemShopDataManager.notify_listeners().

        Repopulates every phase's widgets for *this* shop from the
        manager's current data -- fires on any update, including ones
        made by the other shop editor or a panel, but only this shop's
        slice of the data actually changes this editor's own widgets.
        """
        data = self.data_manager.get_item_shop_data(self.map_name)
        shop_data = data.get(self.shop_name, {})
        for phase_name, phase_data in shop_data.items():
            if phase_name not in self.widgets:
                continue
            for slot_num in range(1, 7):
                slot_data = phase_data.get(f"slot{slot_num}")
                if slot_data:
                    self.widgets[phase_name][f"slot{slot_num}"]["item"].set(
                        slot_data.get("item", "")
                    )
                    self.widgets[phase_name][f"slot{slot_num}"]["count"].set(
                        slot_data.get("count", "")
                    )
                    self.widgets[phase_name][f"slot{slot_num}"]["price"].delete(0, "end")
                    self.widgets[phase_name][f"slot{slot_num}"]["price"].insert(
                        0, slot_data.get("price", 0)
                    )


def _entries_to_nested_dict(entries):
    """[ShopSlotEntry, ...] (36) -> {"KoopaShop": {"P0": {"slot1": {...}, ...}, ...}, ...}

    Matches the shape editor.py/ItemShopEditor expect: count/price as
    strings (mirroring what ttk widgets' .get() returns), keyed by
    "<Shop>Shop" / "P<phase>" / "slot<n>".
    """
    grid = {f"{shop}Shop": {f"P{phase}": {} for phase in PHASES} for shop in SHOPS}
    for entry in entries:
        grid[f"{entry.shop}Shop"][f"P{entry.phase}"][f"slot{entry.slot}"] = {
            "item": entry.item,
            "count": str(entry.count),
            "price": str(entry.price),
        }
    return grid


def _nested_dict_to_entries(data):
    """Inverse of _entries_to_nested_dict."""
    return [
        ShopSlotEntry(
            shop=shop,
            phase=phase,
            slot=slot_no,
            item=data[f"{shop}Shop"][f"P{phase}"][f"slot{slot_no}"]["item"],
            count=int(data[f"{shop}Shop"][f"P{phase}"][f"slot{slot_no}"]["count"]),
            price=int(data[f"{shop}Shop"][f"P{phase}"][f"slot{slot_no}"]["price"]),
        )
        for shop in SHOPS
        for phase in PHASES
        for slot_no in SLOTS
    ]


def save_itemshop_mapdata(BASE_PATH, map_name, data):
    """Save shop data (the nested {"KoopaShop": {"P0": {...}}} shape) via the shared adapter."""
    serialize_item_shop(_nested_dict_to_entries(data), BASE_PATH, map_name)


def load_itemshop_mapdata(BASE_PATH, map_name):
    """Load shop data as the nested {"KoopaShop": {"P0": {...}}} shape this module's UI expects.

    Delegates to jamboree_board_studio.core.items.item_shop; keeps this
    function's original behavior of treating a missing/invalid file as
    "every slot empty" rather than raising, since that adapter is
    stricter by design (see its docstring).
    """
    try:
        entries = parse_item_shop(BASE_PATH, map_name)
    except ItemShopParseError as error:
        print(error)
        entries = empty_item_shop()
    return _entries_to_nested_dict(entries)
