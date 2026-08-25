import random
import tkinter as tk
from tkinter import ttk

from jamboree_board_studio.core.items.item_bag import (
    ItemBagEntry,
    ItemBagParseError,
    parse_item_bag,
    serialize_item_bag,
)


class ItemBagDataManager:
    """Holds each map's live Item Bag entries and notifies registered views
    (``ItemBagEditor``, and any future board-vocabulary panel) when they
    change. Same listener protocol as ``HiddenBlockDataManager``/
    ``EventDataManager``, minus cross-map syncing: each map's Item Bag is
    independent, there is no equivalent of KoopaMass/Hidden Block sharing
    here.

    Introduced so a second view over this data (e.g. a future preview
    panel) can't silently disagree with ``ItemBagEditor`` about what the
    current entries are — before this, ``ItemBagEditor`` kept no live
    list of its own at all; its listbox display *was* the only state, and
    ``save_items()`` reconstructed entries by parsing that display text.
    """

    def __init__(self):
        self.item_bag_data = {}
        self.listeners = []

    def register_listener(self, listener):
        self.listeners.append(listener)

    def get_item_bag_data(self, map_name):
        return self.item_bag_data.get(map_name, [])

    def update_item_bag_data(self, map_name, item_bag_data):
        self.item_bag_data[map_name] = item_bag_data
        self.notify_listeners()

    def notify_listeners(self):
        for listener in self.listeners:
            listener.refresh_data()


