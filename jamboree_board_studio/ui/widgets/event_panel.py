"""Events panel in board vocabulary (Lucky/Unlucky/KoopaMass in one
table, not three separate tabs).

Unlike Item Bag/Item Mass/Item Shop, EventDataManager already had a
fully live shared model before this panel existed -- every EventEditor
(Lucky, Unlucky, KoopaMass) reads and writes through it on every
add/remove/randomize, and it owns both the KoopaMass cross-map broadcast
(``sync_with_linked_maps``, shared by all boards except Map06) and the
save gate (``get_events_status()``, which blocks the *entire app's* save
if any pool's rates sum to zero). This panel is just another registered
view over that same manager, like the legacy widgets already are --
``update_event_listbox()`` is the listener callback name
EventDataManager.notify_listeners() expects, not ``refresh_data()`` like
the other panels' managers use.

Scope for this first pass: view and edit existing entries (rates,
result) across all three pools for one map. Add/remove still happens on
the original "Lucky"/"Unlucky"/"KoopaMass" tabs. Editing a KoopaMass
entry here goes through sync_with_linked_maps() exactly like the legacy
widget's own edits do, so it broadcasts to every other (non-Map06) map
the same way.
"""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk

from jamboree_board_studio.legacy.editor_modules.events import result_options

_POOLS = ("LuckyMass", "UnluckyMass", "KoopaMass")
_POOL_LABELS = {"LuckyMass": "Lucky", "UnluckyMass": "Unlucky", "KoopaMass": "KoopaMass"}
_RATE_KEYS = ("Rate0", "Rate1", "Rate2", "Rate3")


class EventPanel(ttk.Frame):
    def __init__(self, parent, map_name: str, data_manager):
        super().__init__(parent)
        self.map_name = map_name
        self.data_manager = data_manager
        self.entries: list[tuple[str, dict]] = []
        self.selected: tuple[str, dict] | None = None

        # Per-pool result option lists, mirroring EventEditor's own
        # per-map LuckyMass additions (Map02/Map06 get "Key", Map03 gets
        # "Roulette").
        self.result_options: dict[str, list[str]] = {}
        for data_type in _POOLS:
            options = result_options.get(data_type, [])[:]
            if data_type == "LuckyMass":
                if self.map_name in ("Map02", "Map06"):
                    options.append("Key")
                if self.map_name == "Map03":
                    options.append("Roulette")
            self.result_options[data_type] = options

        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        table_frame = ttk.Frame(self)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ttk.Label(table_frame, text="Events", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(0, 4)
        )

        tree_container = ttk.Frame(table_frame)
        tree_container.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(
            tree_container,
            columns=("pool", "rate0", "rate1", "rate2", "rate3", "result"),
            show="headings",
            selectmode="browse",
        )
        for col, label, width in (
            ("pool", "Pool", 80),
            ("rate0", "Rate0", 55),
            ("rate1", "Rate1", 55),
            ("rate2", "Rate2", 55),
            ("rate3", "Rate3", 55),
            ("result", "Result", 110),
        ):
            self.tree.heading(col, text=label)
            self.tree.column(
                col, width=width, anchor="center" if col != "result" else "w",
                stretch=col == "result",
            )

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        note = ttk.Label(
            table_frame,
            text="Add/remove events on the “Lucky”/“Unlucky”/“KoopaMass” tabs; "
            "edit existing ones here.",
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

        self.rate_spinboxes: dict[str, tk.Spinbox] = {}
        for rate_key in _RATE_KEYS:
            rate_frame = ttk.Frame(inspector_frame)
            rate_frame.pack(fill="x", pady=2)
            ttk.Label(rate_frame, text=rate_key).pack(side="left")
            spinbox = tk.Spinbox(rate_frame, from_=0, to=999, width=16, state="disabled")
            spinbox.pack(side="right")
            self.rate_spinboxes[rate_key] = spinbox

        result_frame = ttk.Frame(inspector_frame)
        result_frame.pack(fill="x", pady=2)
        ttk.Label(result_frame, text="Result").pack(side="left")
        self.result_combobox = ttk.Combobox(result_frame, state="disabled", width=14)
        self.result_combobox.pack(side="right")

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
        self.update_event_listbox()

    def update_event_listbox(self) -> None:
        """Listener protocol expected by EventDataManager.notify_listeners()
        -- named to match what every EventEditor already implements, not
        ``refresh_data()`` like the other panels' managers use.
        """
        selected_id = id(self.selected[1]) if self.selected else None

        self.entries = [
            (data_type, entry)
            for data_type in _POOLS
            for entry in self.data_manager.get_event_data(self.map_name, data_type)
        ]

        self.tree.delete(*self.tree.get_children())
        row_to_select = None
        for index, (data_type, entry) in enumerate(self.entries):
            row_id = self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    _POOL_LABELS[data_type],
                    entry.get("Rate0"),
                    entry.get("Rate1"),
                    entry.get("Rate2"),
                    entry.get("Rate3"),
                    entry.get("Result"),
                ),
            )
            if id(entry) == selected_id:
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

    def _show_entry(self, selected: tuple[str, dict] | None) -> None:
        self.selected = selected
        if selected is None:
            self.title_label.config(text="Nothing selected")
            for spinbox in self.rate_spinboxes.values():
                spinbox.config(state="disabled")
                spinbox.delete(0, "end")
            self.result_combobox.config(state="disabled", values=[])
            self.result_combobox.set("")
            self.apply_button.config(state="disabled")
            self._set_raw_text("")
            return

        data_type, entry = selected
        self.title_label.config(text=f"{_POOL_LABELS[data_type]} – {entry.get('Result', '')}")
        for rate_key, spinbox in self.rate_spinboxes.items():
            spinbox.config(state="normal")
            spinbox.delete(0, "end")
            spinbox.insert(0, str(entry.get(rate_key, 0)))
        self.result_combobox.config(state="readonly", values=self.result_options[data_type])
        self.result_combobox.set(entry.get("Result", ""))
        self.apply_button.config(state="normal")
        self._set_raw_text(json.dumps(entry, indent=2, ensure_ascii=False))

    def _set_raw_text(self, text: str) -> None:
        self.raw_text.config(state="normal")
        self.raw_text.delete("1.0", tk.END)
        self.raw_text.insert("1.0", text)
        self.raw_text.config(state="disabled")

    def _apply(self) -> None:
        if not self.selected:
            return
        data_type, entry = self.selected

        try:
            rates = {key: float(self.rate_spinboxes[key].get()) for key in _RATE_KEYS}
        except ValueError:
            return
        result = self.result_combobox.get()
        if not result:
            return

        entry.update(rates)
        entry["Result"] = result

        # Same two calls every EventEditor mutation makes (add/remove/
        # randomize): update_event_data() writes the (already-mutated,
        # same-object) list back, and sync_with_linked_maps() broadcasts
        # a redraw to every registered listener -- including every
        # "Lucky"/"Unlucky"/"KoopaMass" tab, which each recompute their
        # own rate-status gate as a side effect -- and, for KoopaMass on
        # a non-Map06 map, propagates the data itself to every linked map.
        current = self.data_manager.get_event_data(self.map_name, data_type)
        self.data_manager.update_event_data(self.map_name, data_type, current)
        self.data_manager.sync_with_linked_maps(self.map_name, data_type)
