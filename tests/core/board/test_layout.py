from jamboree_board_studio.core.board.layout import (
    apply_visual_positions,
    compute_visual_positions,
)
from jamboree_board_studio.core.board.models import Board, BoardConnection, BoardSpace


def _segment(x0, z0, x1, z1):
    return {"Bezier": [{"Position0X": x0, "Position0Z": z0, "Position1X": x1, "Position1Z": z1}]}


def test_compute_visual_positions_uses_first_touch_and_half_scale():
    board = Board(
        id="Map01",
        name="Map01",
        spaces=[BoardSpace(id="0", type=""), BoardSpace(id="1", type="")],
        connections=[BoardConnection(source="0", target="1", game_data=_segment(0.0, 0.0, 2.0, 4.0))],
    )

    positions = compute_visual_positions(board)

    assert positions["0"] == (0.0, 0.0)
    assert positions["1"] == (1.0, 2.0)


def test_compute_visual_positions_ignores_connections_without_bezier():
    board = Board(
        id="Map01",
        name="Map01",
        spaces=[BoardSpace(id="0", type="")],
        connections=[BoardConnection(source="0", target="1", game_data={})],
    )

    positions = compute_visual_positions(board)

    assert positions == {}


def test_compute_visual_positions_applies_reverse_flags():
    board = Board(
        id="Map01",
        name="Map01",
        spaces=[BoardSpace(id="0", type="")],
        connections=[BoardConnection(source="0", target="1", game_data=_segment(2.0, 4.0, 0.0, 0.0))],
    )

    positions = compute_visual_positions(board, reverse_x=True, reverse_y=True)

    assert positions["0"] == (-1.0, -2.0)


def test_apply_visual_positions_leaves_untouched_spaces_as_none():
    board = Board(
        id="Map01",
        name="Map01",
        spaces=[BoardSpace(id="0", type=""), BoardSpace(id="orphan", type="")],
        connections=[BoardConnection(source="0", target="0", game_data=_segment(0.0, 0.0, 0.0, 0.0))],
    )

    apply_visual_positions(board)

    assert board.get_space("0").visual_position == (0.0, 0.0)
    assert board.get_space("orphan").visual_position is None


def test_apply_visual_positions_never_writes_to_game_data():
    board = Board(
        id="Map01",
        name="Map01",
        spaces=[BoardSpace(id="0", type="", game_data={"NodeNo": 0})],
        connections=[BoardConnection(source="0", target="1", game_data=_segment(1.0, 1.0, 2.0, 2.0))],
    )

    apply_visual_positions(board)

    assert board.get_space("0").game_data == {"NodeNo": 0}
    assert board.get_space("0").position is None
