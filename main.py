from typing import Any, TypedDict

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


class GameState(TypedDict):
    board: list[list[int]]
    currentPlayer: int
    gameActive: bool
    gameReady: bool
    winner: Any
    draw: bool
    playerNum: int | None


# In-memory store for the game
connections: list[WebSocket] = []
game_state: GameState = {}  # type: ignore


def initialize_game():
    """Resets the game state to the initial state."""
    game_state.update(
        {
            "board": [[0] * COLS for _ in range(ROWS)],
            "currentPlayer": 1,
            "gameActive": False,  # Game is not active until 2 players join
            "gameReady": False,  # Game is not ready until 2 players join
            "winner": None,
            "draw": False,
        }
    )


def check_win(row: int, col: int) -> bool:
    """Check for a win condition more efficiently around the last move."""
    player = game_state["board"][row][col]
    if player == 0:
        return False

    # Check horizontal
    count = 0
    for c in range(COLS):
        count = count + 1 if game_state["board"][row][c] == player else 0
        if count >= 4:
            return True

    # Check vertical
    count = 0
    for r in range(ROWS):
        count = count + 1 if game_state["board"][r][col] == player else 0
        if count >= 4:
            return True

    # Check diagonal (top-left to bottom-right)
    count = 0
    for r_offset in range(-min(row, col), min(ROWS - row, COLS - col)):
        r, c = row + r_offset, col + r_offset
        count = count + 1 if game_state["board"][r][c] == player else 0
        if count >= 4:
            return True

    # Check diagonal (top-right to bottom-left)
    count = 0
    for r_offset in range(-min(row, COLS - 1 - col), min(ROWS - row, col + 1)):
        r, c = row + r_offset, col - r_offset
        count = count + 1 if game_state["board"][r][c] == player else 0
        if count >= 4:
            return True

    return False


def check_draw() -> bool:
    """Check for a draw condition (board is full)."""
    return all(cell != 0 for row in game_state["board"] for cell in row)


async def broadcast_game_state():
    """Sends the current game state to all connected clients."""
    for i, connection in enumerate(connections):
        state_with_player_num = game_state.copy()
        state_with_player_num["playerNum"] = i + 1
        await connection.send_json(state_with_player_num)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles WebSocket connections for the game."""
    if len(connections) >= 2:
        await websocket.accept()
        await websocket.send_json({"error": "Game is full"})
        await websocket.close()
        return

    await websocket.accept()
    connections.append(websocket)

    if len(connections) == 1:
        initialize_game()
    elif len(connections) == 2:
        game_state["gameActive"] = True
        game_state["gameReady"] = True

    await broadcast_game_state()

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("action") == "reset":
                initialize_game()
                if len(connections) == 2:
                    game_state["gameActive"] = True
                    game_state["gameReady"] = True
                await broadcast_game_state()
                continue

            player_num = connections.index(websocket) + 1

            if (
                game_state["gameReady"]
                and game_state["gameActive"]
                and game_state["currentPlayer"] == player_num
            ):
                col = data.get("col")
                if (
                    col is not None
                    and 0 <= col < COLS
                    and game_state["board"][0][col] == 0
                ):
                    for r in range(ROWS - 1, -1, -1):
                        if game_state["board"][r][col] == 0:
                            game_state["board"][r][col] = player_num

                            if check_win(r, col):
                                game_state["gameActive"] = False
                                game_state["winner"] = player_num
                            elif check_draw():
                                game_state["gameActive"] = False
                                game_state["draw"] = True
                            else:
                                game_state["currentPlayer"] = (
                                    2 if player_num == 1 else 1
                                )

                            await broadcast_game_state()
                            break
    except WebSocketDisconnect:
        player_num = connections.index(websocket) + 1
        connections.remove(websocket)
        if connections:
            # Notify remaining player
            game_state["gameActive"] = False
            game_state["winner"] = "Opponent disconnected"
            # We need to re-initialize for the next game
            initialize_game()
            await broadcast_game_state()
        else:
            # Last player disconnected, reset everything
            initialize_game()


if __name__ == "__main__":
    import uvicorn

    initialize_game()
    uvicorn.run(app, host="0.0.0.0", port=8000)
