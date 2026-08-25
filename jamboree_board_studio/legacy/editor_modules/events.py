import random
import tkinter as tk
from tkinter import ttk

from jamboree_board_studio.core.events import (
    EventEntry,
    EventParseError,
    parse_events,
    serialize_events,
)

result_options = {
    "LuckyMass": [
        "7Coin",
        "10Coin",
        "12Coin",
        "15Coin",
        "20Coin",
        "10CoinTakeMass",
        "DoubleDice",
        "WarpBox",
        "JustDice",
        "NormalDokan",
        "ItemBag",
        "WanwanWhistle",
        "Kinoko",
        "ManyKinoko",
        "SlowKinoko",
        "ChangeBox",
        "TripleDice",
    ],
    "UnluckyMass": [
        "Rob3Coin",
        "Rob5Coin",
        "Rob7Coin",
        "Give3Coin",
        "Give5Coin",
        "Give7Coin",
        "GetStone",
        "GiveItem",
    ],
    "KoopaMass": [
        "Rob10Coin",
        "Rob15Coin",
        "Rob20Coin",
        "Rob30Coin",
        "RobHalfCoin",
        "Rob10CoinAll",
        "Revolution",
        "Shuffle",
        "Rob1Star",
        "Get100Star",
        "Get1000Coin",
    ],
}


class EventDataManager:
    def __init__(self):
        self.event_status = {}
        self.event_data = {}
        self.listeners = []

    def register_listener(self, listener):
        self.listeners.append(listener)

    def get_event_data(self, map_name, data_type):
        if map_name in self.event_data and data_type in self.event_data[map_name]:
            return self.event_data[map_name][data_type]
        else:
            return []

    def get_events_status(self):
        status = True
        for map_name, map_data in self.event_status.items():
            if (
                not map_data["LuckyMass"]
                or not map_data["UnluckyMass"]
                or not map_data["KoopaMass"]
            ):
                status = False
        return status

    def update_event_data(self, map_name, data_type, event_data):
        if map_name not in self.event_data:
            self.event_data[map_name] = {}
        self.event_data[map_name][data_type] = event_data

    def update_event_status(self, map_name, data_type, status):
        if map_name not in self.event_status:
            self.event_status[map_name] = {}
        self.event_status[map_name][data_type] = status

    def sync_with_linked_maps(self, map_name, data_type):
        if data_type == "KoopaMass" and map_name != "Map06":
            linked_maps = self.get_linked_maps(map_name)
            current_data = self.event_data.get(map_name, {}).get(data_type, [])

            for linked_map in linked_maps:
                if linked_map not in self.event_data:
                    self.event_data[linked_map] = {}
                self.event_data[linked_map][data_type] = current_data
        # Broadcast a redraw regardless of data_type/map_name (not just
        # the KoopaMass cross-map case above): every EventEditor now
        # registers as a listener (see __init__), so this is what makes
        # a Lucky/Unlucky/KoopaMass edit from any single view -- the
        # legacy widget or the new Events preview panel -- show up
        # everywhere else that reads the same (map_name, data_type) pool,
        # including each listener's own rate-status recalculation.
        self.notify_listeners()

    def get_linked_maps(self, map_name):
        linked_maps = []
        if map_name.startswith("Map"):
            map_number = int(map_name[3:])
            if map_number != 6:
                linked_maps = [
                    f"Map{n:02d}" for n in range(1, 8) if n != 6 and n != map_number
                ]
        return linked_maps

    def notify_listeners(self):
        for listener in self.listeners:
            listener.update_event_listbox()


