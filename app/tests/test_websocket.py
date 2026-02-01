import pytest
from fastapi.testclient import TestClient
from fastapi import WebSocketDisconnect
from app.main import app, lobby

client = TestClient(app)


@pytest.fixture(autouse=True)
def run_around_tests():
    # Reset the lobby before each test
    lobby.rooms = {}
    lobby.create_room("room_1")
    lobby.create_room("room_2")
    yield


@pytest.mark.anyio
async def test_websocket_connection():
    with client.websocket_connect("/ws/room_1") as websocket:
        response = websocket.receive_json()
        assert "board" in response
        assert response["playerNum"] == 1
        assert response["gameActive"] is False
        assert response["gameReady"] is False


@pytest.mark.anyio
async def test_two_players_connect():
    with client.websocket_connect("/ws/room_1") as ws1:
        response1 = ws1.receive_json()
        assert response1["playerNum"] == 1
        assert response1["gameActive"] is False
        assert response1["gameReady"] is False

        with client.websocket_connect("/ws/room_1") as ws2:
            response2 = ws2.receive_json()
            assert response2["playerNum"] == 2
            assert response2["gameActive"] is True
            assert response2["gameReady"] is True

            # Both should receive updated state
            response1_after_p2 = ws1.receive_json()
            assert response1_after_p2["playerNum"] == 1
            assert response1_after_p2["gameActive"] is True
            assert response1_after_p2["gameReady"] is True


@pytest.mark.anyio
async def test_three_players_connection_refused():
    with client.websocket_connect("/ws/room_1") as ws1:
        ws1.receive_json()  # Initial state for P1

        with client.websocket_connect("/ws/room_1") as ws2:
            ws2.receive_json()  # Initial state for P2
            ws1.receive_json()  # Updated state for P1 after P2 joins

            with client.websocket_connect("/ws/room_1") as ws3:
                response = ws3.receive_json()
                assert response == {"error": "Game is full"}
                with pytest.raises(WebSocketDisconnect):
                    ws3.receive_json()


@pytest.mark.anyio
async def test_player_move():
    with client.websocket_connect("/ws/room_1") as ws1:
        with client.websocket_connect("/ws/room_1") as ws2:
            # P1 and P2 connect and game starts
            ws1.receive_json()
            ws2.receive_json()
            ws1.receive_json()

            # Player 1 makes a move
            ws1.send_json({"col": 0})

            # Both should receive updated state
            state_p1 = ws1.receive_json()
            state_p2 = ws2.receive_json()

            assert state_p1["board"][5][0] == 1
            assert state_p2["board"][5][0] == 1
            assert state_p1["currentPlayer"] == 2
            assert state_p2["currentPlayer"] == 2


@pytest.mark.anyio
async def test_player_wins():
    with client.websocket_connect("/ws/room_1") as ws1:
        with client.websocket_connect("/ws/room_1") as ws2:
            # P1 and P2 connect and game starts
            ws1.receive_json()
            ws2.receive_json()
            ws1.receive_json()

            # Simulate P1 winning (4 in a row in column 0)
            ws1.send_json({"col": 0})  # P1
            ws2.receive_json()
            ws1.receive_json()

            ws2.send_json({"col": 1})  # P2
            ws1.receive_json()
            ws2.receive_json()

            ws1.send_json({"col": 0})  # P1
            ws2.receive_json()
            ws1.receive_json()

            ws2.send_json({"col": 1})  # P2
            ws1.receive_json()
            ws2.receive_json()

            ws1.send_json({"col": 0})  # P1
            ws2.receive_json()
            ws1.receive_json()

            ws2.send_json({"col": 1})  # P2
            ws1.receive_json()
            ws2.receive_json()

            ws1.send_json({"col": 0})  # P1 wins
            win_state_p1 = ws1.receive_json()
            win_state_p2 = ws2.receive_json()

            assert win_state_p1["winner"] == 1
            assert win_state_p2["winner"] == 1
            assert win_state_p1["gameActive"] is False


@pytest.mark.anyio
async def test_reset_game():
    with client.websocket_connect("/ws/room_1") as ws1:
        with client.websocket_connect("/ws/room_1") as ws2:
            # P1 and P2 connect and game starts
            ws1.receive_json()
            ws2.receive_json()
            ws1.receive_json()

            # P1 makes a move
            ws1.send_json({"col": 0})
            ws1.receive_json()
            ws2.receive_json()

            # Send reset action
            ws1.send_json({"action": "reset"})

            # Both should receive initial game state
            reset_state_p1 = ws1.receive_json()
            reset_state_p2 = ws2.receive_json()

            assert all(0 in row for row in reset_state_p1["board"])  # Board is empty
            assert reset_state_p1["currentPlayer"] == 1
            assert reset_state_p1["gameActive"] is True
            assert reset_state_p2["gameActive"] is True
