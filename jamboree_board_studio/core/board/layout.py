"""Presentation-only visual layout computation for boards.

This is *not* game data. It computes a 2D position per space purely for
on-screen display, using the same technique the legacy Map Layout viewer
already used (``jamboree_board_studio.legacy.editor_modules.map_layout.MapLayoutEditor.draw_map``):
inferring a node's position from the first Bezier control point of the
first path segment that touches it (first-touch wins, X/Z only, no
height). This is an approximation of unknown accuracy — see
``docs/research/board-format.md`` — so results are only ever written to
``BoardSpace.visual_position``, never back into ``game_data``.

Kept dependency-free from Tkinter/matplotlib like the rest of
``core.board``, and kept free of the *rendering* concern (colors, node
shapes) — this module only computes numbers.
"""

from __future__ import annotations

from jamboree_board_studio.core.board.models import Board


def compute_visual_positions(
    board: Board, reverse_x: bool = False, reverse_y: bool = False
) -> dict[str, tuple[float, float]]:
    """Infer a 2D (x, z) position per space id from connection Bezier data.

    Mirrors the legacy computation exactly, including its ``* 0.5`` scale
    factor and first-touch-wins behavior, so results match what the
    existing Map Layout viewer has always shown for the same data.
    """
    positions: dict[str, tuple[float, float]] = {}

    def place(node_id: str, x: float, z: float) -> None:
        if node_id in positions:
            return
        positions[node_id] = (-x if reverse_x else x, -z if reverse_y else z)

    for connection in board.connections:
        bezier_points = connection.game_data.get("Bezier") or []
        if not bezier_points:
            continue
        point = bezier_points[0]
        if "Position0X" in point and "Position0Z" in point:
            place(connection.source, point["Position0X"] * 0.5, point["Position0Z"] * 0.5)
        if "Position1X" in point and "Position1Z" in point:
            place(connection.target, point["Position1X"] * 0.5, point["Position1Z"] * 0.5)

    return positions


def apply_visual_positions(
    board: Board, reverse_x: bool = False, reverse_y: bool = False
) -> None:
    """Compute and assign ``visual_position`` on each of the board's spaces, in place.

    Spaces that no connection touches are left with ``visual_position =
    None`` — no guessed fallback position is invented for them.
    """
    positions = compute_visual_positions(board, reverse_x=reverse_x, reverse_y=reverse_y)
    for space in board.spaces:
        space.visual_position = positions.get(space.id)
