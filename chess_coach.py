"""Coaching layer on top of the trained ChessNet."""

import random

import chess

from chess_ai import get_top_moves

EASY = "easy"
MEDIUM = "medium"
HARD = "hard"

_SETTINGS = {
    EASY:   dict(temperature=1.8, random_chance=0.25, blunder_check=False),
    MEDIUM: dict(temperature=1.05, random_chance=0.0, blunder_check=False),
    HARD:   dict(temperature=0.2, random_chance=0.0, blunder_check=True),
}

LABELS = {EASY: "Low", MEDIUM: "Medium", HARD: "High"}
ORDER = [EASY, MEDIUM, HARD]

PIECE_VALUE = {
    chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
    chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0,
}


def hangs_piece(board, color):
    opponent = not color
    for square, piece in board.piece_map().items():
        if piece.color != color or piece.piece_type == chess.KING:
            continue
        if board.is_attacked_by(opponent, square) and not board.attackers(color, square):
            return True
    return False


def get_coach_move(board, level=MEDIUM):
    move, _ = get_coach_move_and_top(board, level, k=0)
    return move


def get_coach_move_and_top(board, level=MEDIUM, k=5):
    legal = list(board.legal_moves)
    if not legal:
        return None, []

    cfg = _SETTINGS[level]
    ranked = get_top_moves(board, k=len(legal), temperature=cfg["temperature"])
    top = ranked[:k] if k else []

    if cfg["random_chance"] and random.random() < cfg["random_chance"]:
        chosen = random.choice(legal)
    elif cfg["blunder_check"]:
        chosen = None
        for move, _ in ranked:
            after = board.copy()
            after.push(move)
            if not hangs_piece(after, board.turn):
                chosen = move
                break
        if chosen is None:
            chosen = ranked[0][0]
    else:
        moves, weights = zip(*ranked)
        chosen = random.choices(moves, weights=weights, k=1)[0]

    return chosen, top


def evaluate_human_move(board_before, move_played, k=5):
    legal = list(board_before.legal_moves)
    ranked = get_top_moves(board_before, k=len(legal))
    ranked_moves = [m for m, _ in ranked]

    try:
        rank = ranked_moves.index(move_played)
    except ValueError:
        rank = None

    after = board_before.copy()
    after.push(move_played)
    dropped_material = hangs_piece(after, board_before.turn)

    best_move, best_prob = ranked[0]

    return {
        "rank": rank,
        "is_best": rank == 0,
        "in_top_k": rank is not None and rank < k,
        "dropped_material": dropped_material,
        "best_move_san": board_before.san(best_move),
        "played_move_san": board_before.san(move_played),
        "top_k": [(board_before.san(m), p) for m, p in ranked[:k]],
    }


def coaching_message(result):
    if result["dropped_material"]:
        return (f"{result['played_move_san']} leaves a piece hanging — "
                f"{result['best_move_san']} kept everything defended.")
    if result["is_best"]:
        return f"{result['played_move_san']} — that's the strongest move here."
    if result["in_top_k"]:
        return (f"{result['played_move_san']} is a solid move. "
                f"{result['best_move_san']} was slightly stronger.")
    return (f"{result['played_move_san']} isn't among the engine's top picks. "
            f"{result['best_move_san']} was a stronger option.")