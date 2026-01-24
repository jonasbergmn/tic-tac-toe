from typing import Any, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


# Game constants
ROWS = 6
COLS = 7


class Game:
    """Represents the state and logic of a Connect 4 game."""

    def __init__(self):
        self.board: List[List[int]] = []
        self.current_player: int = 1
        self.game_active: bool = False
        self.game_ready: bool = False
        self.winner: Optional[Any] = None
        self.draw: bool = False
        self.connections: List[WebSocket] = []
        self.initialize_game()

    def initialize_game(self):
        """Resets the game state to the initial state."""
        self.board = [[0] * COLS for _ in range(ROWS)]
        self.current_player = 1
        self.game_active = False
        self.game_ready = False
        self.winner = None
        self.draw = False
        if len(self.connections) == 2:
            self.game_active = True
            self.game_ready = True

    def add_player(self, websocket: WebSocket) -> bool:
        """Adds a player to the game if there is space."""
        if len(self.connections) >= 2:
            return False
        self.connections.append(websocket)
        # When first player joins, reset the game
        if len(self.connections) == 1:
            self.initialize_game()
        elif len(self.connections) == 2:
            self.game_active = True
            self.game_ready = True
        return True

    def remove_player(self, websocket: WebSocket):
        """Removes a player from the game and handles disconnection logic."""
        try:
            self.connections.remove(websocket)
            if self.connections:
                # A player left, game is over, and we need to reset for the next game.
                self.game_active = False
                self.winner = "Opponent disconnected"
                self.initialize_game()
            else:
                # Last player disconnected, fully reset.
                self.initialize_game()
        except ValueError:
            pass  # Player already removed

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

    async def broadcast_game_state(self):
        """Sends the current game state to all connected clients."""
        for i, connection in enumerate(self.connections):
            await connection.send_json(self.get_state(i + 1))

    def make_move(self, col: int, player_num: int) -> bool:
        """Attempts to make a move for a player."""
        if not (0 <= col < COLS and self.board[0][col] == 0):
            return False

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
                return True
        return False

    def _check_win(self, row: int, col: int) -> bool:
        """Check for a win condition more efficiently around the last move."""
        player = self.board[row][col]
        if player == 0:
            return False

        # Check horizontal
        count = 0
        for c in range(COLS):
            count = count + 1 if self.board[row][c] == player else 0
            if count >= 4:
                return True

        # Check vertical
        count = 0
        for r in range(ROWS):
            count = count + 1 if self.board[r][col] == player else 0
            if count >= 4:
                return True

        # Check diagonal (top-left to bottom-right)
        count = 0
        for r_offset in range(-min(row, col), min(ROWS - row, COLS - col)):
            r, c = row + r_offset, col + r_offset
            count = count + 1 if self.board[r][c] == player else 0
            if count >= 4:
                return True

        # Check diagonal (top-right to bottom-left)
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


# In-memory store for the game
game = Game()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles WebSocket connections for the game."""
    await websocket.accept()
    if not game.add_player(websocket):
        await websocket.send_json({"error": "Game is full"})
        await websocket.close()
        return

    await game.broadcast_game_state()

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "reset":
                game.initialize_game()
                await game.broadcast_game_state()
                continue

            try:
                player_num = game.connections.index(websocket) + 1
            except ValueError:
                # Player has disconnected, but we received a message.
                # This can happen in rare race conditions.
                break

            if (
                game.game_ready
                and game.game_active
                and game.current_player == player_num
            ):
                col = data.get("col")
                if col is not None and game.make_move(col, player_num):
                    await game.broadcast_game_state()

    except WebSocketDisconnect:
        game.remove_player(websocket)
        # When a player disconnects, the game state changes for the other player.
        # We need to inform the remaining player of this change.
        if game.connections:
            await game.broadcast_game_state()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
