import pytest
from fastapi.testclient import TestClient
from fastapi import WebSocketDisconnect
from main import app, initialize_game, game_state
import json

client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    initialize_game() # Ensure game state is clean before each test
    yield
    # After each test, reset the game state and connections
    # This might be redundant if initialize_game is called before each test
    # but ensures a clean slate if any test modifies connections directly
    global game_state
    game_state = {}
    from main import connections
    connections.clear()
    initialize_game()

@pytest.mark.anyio
async def test_websocket_connection():
    websocket = client.websocket_connect("/ws")
    try:
        response = await websocket.receive_json()
        assert "board" in response
        assert response["playerNum"] == 1
        assert response["gameActive"] == False
        assert response["gameReady"] == False
    finally:
        await websocket.close()

@pytest.mark.anyio
async def test_two_players_connect():
    ws1 = client.websocket_connect("/ws")
    ws2 = client.websocket_connect("/ws")
    try:
        # Player 1 connects
        response1 = await ws1.receive_json()
        assert response1["playerNum"] == 1
        assert response1["gameActive"] == False
        assert response1["gameReady"] == False

        # Player 2 connects
        response2 = await ws2.receive_json()
        assert response2["playerNum"] == 2
        assert response2["gameActive"] == True
        assert response2["gameReady"] == True
        
        # Both should receive updated state
        response1_after_p2 = await ws1.receive_json()
        assert response1_after_p2["playerNum"] == 1
        assert response1_after_p2["gameActive"] == True
        assert response1_after_p2["gameReady"] == True
    finally:
        await ws1.close()
        await ws2.close()

@pytest.mark.anyio
async def test_three_players_connection_refused():
    ws1 = client.websocket_connect("/ws")
    ws2 = client.websocket_connect("/ws")
    ws3 = None
    try:
        await ws1.receive_json() # Initial state for P1
        await ws2.receive_json() # Initial state for P2
        await ws1.receive_json() # Updated state for P1 after P2 joins

        with pytest.raises(WebSocketDisconnect):
            ws3 = client.websocket_connect("/ws")
            response3 = await ws3.receive_json()
            assert response3["error"] == "Game is full"
    finally:
        await ws1.close()
        await ws2.close()
        if ws3:
            await ws3.close()

@pytest.mark.anyio
async def test_player_move():
    ws1 = client.websocket_connect("/ws")
    ws2 = client.websocket_connect("/ws")
    try:
        # P1 and P2 connect and game starts
        await ws1.receive_json() 
        await ws2.receive_json()
        await ws1.receive_json() 

        # Player 1 makes a move
        await ws1.send_json({"col": 0})

        # Both should receive updated state
        state_p1 = await ws1.receive_json()
        state_p2 = await ws2.receive_json()

        assert state_p1["board"][5][0] == 1
        assert state_p2["board"][5][0] == 1
        assert state_p1["currentPlayer"] == 2
        assert state_p2["currentPlayer"] == 2
    finally:
        await ws1.close()
        await ws2.close()

@pytest.mark.anyio
async def test_player_wins():
    ws1 = client.websocket_connect("/ws")
    ws2 = client.websocket_connect("/ws")
    try:
        # P1 and P2 connect and game starts
        await ws1.receive_json()
        await ws2.receive_json()
        await ws1.receive_json()
        
        # Simulate P1 winning (4 in a row in column 0)
        await ws1.send_json({"col": 0}) # P1
        await ws2.receive_json()
        await ws1.receive_json()

        await ws2.send_json({"col": 1}) # P2
        await ws1.receive_json()
        await ws2.receive_json()
        
        await ws1.send_json({"col": 0}) # P1
        await ws2.receive_json()
        await ws1.receive_json()

        await ws2.send_json({"col": 1}) # P2
        await ws1.receive_json()
        await ws2.receive_json()

        await ws1.send_json({"col": 0}) # P1
        await ws2.receive_json()
        await ws1.receive_json()

        await ws2.send_json({"col": 1}) # P2
        await ws1.receive_json()
        await ws2.receive_json()

        await ws1.send_json({"col": 0}) # P1 wins
        win_state_p1 = await ws1.receive_json()
        win_state_p2 = await ws2.receive_json()

        assert win_state_p1["winner"] == 1
        assert win_state_p2["winner"] == 1
        assert win_state_p1["gameActive"] == False
    finally:
        await ws1.close()
        await ws2.close()

@pytest.mark.anyio
async def test_reset_game():
    ws1 = client.websocket_connect("/ws")
    ws2 = client.websocket_connect("/ws")
    try:
        # P1 and P2 connect and game starts
        await ws1.receive_json()
        await ws2.receive_json()
        await ws1.receive_json()

        # P1 makes a move
        await ws1.send_json({"col": 0})
        await ws1.receive_json()
        await ws2.receive_json()

        # Send reset action
        await ws1.send_json({"action": "reset"})

        # Both should receive initial game state
        reset_state_p1 = await ws1.receive_json()
        reset_state_p2 = await ws2.receive_json()

        assert all(0 in row for row in reset_state_p1["board"]) # Board is empty
        assert reset_state_p1["currentPlayer"] == 1
        assert reset_state_p1["gameActive"] == True
        assert reset_state_p2["gameActive"] == True
    finally:
        await ws1.close()
        await ws2.close()
