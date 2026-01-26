from typing import Any, List, Optional, Tuple, Union, Callable

from fastapi import WebSocket

from config import COLS, ROWS


class ConnectionManager:
    """Manages WebSocket connections for a game room."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    def add_connection(self, websocket: WebSocket):
        """Adds a new WebSocket connection."""
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Removes a WebSocket connection."""
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        """Sends a message to all connected clients."""
        for connection in self.active_connections:
            await connection.send_json(message)

    async def broadcast_game_state(
        self,
        game_state_provider: Callable[..., dict[str, Any]],
        player_provider: Callable[..., int | None],
    ):
        """Sends the current game state to all connected clients."""
        for _, connection in enumerate(self.active_connections):
            player_num = player_provider(connection)
            await connection.send_json(game_state_provider(player_num))


class GameRoom:
    """Represents the state and logic of a Connect 4 game room."""

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.board: List[List[int]] = []
        self.current_player: int = 1
        self.game_active: bool = False
        self.game_ready: bool = False
        self.winner: Optional[Union[int, str]] = None
        self.draw: bool = False
        self.manager = ConnectionManager()
        self.initialize_game()

    def initialize_game(self):
        """Resets the game state to the initial state."""
        self.board = [[0] * COLS for _ in range(ROWS)]
        self.current_player = 1
        self.game_active = False
        self.game_ready = False
        self.winner = None
        self.draw = False
        if len(self.manager.active_connections) == 2:
            self.game_active = True
            self.game_ready = True

    def add_player(self, websocket: WebSocket) -> bool:
        """Adds a player to the game if there is space."""
        if len(self.manager.active_connections) >= 2:
            return False
        self.manager.add_connection(websocket)
        # When first player joins, reset the game
        if len(self.manager.active_connections) == 1:
            self.initialize_game()
        elif len(self.manager.active_connections) == 2:
            self.game_active = True
            self.game_ready = True
        return True

    def remove_player(self, websocket: WebSocket):
        """Removes a player from the game and handles disconnection logic."""
        try:
            self.manager.disconnect(websocket)
            if self.manager.active_connections:
                self.game_active = False
                self.winner = "Opponent disconnected"
                self.initialize_game()
            else:
                self.initialize_game()
        except ValueError:
            pass

    def get_player_num(self, websocket: WebSocket) -> Optional[int]:
        """Gets the player number for a given websocket."""
        try:
            return self.manager.active_connections.index(websocket) + 1
        except ValueError:
            return None

    def get_state(self, player_num: int) -> dict[str, Any]:
        """Gets the game state from the perspective of a specific player."""
        return {
            "board": self.board,
            "currentPlayer": self.current_player,
            "gameActive": self.game_active,
            "gameReady": self.game_ready,
            "winner": self.winner,
            "draw": self.draw,
            "playerNum": player_num,
        }

    def make_move(self, col: int, player_num: int) -> Tuple[bool, Optional[str]]:
        """Attempts to make a move for a player."""
        if not self.game_active:
            return False, "Game is not active."
        if self.current_player != player_num:
            return False, "Not your turn."
        if not (0 <= col < COLS and self.board[0][col] == 0):
            return False, "Invalid column."

        for r in range(ROWS - 1, -1, -1):
            if self.board[r][col] == 0:
                self.board[r][col] = player_num
                if self._check_win(r, col):
                    self.game_active = False
                    self.winner = player_num
                elif self._check_draw():
                    self.game_active = False
                    self.draw = True
                else:
                    self.current_player = 2 if player_num == 1 else 1
                return True, None
        return False, "Column is full."

    def _check_win(self, row: int, col: int) -> bool:
        """Check for a win condition more efficiently around the last move."""
        player = self.board[row][col]
        if player == 0:
            return False

        return (
            self._check_horizontal(row, player)
            or self._check_vertical(col, player)
            or self._check_diagonal_main(row, col, player)
            or self._check_diagonal_anti(row, col, player)
        )

    def _check_horizontal(self, row: int, player: int) -> bool:
        """Check for a horizontal win (4 in a row)."""
        count = 0
        for c in range(COLS):
            count = count + 1 if self.board[row][c] == player else 0
            if count >= 4:
                return True
        return False

    def _check_vertical(self, col: int, player: int) -> bool:
        """Check for a vertical win (4 in a column)."""
        count = 0
        for r in range(ROWS):
            count = count + 1 if self.board[r][col] == player else 0
            if count >= 4:
                return True
        return False

    def _check_diagonal_main(self, row: int, col: int, player: int) -> bool:
        """Check for a diagonal win (top-left to bottom-right)."""
        count = 0
        for r_offset in range(-min(row, col), min(ROWS - row, COLS - col)):
            r, c = row + r_offset, col + r_offset
            count = count + 1 if self.board[r][c] == player else 0
            if count >= 4:
                return True
        return False

    def _check_diagonal_anti(self, row: int, col: int, player: int) -> bool:
        """Check for a diagonal win (top-right to bottom-left)."""
        count = 0
        for r_offset in range(-min(row, COLS - 1 - col), min(ROWS - row, col + 1)):
            r, c = row + r_offset, col - r_offset
            count = count + 1 if self.board[r][c] == player else 0
            if count >= 4:
                return True
        return False

    def _check_draw(self) -> bool:
        """Check for a draw condition (board is full)."""
        return all(cell != 0 for row in self.board for cell in row)
