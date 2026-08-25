"""2D canvas widget rendering a Board's spaces and connections.

Extracted from the drawing/interaction logic of
``editor_modules.map_layout.MapLayoutEditor`` (pan/zoom/click-select over
a matplotlib figure embedded in Tk), but rendering from the
format-independent ``Board`` model instead of a raw game-data dict.
Colors and the "editable type" list are reused directly from
``editor_modules.map_layout`` rather than duplicated.

This widget never invents a space's position: it only draws a space that
already has a ``visual_position`` (computed by
``jamboree_board_studio.core.board.layout``, itself derived from known
path data — see ``docs/research/board-format.md``). Spaces with no
inferable position are listed but not plotted, rather than being placed
at a guessed location.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patheffects
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Circle, FancyArrowPatch, Polygon

from editor_modules.map_layout import mass_attr_colors
from jamboree_board_studio.core.board.layout import apply_visual_positions
from jamboree_board_studio.core.board.models import Board, BoardSpace

_DEFAULT_COLOR = "gray"
_SELECTED_EDGE_COLOR = "white"
_SELECTED_LINEWIDTH = 2.5


class BoardCanvas(ttk.Frame):
    """Renders a ``Board``'s spaces/connections; reports clicks via ``on_select``."""

    def __init__(self, parent, on_select=None):
        super().__init__(parent)
        self.on_select = on_select
        self.board: Board | None = None
        self.selected_space_id: str | None = None
        self._node_patches: dict[str, object] = {}

        self.fig, self.ax = plt.subplots(figsize=(6, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True)
        self.canvas_widget.config(bd=2, relief="solid", highlightbackground="black")

        self.status_label = ttk.Label(self, text="")
        self.status_label.pack(side="bottom", fill="x", padx=4, pady=2)

        self.fig.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.fig.canvas.mpl_connect("button_press_event", self._on_click)
        self.canvas_widget.bind("<Left>", lambda e: self._pan(dx=-0.5))
        self.canvas_widget.bind("<Right>", lambda e: self._pan(dx=0.5))
        self.canvas_widget.bind("<Up>", lambda e: self._pan(dy=0.5))
        self.canvas_widget.bind("<Down>", lambda e: self._pan(dy=-0.5))

    def load_board(self, board: Board, reverse_x: bool = False, reverse_y: bool = False) -> None:
        self.board = board
        apply_visual_positions(board, reverse_x=reverse_x, reverse_y=reverse_y)
        self.selected_space_id = None
        self._redraw(fit_view=True)

    def select_space(self, space_id: str | None) -> None:
        """Programmatically select (and redraw to highlight) a space, without firing on_select."""
        self.selected_space_id = space_id
        self._redraw(fit_view=False)

    def _redraw(self, fit_view: bool) -> None:
        prev_xlim, prev_ylim = self.ax.get_xlim(), self.ax.get_ylim()
        self.ax.clear()
        self._node_patches = {}

        if not self.board:
            self.canvas.draw()
            return

        positioned = [s for s in self.board.spaces if s.visual_position is not None]
        missing_count = len(self.board.spaces) - len(positioned)

        for connection in self.board.connections:
            source = self.board.get_space(connection.source)
            target = self.board.get_space(connection.target)
            if not source or not target:
                continue
            if source.visual_position is None or target.visual_position is None:
                continue
            arrow = FancyArrowPatch(
                source.visual_position,
                target.visual_position,
                arrowstyle="->",
                mutation_scale=15,
                color="black",
            )
            arrow.set_path_effects(
                [patheffects.withStroke(linewidth=2, alpha=0, foreground="black")]
            )
            self.ax.add_patch(arrow)

        for space in positioned:
            patch = self._make_patch(space)
            self.ax.add_patch(patch)
            self._node_patches[space.id] = patch

        if fit_view and positioned:
            xs = [s.visual_position[0] for s in positioned]
            ys = [s.visual_position[1] for s in positioned]
            margin = 0.5
            self.ax.set_xlim(min(xs) - margin, max(xs) + margin)
            self.ax.set_ylim(min(ys) - margin, max(ys) + margin)
        else:
            self.ax.set_xlim(prev_xlim)
            self.ax.set_ylim(prev_ylim)

        self.ax.set_aspect("equal", adjustable="box")
        self.ax.axis("off")
        self.canvas.draw()

        status = f"{len(positioned)} space(s) shown"
        if missing_count:
            status += f" | {missing_count} space(s) have no known position (not drawn)"
        self.status_label.config(text=status)

    def _make_patch(self, space: BoardSpace):
        x, y = space.visual_position
        color = mass_attr_colors.get(space.type, _DEFAULT_COLOR)
        is_selected = space.id == self.selected_space_id
        edge_color = _SELECTED_EDGE_COLOR if is_selected else "none"
        linewidth = _SELECTED_LINEWIDTH if is_selected else 0
        npc_linked = space.game_data.get("NpcNodeNo0", -1) != -1

        if npc_linked:
            return Polygon(
                np.column_stack(
                    [
                        x + 0.3 * np.cos(np.linspace(0, 2 * np.pi, 4, endpoint=False)),
                        y + 0.3 * np.sin(np.linspace(0, 2 * np.pi, 4, endpoint=False)),
                    ]
                ),
                facecolor=color,
                alpha=0.7,
                edgecolor=edge_color,
                linewidth=linewidth,
            )
        return Circle(
            (x, y),
            0.3 if space.type else 0.12,
            facecolor=color,
            alpha=0.7,
            edgecolor=edge_color,
            linewidth=linewidth,
        )

    def _on_scroll(self, event) -> None:
        scale = 1.1 if event.button == "down" else 0.9
        xlim, ylim = self.ax.get_xlim(), self.ax.get_ylim()
        self.ax.set_xlim(xlim[0] * scale, xlim[1] * scale)
        self.ax.set_ylim(ylim[0] * scale, ylim[1] * scale)
        self.canvas.draw()

    def _pan(self, dx: float = 0, dy: float = 0) -> None:
        xlim, ylim = self.ax.get_xlim(), self.ax.get_ylim()
        self.ax.set_xlim(xlim[0] + dx, xlim[1] + dx)
        self.ax.set_ylim(ylim[0] + dy, ylim[1] + dy)
        self.canvas.draw()

    def _on_click(self, event) -> None:
        if event.inaxes != self.ax or not self.board:
            return
        for space_id, patch in self._node_patches.items():
            if patch.contains(event)[0]:
                self.selected_space_id = space_id
                self._redraw(fit_view=False)
                if self.on_select:
                    space = self.board.get_space(space_id)
                    if space:
                        self.on_select(space)
                return
