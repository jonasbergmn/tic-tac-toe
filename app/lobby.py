import uuid
from typing import Any, Dict, List, Optional

from .game import GameRoom


class Lobby:
    """Manages game rooms."""

    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}

    def create_room(self, room_id: Optional[str] = None) -> GameRoom:
        """Creates a new game room and adds it to the lobby."""
        if not room_id:
            room_id = str(uuid.uuid4())
        room = GameRoom(room_id)
        self.rooms[room_id] = room
        return room

    def get_room(self, room_id: str) -> Optional[GameRoom]:
        """Gets a game room by its ID."""
        return self.rooms.get(room_id)

    def get_rooms_info(self) -> List[Dict[str, Any]]:
        """Gets information about all rooms in the lobby."""
        return [
            {
                "room_id": room_id,
                "players": len(room.manager.active_connections),
                "is_full": len(room.manager.active_connections) >= 2,
            }
            for room_id, room in self.rooms.items()
        ]
