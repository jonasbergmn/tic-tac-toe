from app.lobby import Lobby


def test_create_room():
    lobby = Lobby()
    room = lobby.create_room("test_room")
    assert room.room_id == "test_room"
    assert lobby.get_room("test_room") == room


def test_get_room():
    lobby = Lobby()
    lobby.create_room("test_room")
    room = lobby.get_room("test_room")
    assert room is not None
    assert room.room_id == "test_room"


def test_get_non_existent_room():
    lobby = Lobby()
    room = lobby.get_room("non_existent_room")
    assert room is None


def test_get_rooms_info():
    lobby = Lobby()
    lobby.create_room("room_1")
    lobby.create_room("room_2")
    rooms_info = lobby.get_rooms_info()
    assert len(rooms_info) == 2
    assert rooms_info[0]["room_id"] == "room_1"
    assert rooms_info[1]["room_id"] == "room_2"
    assert rooms_info[0]["players"] == 0
    assert rooms_info[1]["players"] == 0
    assert rooms_info[0]["is_full"] is False
    assert rooms_info[1]["is_full"] is False
