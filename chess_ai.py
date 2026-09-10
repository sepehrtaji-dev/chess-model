import chess
import torch
from model import ChessNet
from chess_utils import board_to_tensor, decode_move

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = ChessNet().to(DEVICE)
model.load_state_dict(torch.load("chess_model.pth", map_location=DEVICE))
model.eval()


def get_ai_move(board):
    tensor = torch.tensor(board_to_tensor(
        board), dtype=torch.float32).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        logits = model(tensor).squeeze(0)

    ranked = torch.argsort(logits, descending=True).tolist()

    for idx in ranked:
        move = decode_move(board, idx)
        if move in board.legal_moves:
            return move

    return list(board.legal_moves)[0]
