from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .lobby import Lobby
from .config import DEFAULT_ROOMS

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def read_index():
    return FileResponse("app/static/index.html")


lobby = Lobby()
for i in range(DEFAULT_ROOMS):
    lobby.create_room(f"room_{i + 1}")


@app.get("/rooms")
async def get_rooms():
    """Returns a list of available game rooms."""
    return lobby.get_rooms_info()


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """Handles WebSocket connections for a specific game room."""
    room = lobby.get_room(room_id)
    if not room:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    if not room.add_player(websocket):
        await websocket.send_json({"error": "Game is full"})
        await websocket.close()
        return

    await room.manager.broadcast_game_state(room.get_state, room.get_player_num)

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "reset":
                room.initialize_game()
                await room.manager.broadcast_game_state(
                    room.get_state, room.get_player_num
                )
                continue

            player_num = room.get_player_num(websocket)
            if player_num is None:
                break

            col = data.get("col")
            if col is not None:
                success, reason = room.make_move(col, player_num)
                if success:
                    await room.manager.broadcast_game_state(
                        room.get_state, room.get_player_num
                    )
                else:
                    await websocket.send_json({"error": reason})

    except WebSocketDisconnect:
        room.remove_player(websocket)
        if room.manager.active_connections:
            await room.manager.broadcast_game_state(room.get_state, room.get_player_num)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
