const lobbyContainer = document.getElementById('lobby-container');
const roomList = document.getElementById('room-list');
const gameContainer = document.querySelector('.game-container');
const board = document.getElementById('game-board');
const statusDisplay = document.getElementById('game-status');
const playerInfo = document.getElementById('player-info');
const resetButton = document.getElementById('reset-button');

const COLS = 7;
const ROWS = 6;
let playerNum = null;
let ws = null;

async function fetchRooms() {
    try {
        const response = await fetch('/rooms');
        const rooms = await response.json();
        renderRoomList(rooms);
    } catch (error) {
        console.error('Error fetching rooms:', error);
        roomList.textContent = 'Error loading rooms. Please try refreshing the page.';
    }
}

function renderRoomList(rooms) {
    roomList.innerHTML = '<h2>Available Rooms</h2>';
    rooms.forEach(room => {
        const roomElement = document.createElement('div');
        roomElement.classList.add('room');
        roomElement.textContent = `Room ${room.room_id} (${room.players}/2 players)`;
        if (room.is_full) {
            roomElement.classList.add('full');
        } else {
            roomElement.addEventListener('click', () => joinRoom(room.room_id));
        }
        roomList.appendChild(roomElement);
    });
}

function joinRoom(roomId) {
    lobbyContainer.style.display = 'none';
    gameContainer.style.display = 'block';

    ws = new WebSocket(`ws://${window.location.host}/ws/${roomId}`);

    ws.onopen = () => {
        statusDisplay.textContent = 'Waiting for opponent...';
    };

    ws.onclose = () => {
        statusDisplay.textContent = 'Disconnected from server.';
        playerInfo.textContent = '';
    };

    ws.onmessage = function(event) {
        const gameState = JSON.parse(event.data);

        if (gameState.error) {
            alert(gameState.error);
            showLobby();
            return;
        }

        // Assign player number if it's not set yet
        if (playerNum === null && gameState.playerNum) {
            playerNum = gameState.playerNum;
            playerInfo.textContent = `You are Player ${playerNum}`;
        }

        renderBoard(gameState);

        if (gameState.winner) {
            if (gameState.winner === playerNum) {
                statusDisplay.textContent = 'You win!';
            } else {
                statusDisplay.textContent = `Player ${gameState.winner} wins!`;
            }
        } else if (gameState.draw) {
            statusDisplay.textContent = "It's a draw!";
        } else if (gameState.gameActive) {
            if (gameState.currentPlayer === playerNum) {
                statusDisplay.textContent = 'Your Turn';
            } else {
                statusDisplay.textContent = `Player ${gameState.currentPlayer}'s Turn`;
            }
        } else {
             if (gameState.winner === "Opponent disconnected"){
                statusDisplay.textContent = "Opponent disconnected";
            } else {
                statusDisplay.textContent = 'Waiting for players...';
            }
        }
    };
}

function showLobby() {
    lobbyContainer.style.display = 'block';
    gameContainer.style.display = 'none';
    if (ws) {
        ws.close();
    }
    playerNum = null;
    fetchRooms();
}

function renderBoard(gameState) {
    board.innerHTML = '';
    const gameBoard = gameState.board;

    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
            const cell = document.createElement('div');
            cell.classList.add('cell');
            cell.dataset.row = r;
            cell.dataset.col = c;
            cell.addEventListener('click', () => handleCellClick(c));

            if (gameBoard[r][c] === 1) {
                const piece = document.createElement('div');
                piece.classList.add('piece', 'player1-piece');
                cell.appendChild(piece);
            } else if (gameBoard[r][c] === 2) {
                const piece = document.createElement('div');
                piece.classList.add('piece', 'player2-piece');
                cell.appendChild(piece);
            }
            board.appendChild(cell);
        }
    }
}

function handleCellClick(col) {
    if (ws) {
        ws.send(JSON.stringify({ col: col }));
    }
}

resetButton.addEventListener('click', () => {
    if (ws) {
        ws.send(JSON.stringify({ action: 'reset' }));
    }
});

// Initial load
fetchRooms();
setInterval(fetchRooms, 5000); // Refresh rooms every 5 seconds