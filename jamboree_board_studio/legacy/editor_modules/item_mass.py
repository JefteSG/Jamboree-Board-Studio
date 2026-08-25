import random
import tkinter as tk
from tkinter import ttk

from jamboree_board_studio.core.items.item_mass import (
    ItemMassEntry,
    ItemMassParseError,
    parse_item_mass,
    serialize_item_mass,
)


class ItemMassDataManager:
    """Holds each map's live Item Mass entries and notifies registered views
    (``ItemMassEditor``, and any future board-vocabulary panel) when they
    change. Same listener protocol as ``ItemBagDataManager``/
    ``HiddenBlockDataManager``/``EventDataManager``, minus cross-map
    syncing: each map's Item Mass is independent.

    Introduced for the same reason ItemBagDataManager was: before this,
    ``ItemMassEditor`` kept no live list of its own -- its per-lot
    listboxes *were* the only state, and ``save_items()`` reconstructed
    entries by reading that display text back out. A second view over the
    same data would have had no way to see edits made through the first.
    """

    def __init__(self):
        self.item_mass_data = {}
        self.listeners = []

    def register_listener(self, listener):
        self.listeners.append(listener)

    def get_item_mass_data(self, map_name):
        return self.item_mass_data.get(map_name, [])

    def update_item_mass_data(self, map_name, item_mass_data):
        self.item_mass_data[map_name] = item_mass_data
        self.notify_listeners()

    def notify_listeners(self):
        for listener in self.listeners:
            listener.refresh_data()


class ItemMassEditor:
    def __init__(
        self, parent, data_manager, map_name, app_width, general_items, map_items
    ):
        self.data_manager = data_manager
        self.map_name = map_name.replace(" ", "_")
        self.combined_items = map_items[self.map_name]["items"] + general_items
        self.lots = {}

        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = 7
        rows = 1

        for col in range(columns):
            self.frame.grid_columnconfigure(col, weight=1, uniform="group")
        for row in range(rows):
            self.frame.grid_rowconfigure(row, weight=1, uniform="group")

        num_columns = 7
        for index, lot_no in enumerate([0, 1, 2, 3, 5, 7, 8]):
            self.create_lot_column(lot_no, app_width, index, num_columns)

        self.data_manager.register_listener(self)

    def create_lot_column(self, lot_no, app_width, index, num_columns):
        column_width = app_width // num_columns

        row = index // num_columns
        column = index % num_columns

        lot_frame = ttk.LabelFrame(self.frame, text=f"{lot_no}", width=column_width)
        lot_frame.grid(row=row, column=column, padx=5, pady=5, sticky="nsew")

        entry = ttk.Combobox(lot_frame, values=self.combined_items, width=column_width)
        entry.pack(pady=5)

        add_button = ttk.Button(
            lot_frame,
            text="Add Item",
            command=lambda: self.add_item(lot_no, entry),
            width=column_width,
        )
        add_button.pack(pady=5)

        scroll_frame = tk.Frame(lot_frame)
        scroll_frame.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(scroll_frame)
        listbox = tk.Listbox(
            scroll_frame, yscrollcommand=scrollbar.set, height=10, width=column_width
        )
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        remove_button = ttk.Button(
            lot_frame,
            text="Remove Item",
            command=lambda: self.remove_item(lot_no),
            width=column_width,
        )
        remove_button.pack(pady=5)

        self.lots[lot_no] = {"entry": entry, "listbox": listbox}

    def add_item(self, lot_no, entry):
        item = entry.get()
        if item:
            current = list(self.data_manager.get_item_mass_data(self.map_name))
            current.append({"Item": item, "No": lot_no})
            self.data_manager.update_item_mass_data(self.map_name, current)

    def remove_item(self, lot_no):
        listbox = self.lots[lot_no]["listbox"]
        selected_index = listbox.curselection()
        if selected_index:
            lot_entries = [
                e
                for e in self.data_manager.get_item_mass_data(self.map_name)
                if e.get("No") == lot_no
            ]
            index_in_lot = selected_index[0]
            if index_in_lot < len(lot_entries):
                current = list(self.data_manager.get_item_mass_data(self.map_name))
                current.remove(lot_entries[index_in_lot])
                self.data_manager.update_item_mass_data(self.map_name, current)

    def load_items(self, data):
        items = data.get(self.map_name, [])
        self.data_manager.update_item_mass_data(self.map_name, items)

    def randomize_items(self, probability=0.2):
        new_items = []
        for lot_no in self.lots:
            for item in self.combined_items:
                if random.random() < probability:
                    new_items.append({"Item": item, "No": lot_no})
        self.data_manager.update_item_mass_data(self.map_name, new_items)

    def save_items(self):
        return list(self.data_manager.get_item_mass_data(self.map_name))

    def refresh_data(self):
        """Listener protocol expected by ItemMassDataManager.notify_listeners()."""
        for lot_data in self.lots.values():
            lot_data["listbox"].delete(0, tk.END)

        for item in self.data_manager.get_item_mass_data(self.map_name):
            lot_no = item.get("No")
            lot_data = self.lots.get(lot_no)
            if lot_data is None:
                continue
            lot_data["listbox"].insert(tk.END, item.get("Item", ""))


def load_itemmass_mapdata(base_path, map_name):
    """Load bd00_ItemMass_<map>.json's entries as plain dicts, keyed by map_name.

    Delegates to jamboree_board_studio.core.items.item_mass; this
    wrapper unwraps back to the {map_name: [...]} shape this module's UI
    code expects, and keeps this function's original behavior of
    returning an empty list (with a printed message) rather than raising
    when the file is missing or invalid.
    """
    try:
        entries = parse_item_mass(base_path, map_name)
    except ItemMassParseError as error:
        print(error)
        entries = []
    return {map_name: [entry.game_data for entry in entries]}


def save_itemmass_mapdata(base_path, item_mass_data, map_name):
    """Save Item Mass entries (plain dicts) via the same adapter used to load them."""
    entries = [
        ItemMassEntry(item=d["Item"], lot=d["No"], game_data=d) for d in item_mass_data
    ]
    serialize_item_mass(entries, base_path, map_name)
