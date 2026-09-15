import threading
from pathlib import Path

import chess
import torch

from model import ChessNet
from chess_utils import board_to_tensor, decode_move, encode_move

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_PATH = Path(__file__).resolve().parent / "checkpoints" / "chess_model_best.pth"

_model = None
_model_lock = threading.Lock()
_model_error = None


def get_model():
    """Load the trained ChessNet once, on first use (thread-safe)."""
    global _model, _model_error
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            if _model_error is not None:
                raise _model_error
            try:
                m = ChessNet().to(DEVICE)
                sd = torch.load(MODEL_PATH, map_location=DEVICE)
                m.load_state_dict(sd)
                m.eval()
                _model = m
            except Exception as e:
                _model_error = e
                raise
    return _model


def model_loaded():
    return _model is not None


def _legal_move_logits(board, model):
    """Logits for every legal move, as {move: logit}."""
    tensor = torch.tensor(
        board_to_tensor(board), dtype=torch.float32).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        logits = model(tensor).squeeze(0)
    out = {}
    for move in board.legal_moves:
        out[move] = float(logits[encode_move(board, move)])
    return out


def get_top_moves(board, k=5):
    """Top-k legal moves with softmax probabilities, best first."""
    probs = _softmax(_legal_move_logits(board, get_model()))
    ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    return ranked[:k]


def get_ai_move(board, sample=False):
    """Pick the model's move: greedy argmax, or sampled from its policy."""
    probs = _softmax(_legal_move_logits(board, get_model()))
    if sample and len(probs) > 1:
        moves = list(probs.keys())
        weights = torch.tensor([probs[m] for m in moves])
        pick = torch.multinomial(weights, 1).item()
        return moves[pick]
    return max(probs, key=probs.get)


def get_move_and_top(board, k=5, sample=False):
    """Chosen move plus top-k policy in a single forward pass."""
    probs = _softmax(_legal_move_logits(board, get_model()))
    ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    if sample and len(probs) > 1:
        moves = list(probs.keys())
        weights = torch.tensor([probs[m] for m in moves])
        pick = torch.multinomial(weights, 1).item()
        chosen = moves[pick]
    else:
        chosen = ranked[0][0]
    return chosen, ranked[:k]


def _softmax(values):
    if not values:
        return {}
    keys = list(values.keys())
    t = torch.tensor([values[k] for k in keys])
    t = torch.softmax(t, dim=0)
    return dict(zip(keys, t.tolist()))
