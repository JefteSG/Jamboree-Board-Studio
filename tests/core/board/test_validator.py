from jamboree_board_studio.core.board.models import Board, BoardConnection, BoardSpace
from jamboree_board_studio.core.board.validator import is_valid, validate_board


def test_valid_board_has_no_issues():
    board = Board(
        id="Map01",
        name="Goomba Lagoon",
        spaces=[BoardSpace(id="0", type="Lucky"), BoardSpace(id="1", type="Unlucky")],
        connections=[BoardConnection(source="0", target="1")],
    )
    assert validate_board(board) == []
    assert is_valid(board)


def test_duplicate_space_id_is_an_error():
    board = Board(
        id="Map01",
        name="Goomba Lagoon",
        spaces=[BoardSpace(id="0", type="Lucky"), BoardSpace(id="0", type="Unlucky")],
    )
    issues = validate_board(board)
    assert any("Duplicate space id" in issue.message for issue in issues)
    assert not is_valid(board)


def test_dangling_connection_target_is_an_error():
    board = Board(
        id="Map01",
        name="Goomba Lagoon",
        spaces=[BoardSpace(id="0", type="Lucky")],
        connections=[BoardConnection(source="0", target="99")],
    )
    issues = validate_board(board)
    assert any("unknown target space" in issue.message for issue in issues)
    assert not is_valid(board)


def test_dangling_connection_source_is_an_error():
    board = Board(
        id="Map01",
        name="Goomba Lagoon",
        spaces=[BoardSpace(id="0", type="Lucky")],
        connections=[BoardConnection(source="99", target="0")],
    )
    issues = validate_board(board)
    assert any("unknown source space" in issue.message for issue in issues)
    assert not is_valid(board)
