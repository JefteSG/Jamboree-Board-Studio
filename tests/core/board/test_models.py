from jamboree_board_studio.core.board.models import Board, BoardConnection, BoardSpace


def test_board_space_defaults_do_not_invent_position():
    space = BoardSpace(id="0", type="Lucky")
    assert space.position is None
    assert space.visual_position is None
    assert space.game_data == {}


def test_board_defaults_allow_empty_spaces_and_connections():
    board = Board(id="Map01", name="Goomba Lagoon")
    assert board.spaces == []
    assert board.connections == []


def test_get_space_found_and_missing():
    board = Board(
        id="Map01",
        name="Goomba Lagoon",
        spaces=[BoardSpace(id="0", type="Lucky"), BoardSpace(id="1", type="Unlucky")],
    )
    assert board.get_space("1").type == "Unlucky"
    assert board.get_space("missing") is None


def test_connections_from_filters_by_source():
    board = Board(
        id="Map01",
        name="Goomba Lagoon",
        spaces=[BoardSpace(id=str(i), type="") for i in range(3)],
        connections=[
            BoardConnection(source="0", target="1"),
            BoardConnection(source="1", target="2"),
            BoardConnection(source="0", target="2"),
        ],
    )
    from_zero = board.connections_from("0")
    assert {(c.source, c.target) for c in from_zero} == {("0", "1"), ("0", "2")}
