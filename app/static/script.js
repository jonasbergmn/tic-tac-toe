const lobbyContainer = document.getElementById('lobby-container');
const roomList = document.getElementById('room-list');
const gameContainer = document.querySelector('.game-container');
const board = document.getElementById('game-board');
const statusDisplay = document.getElementById('game-status');
const playerInfo = document.getElementById('player-info');
const resetButton = document.getElementById('reset-button');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendChatButton = document.getElementById('send-chat-button');

const COLS = 7;
const ROWS = 6;
let playerNum = null;
let ws = null;
let lastPieceElement = null; // To keep track of the last placed piece element

// Stores the state of pieces currently rendered on the DOM
// Used to determine if a piece is new or has been removed
const currentDOMPieces = Array(ROWS).fill(null).map(() => Array(COLS).fill(0));

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

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${protocol}://${window.location.host}/ws/${roomId}`);

    ws.onopen = () => {
        statusDisplay.textContent = 'Waiting for opponent...';
    };

    ws.onclose = () => {
        statusDisplay.textContent = 'Disconnected from server.';
        playerInfo.textContent = '';
    };

    ws.onmessage = function (event) {

        const inputData = JSON.parse(event.data);
        if (inputData.hasOwnProperty("message")) {
            const chatMessage = inputData["message"];
            const chatUser = inputData["player"];

            const messageElement = document.createElement('div');
            messageElement.textContent = `${chatUser}: ${chatMessage}`;
            chatMessages.appendChild(messageElement);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            return;
        }

        const gameState = inputData;

        if (gameState.error) {
            alert(gameState.error);
            return;
        }

        // Assign player number if it's not set yet
        if (playerNum === null && gameState.playerNum) {
            playerNum = gameState.playerNum;
            playerInfo.textContent = `You are Player ${playerNum}`;
        }

        updateBoard(gameState);

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
            if (gameState.winner === "Opponent disconnected") {
                statusDisplay.textContent = "Opponent disconnected";
            } else {
                statusDisplay.textContent = 'Waiting for players...';
            }
        }
    };

};


function showLobby() {
    lobbyContainer.style.display = 'block';
    gameContainer.style.display = 'none';
    if (ws) {
        ws.close();
    }
    playerNum = null;
    fetchRooms();
}

function initializeBoardStructure() {
    board.innerHTML = ''; // Clear any existing structure
    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
            const cell = document.createElement('div');
            cell.classList.add('cell');
            cell.dataset.row = r;
            cell.dataset.col = c;
            cell.addEventListener('click', () => {
                handleCellClick(c);
            });
            board.appendChild(cell);
        }
    }
}



function updateBoard(gameState) {
    const gameBoard = gameState.board;

    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
            const cell = board.children[r * COLS + c]; // Get existing cell
            let piece = cell.querySelector('.piece'); // Check for existing piece

            const playerInState = gameBoard[r][c];
            const playerInDOM = currentDOMPieces[r][c];

            if (playerInState !== playerInDOM) { // State changed for this cell
                if (playerInState !== 0) { // A piece should be here (or changed)
                    if (!piece) { // No piece in DOM, create new one
                        piece = document.createElement('div');
                        piece.classList.add('piece');
                        // Add new-piece class for animation if it's a freshly dropped piece
                        if (playerInDOM === 0) { // Only animate if it was previously empty
                            piece.classList.add('new-piece');
                            setTimeout(() => {
                                piece.classList.remove('new-piece');
                            }, 500); // 0.5 seconds, matches CSS animation duration

                            // Highlight this as the last placed piece
                            if (lastPieceElement) {
                                lastPieceElement.classList.remove('last-piece');
                            }
                            piece.classList.add('last-piece');
                            lastPieceElement = piece;
                        }
                        cell.appendChild(piece);
                    }
                    // Update player class for the piece
                    if (playerInState === 1) {
                        piece.classList.add('player1-piece');
                        piece.classList.remove('player2-piece');
                    } else {
                        piece.classList.add('player2-piece');
                        piece.classList.remove('player1-piece');
                    }
                } else { // No piece should be here (removed)
                    if (piece) { // Piece exists in DOM, remove it
                        cell.removeChild(piece);
                    }
                }
                currentDOMPieces[r][c] = playerInState; // Update DOM state tracking
            }
            // No need to re-add event listeners; they are attached once during initializeBoardStructure
        }
    }
}

sendChatButton.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

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

function sendMessage() {
    const message = chatInput.value.trim();

    if (message && ws) {
        ws.send(JSON.stringify({ message: message }));
        chatInput.value = '';
    }
}

// Initial setup
initializeBoardStructure();
fetchRooms();
setInterval(fetchRooms, 5000); // Refresh rooms every 5 seconds