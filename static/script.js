const board = document.getElementById('game-board');
const statusDisplay = document.getElementById('game-status');
const playerInfo = document.getElementById('player-info');
const resetButton = document.getElementById('reset-button');

const ws = new WebSocket(`ws://${window.location.host}/ws`);

const COLS = 7;
const ROWS = 6;
let playerNum = null;

ws.onopen = () => {
    statusDisplay.textContent = 'Waiting for opponent...';
};

ws.onclose = () => {
    statusDisplay.textContent = 'Disconnected from server.';
    playerInfo.textContent = '';
};

ws.onmessage = function(event) {
    const gameState = JSON.parse(event.data);

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
    // Send the move to the server
    ws.send(JSON.stringify({ col: col }));
}

resetButton.addEventListener('click', () => {
    ws.send(JSON.stringify({ action: 'reset' }));
});