class EventEditor:
    def __init__(self, parent, data_type, map_name, app_width, event_data_manager):
        self.event_data_manager = event_data_manager
        self.rates_totals = {"Rate0": 0.0, "Rate1": 0.0, "Rate2": 0.0, "Rate3": 0.0}
        self.map_name = map_name.replace(" ", "_")
        self.data_type = data_type
        self.result_options = result_options.get(self.data_type, [])[:]
        
        if self.data_type == "LuckyMass":
            if self.map_name == "Map02" or self.map_name == "Map06":
                self.result_options.append("Key")
            if self.map_name == "Map03":
                self.result_options.append("Roulette")
            

        self.frame = ttk.Frame(parent)
        self.frame.pack(
            side="left",
            padx=(app_width * 0.05, app_width * 0.05 // 2),
            pady=10,
            fill="both",
            expand=True,
        )

        self.entries = {}
        self.create_ui(app_width)

        # Every editor is a listener now (not just KoopaMass on non-Map06
        # maps, as before): sync_with_linked_maps() always broadcasts,
        # and update_event_listbox() only ever touches this instance's
        # own (map_name, data_type) pool, so a broadcast from an
        # unrelated pool/map is a harmless no-op redraw here. This is
        # what lets the new Events preview panel's edits show up in this
        # widget automatically.
        event_data_manager.register_listener(self)

    def create_ui(self, app_width):
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(5, weight=1)

        self.cumul_frame = ttk.LabelFrame(
            self.frame, text="Rate Status", width=app_width
        )
        self.cumul_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.rate_labels = {}
        for i, rate in enumerate(["Rate0", "Rate1", "Rate2", "Rate3"]):
            label = ttk.Label(self.cumul_frame, text=f"{rate}")
            label.grid(row=i, column=0, padx=5, pady=5, sticky="w")
            self.rate_labels[rate] = label

        entry_frame = ttk.LabelFrame(
            self.frame, text="Add Event Entry", width=app_width
        )
        entry_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        entry_frame.grid_columnconfigure(1, weight=1)

        labels = ["Rate0", "Rate1", "Rate2", "Rate3"]
        self.entries = {}
        for i, label in enumerate(labels):
            ttk.Label(entry_frame, text=label).grid(
                row=i, column=0, padx=5, pady=5, sticky="w"
            )
            entry = tk.Spinbox(entry_frame, from_=0, to=999)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
            self.entries[label] = entry

        ttk.Label(entry_frame, text="Result").grid(
            row=4, column=0, padx=5, pady=5, sticky="w"
        )

        if self.result_options:
            self.result_combobox = ttk.Combobox(
                entry_frame, values=self.result_options, width=15
            )
        else:
            self.result_combobox = ttk.Combobox(
                entry_frame, values=["No options available"], width=15
            )

        self.result_combobox.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        add_button = ttk.Button(
            self.frame, text="Add Entry", command=self.add_event_entry
        )
        add_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.listbox = tk.Listbox(self.frame, height=10, width=50)
        self.listbox.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

        self.remove_button = ttk.Button(
            self.frame, text="Remove Selected", command=self.remove_event_entry
        )
        self.remove_button.grid(row=4, column=0, padx=10, pady=10, sticky="ew")

    def load_event_data(self, data):
        self.event_data_manager.update_event_data(self.map_name, self.data_type, data)
        self.update_event_listbox()
        # Unlike add/remove/randomize, this never went through
        # sync_with_linked_maps() (no need to -- each map's own file read
        # already gets it the correct, already-shared KoopaMass data), so
        # it never broadcast to other listeners either. Now that every
        # editor (and the Events preview panel) is a listener, an
        # explicit notify here is what lets the panel actually see data
        # loaded before it existed, instead of staying empty until the
        # first edit.
        self.event_data_manager.notify_listeners()
    
    def randomize_event_data(self): # randomize les entrées a partir de la variable result_options et du self.data_type, les rates ne peuvent pas etre a 0 et ne peuvent pas dépasser 100 chaque rate ne peut pas dépasser un certain pourcentage de l'espace disponible, chaque rate est indépendante des autres
        rate0 = 0
        rate1 = 0
        rate2 = 0
        rate3 = 0
        entries = random.sample(self.result_options, 8)
        self.current_data = []
        while entries:
            entry = entries.pop(random.randrange(len(entries)))
            new_entry = {
                "Rate0": random.randint(0, (100 - rate0) // 3),
                "Rate1": random.randint(0, (100 - rate1) // 3),
                "Rate2": random.randint(0, (100 - rate2) // 3),
                "Rate3": random.randint(0, (100 - rate3) // 3),
                "Result": entry,
            }
            self.current_data.append(new_entry)
            rate0 += new_entry["Rate0"]
            rate1 += new_entry["Rate1"]
            rate2 += new_entry["Rate2"]
            rate3 += new_entry["Rate3"]

        self.event_data_manager.update_event_data(
            self.map_name, self.data_type, self.current_data
        )

        self.event_data_manager.sync_with_linked_maps(self.map_name, self.data_type)

        self.recalculate_totals()
        self.update_event_listbox()   

    def update_event_listbox(self):
        self.current_data = self.event_data_manager.get_event_data(
            self.map_name, self.data_type
        )
        self.listbox.delete(0, tk.END)

        self.recalculate_totals()

        for entry in self.current_data:
            display_text = f"Rate0: {str(float(entry['Rate0'])).split('.')[0].rjust(3, '\u2007')}.{str(float(entry['Rate0'])).split('.')[1].ljust(3, '\u2007')}\t Rate1: {str(float(entry['Rate1'])).split('.')[0].rjust(3, '\u2007')}.{str(float(entry['Rate1'])).split('.')[1].ljust(3, '\u2007')}\t Rate2: {str(float(entry['Rate2'])).split('.')[0].rjust(3, '\u2007')}.{str(float(entry['Rate2'])).split('.')[1].ljust(3, '\u2007')}\t Rate3: {str(float(entry['Rate3'])).split('.')[0].rjust(3, '\u2007')}.{str(float(entry['Rate3'])).split('.')[1].ljust(3, '\u2007')}\t | {entry['Result']}"
            self.listbox.insert(tk.END, display_text)

        for rate, total in self.rates_totals.items():
            color = "green" if total != 0 else "red"
            self.rate_labels[rate].config(text=f"{rate}: {total}", foreground=color)

        if (
            self.rates_totals["Rate0"] == 0
            or self.rates_totals["Rate1"] == 0
            or self.rates_totals["Rate2"] == 0
            or self.rates_totals["Rate3"] == 0
        ):
            self.event_data_manager.update_event_status(
                self.map_name, self.data_type, False
            )
        else:
            self.event_data_manager.update_event_status(
                self.map_name, self.data_type, True
            )

    def recalculate_totals(self):
        self.rates_totals = {"Rate0": 0.0, "Rate1": 0.0, "Rate2": 0.0, "Rate3": 0.0}

        for entry in self.current_data:
            for rate in self.rates_totals:
                self.rates_totals[rate] += entry[rate]

    def add_event_entry(self):
        try:
            rate0 = float(self.entries["Rate0"].get())
            rate1 = float(self.entries["Rate1"].get())
            rate2 = float(self.entries["Rate2"].get())
            rate3 = float(self.entries["Rate3"].get())
            result = self.result_combobox.get()
            new_entry = {
                "Rate0": rate0,
                "Rate1": rate1,
                "Rate2": rate2,
                "Rate3": rate3,
                "Result": result,
            }
            self.current_data.append(new_entry)

            self.event_data_manager.update_event_data(
                self.map_name, self.data_type, self.current_data
            )

            self.event_data_manager.sync_with_linked_maps(self.map_name, self.data_type)

            self.recalculate_totals()
            self.update_event_listbox()

        except ValueError as e:
            print(f"Error: {e}")
            
        
    def remove_event_entry(self):
        try:
            selected_index = self.listbox.curselection()[0]
            self.current_data.pop(selected_index)

            self.event_data_manager.update_event_data(
                self.map_name, self.data_type, self.current_data
            )
            self.event_data_manager.sync_with_linked_maps(self.map_name, self.data_type)

            self.recalculate_totals()
            self.update_event_listbox()

        except IndexError:
            print("No item selected for removal.")


def load_event_mapdata(base_path, map_name, data_type):
    """Load LuckyMass/UnluckyMass/KoopaMass entries as plain dicts.

    Delegates to jamboree_board_studio.core.events, which does the
    actual parsing (including the KoopaMass -> shared Map00 file
    remapping); this wrapper just unwraps back to the plain
    list-of-dicts shape this module's UI code expects, and keeps this
    function's original behavior of returning [] (with a printed
    message) rather than raising when the file is missing or invalid.
    """
    try:
        entries = parse_events(base_path, map_name, data_type)
    except EventParseError as error:
        print(error)
        return []
    return [entry.game_data for entry in entries]


def save_event_mapdata(base_path, event_data, map_name, data_type):
    """Save event entries (plain dicts) via the same adapter used to load them."""
    entries = [
        EventEntry(
            rate0=d["Rate0"],
            rate1=d["Rate1"],
            rate2=d["Rate2"],
            rate3=d["Rate3"],
            result=d["Result"],
            game_data=d,
        )
        for d in event_data
    ]
    serialize_events(entries, base_path, map_name, data_type)