class ItemBagEditor:
    def __init__(
        self, parent, data_manager, map_name, app_width, general_items, map_items
    ):
        self.data_manager = data_manager
        self.map_name = map_name.replace(" ", "_")

        map_specific_items = map_items[self.map_name]["items"]
        self.combined_items = map_specific_items + general_items

        self.frame = ttk.Frame(parent)
        self.frame.pack(
            side="left",
            padx=(app_width * 0.05, app_width * 0.05 // 2),
            pady=10,
            fill="both",
            expand=True,
        )

        self.add_form_frame = tk.Frame(self.frame)
        self.add_form_frame.pack(pady=5)

        self.add_button_frame = tk.Frame(self.frame)
        self.add_button_frame.pack(pady=5)

        self.phase_names = ["Standard", "Standard (5 Last Turns)"]
        self.phase_map = {name: idx for idx, name in enumerate(self.phase_names)}

        self.phase_label = ttk.Label(self.add_form_frame, text="Phase:")
        self.phase_label.grid(row=0, column=1, padx=5, pady=5)
        self.phase_combobox = ttk.Combobox(
            self.add_form_frame, values=self.phase_names, width=25
        )
        self.phase_combobox.grid(row=0, column=2, padx=5, pady=5)

        self.unique_var = tk.IntVar()
        self.unique_checkbutton = tk.Checkbutton(
            self.add_form_frame, text="Unique", variable=self.unique_var
        )
        self.unique_checkbutton.grid(row=0, column=3, padx=5, pady=5)

        self.entry = ttk.Combobox(self.add_form_frame, values=self.combined_items, width=20)
        self.entry.grid(row=0, column=0, padx=5, pady=5)
        self.add_button = ttk.Button(
            self.add_button_frame, text="Add Item", command=self.add_item, width=160
        )
        self.add_button.grid(row=0, column=4, padx=5, pady=5)

        self.phase_frames = {}
        for phase in range(2):
            phase_frame = ttk.LabelFrame(
                self.frame, text=f"{self.phase_names[phase]}", padding=(10, 5)
            )
            phase_frame.pack(fill="both", expand=True, padx=5, pady=5)
            self.phase_frames[phase] = phase_frame

            scroll_frame = tk.Frame(phase_frame)
            scroll_frame.pack(fill="both", expand=True)

            scrollbar = tk.Scrollbar(scroll_frame)
            listbox = tk.Listbox(scroll_frame, yscrollcommand=scrollbar.set, height=5)
            scrollbar.config(command=listbox.yview)
            scrollbar.pack(side="right", fill="y")
            listbox.pack(side="left", fill="both", expand=True)
            self.phase_frames[phase].listbox = listbox

        self.remove_button_frame = tk.Frame(self.frame)
        self.remove_button_frame.pack(pady=5)

        self.remove_button = ttk.Button(
            self.remove_button_frame,
            text="Remove Item",
            command=self.remove_item,
            width=160,
        )
        self.remove_button.pack(pady=5)

        self.data_manager.register_listener(self)

    def add_item(self):
        item = self.entry.get()
        if item:
            phase_name = self.phase_combobox.get()
            phase_idx = self.phase_map.get(phase_name)
            unique = bool(self.unique_var.get())

            current = list(self.data_manager.get_item_bag_data(self.map_name))
            current.append({"Item": item, "Phase": phase_idx, "Unique": int(unique)})
            self.data_manager.update_item_bag_data(self.map_name, current)

    def remove_item(self):
        for phase in range(2):
            selection = self.phase_frames[phase].listbox.curselection()
            if selection:
                phase_entries = [
                    e
                    for e in self.data_manager.get_item_bag_data(self.map_name)
                    if e.get("Phase") == phase
                ]
                index_in_phase = selection[0]
                if index_in_phase < len(phase_entries):
                    current = list(self.data_manager.get_item_bag_data(self.map_name))
                    current.remove(phase_entries[index_in_phase])
                    self.data_manager.update_item_bag_data(self.map_name, current)
                break

    def load_items(self, data):
        items = data.get(self.map_name, [])
        self.data_manager.update_item_bag_data(self.map_name, items)

    def randomize_items(self, add_probability=0.5, unique_probability=0.2):
        new_items = []
        for phase in range(2):
            random_items = []
            # Prendre 2 items au hasard dans la liste d'items disponible
            if len(self.combined_items) >= 2:
                random_items = random.sample(self.combined_items, 2)
                new_items.append({"Item": random_items[0], "Phase": phase, "Unique": 1})
                new_items.append({"Item": random_items[1], "Phase": phase, "Unique": 0})

            # Ajouter les items aléatoires avec les probabilités spécifiées
            for item in self.combined_items:
                if item not in random_items:
                    if random.random() < add_probability:
                        unique = random.random() < unique_probability
                        new_items.append(
                            {"Item": item, "Phase": phase, "Unique": int(unique)}
                        )

        self.data_manager.update_item_bag_data(self.map_name, new_items)

    def save_items(self):
        return list(self.data_manager.get_item_bag_data(self.map_name))

    def refresh_data(self):
        """Listener protocol expected by ItemBagDataManager.notify_listeners()."""
        for phase in range(2):
            self.phase_frames[phase].listbox.delete(0, tk.END)

        for item in self.data_manager.get_item_bag_data(self.map_name):
            phase = item.get("Phase")
            if phase not in self.phase_frames:
                continue
            unique = "Unique" if item.get("Unique") else "Not Unique"
            display_text = f"{item['Item']} - {unique}"
            self.phase_frames[phase].listbox.insert(tk.END, display_text)


def load_itembag_mapdata(base_path, map_name):
    """Load bd00_ItemBag_<map>.json's entries as plain dicts, keyed by map_name.

    Delegates to jamboree_board_studio.core.items.item_bag; this wrapper
    unwraps back to the {map_name: [...]} shape this module's UI code
    expects, and keeps this function's original behavior of returning an
    empty list (with a printed message) rather than raising when the
    file is missing or invalid.
    """
    try:
        entries = parse_item_bag(base_path, map_name)
    except ItemBagParseError as error:
        print(error)
        entries = []
    return {map_name: [entry.game_data for entry in entries]}


def save_itembag_mapdata(base_path, item_bag_data, map_name):
    """Save Item Bag entries (plain dicts) via the same adapter used to load them."""
    entries = [
        ItemBagEntry(
            item=d["Item"], phase=d["Phase"], unique=bool(d["Unique"]), game_data=d
        )
        for d in item_bag_data
    ]
    serialize_item_bag(entries, base_path, map_name)
