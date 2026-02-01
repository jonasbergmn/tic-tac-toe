# type: ignore
from app.game import GameRoom


def test_make_move():
    room = GameRoom("test_room")
    room.game_active = True
    success, reason = room.make_move(0, 1)
    assert success is True
    assert reason is None
    assert room.board[5][0] == 1


def test_make_move_invalid_column():
    room = GameRoom("test_room")
    room.game_active = True
    success, reason = room.make_move(7, 1)
    assert success is False
    assert reason == "Invalid column."


def test_make_move_not_your_turn():
    room = GameRoom("test_room")
    room.game_active = True
    success, reason = room.make_move(0, 2)
    assert success is False
    assert reason == "Not your turn."


def test_make_move_game_not_active():
    room = GameRoom("test_room")
    success, reason = room.make_move(0, 1)
    assert success is False
    assert reason == "Game is not active."


def test_check_win_horizontal():
    room = GameRoom("test_room")
    room.board[5] = [1, 1, 1, 1, 0, 0, 0]
    assert room._check_win(5, 0) is True
    assert room._check_win(5, 1) is True
    assert room._check_win(5, 2) is True
    assert room._check_win(5, 3) is True


def test_check_win_vertical():
    room = GameRoom("test_room")
    for r in range(4):
        room.board[r + 2][0] = 1
    assert room._check_win(2, 0) is True
    assert room._check_win(3, 0) is True
    assert room._check_win(4, 0) is True
    assert room._check_win(5, 0) is True


def test_check_win_diagonal_down_right():
    room = GameRoom("test_room")
    for i in range(4):
        room.board[2 + i][0 + i] = 1
    assert room._check_win(2, 0) is True
    assert room._check_win(3, 1) is True
    assert room._check_win(4, 2) is True
    assert room._check_win(5, 3) is True


def test_check_win_diagonal_up_right():
    room = GameRoom("test_room")
    for i in range(4):
        room.board[5 - i][0 + i] = 1
    assert room._check_win(5, 0) is True
    assert room._check_win(4, 1) is True
    assert room._check_win(3, 2) is True
    assert room._check_win(2, 3) is True


def test_check_draw():
    room = GameRoom("test_room")
    room.board = [[1] * 7 for _ in range(6)]
    assert room._check_draw() is True
