"""Coaching and difficulty control on top of the trained ChessNet policy."""

import random

import chess

from chess_ai import get_top_moves

EASY = "easy"
CASUAL = "casual"
MEDIUM = "medium"
HARD = "hard"
EXPERT = "expert"

_SETTINGS = {
    EASY:   dict(temperature=2.0, random_chance=0.35, blunder_check=False, top_bias=0.0),
    CASUAL: dict(temperature=1.5, random_chance=0.15, blunder_check=False, top_bias=0.05),
    MEDIUM: dict(temperature=1.0, random_chance=0.0, blunder_check=False, top_bias=0.15),
    HARD:   dict(temperature=0.45, random_chance=0.0, blunder_check=True, top_bias=0.35),
    EXPERT: dict(temperature=0.20, random_chance=0.0, blunder_check=True, top_bias=0.65),
}

LABELS = {
    EASY: "Easy",
    CASUAL: "Casual",
    MEDIUM: "Medium",
    HARD: "Hard",
    EXPERT: "Expert",
}
ORDER = [EASY, CASUAL, MEDIUM, HARD, EXPERT]

STYLES = {
    "balanced": "Balanced",
    "aggressive": "Aggressive",
    "defensive": "Defensive",
    "tactical": "Tactical",
    "positional": "Positional",
}

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


def _style_score(board, move, style):
    if style == "balanced":
        return 0.0

    before_material = sum(
        PIECE_VALUE[p.piece_type] * (1 if p.color == board.turn else -1)
        for p in board.piece_map().values()
    )
    after = board.copy()
    capture = after.is_capture(move)
    check = after.gives_check(move)
    after.push(move)

    score = 0.0
    if style == "aggressive":
        score += 0.45 if capture else 0.0
        score += 0.55 if check else 0.0
        score += 0.08 * max(0, len(list(after.legal_moves)) - 20)
    elif style == "defensive":
        score += 0.35 if after.is_check() is False else 0.0
        if hangs_piece(after, board.turn):
            score -= 1.5
        score += 0.15 if not capture else 0.0
    elif style == "tactical":
        score += 0.75 if check else 0.0
        score += 0.60 if capture else 0.0
        score += 0.20 * len(after.attackers(board.turn, move.to_square))
    elif style == "positional":
        score += 0.10 * len(list(after.legal_moves))
        score += 0.25 if not capture else -0.05
        score += 0.15 if after.is_castling(move) else 0.0
    return score + before_material * 0.0


def get_coach_move(board, level=MEDIUM, style="balanced"):
    move, _ = get_coach_move_and_top(board, level, style=style, k=0)
    return move


def get_coach_move_and_top(board, level=MEDIUM, style="balanced", k=5):
    legal = list(board.legal_moves)
    if not legal:
        return None, []

    cfg = _SETTINGS.get(level, _SETTINGS[MEDIUM])
    ranked = get_top_moves(board, k=len(legal), temperature=cfg["temperature"])
    top = ranked[:k] if k else []

    if cfg["random_chance"] and random.random() < cfg["random_chance"]:
        chosen = random.choice(legal)
    elif cfg["blunder_check"]:
        candidates = []
        for move, prob in ranked:
            after = board.copy()
            after.push(move)
            if not hangs_piece(after, board.turn):
                score = prob + _style_score(board, move, style) * 0.02
                candidates.append((move, score))
        if candidates:
            chosen = max(candidates, key=lambda item: item[1])[0]
        else:
            chosen = ranked[0][0]
    elif style != "balanced":
        candidates = [
            (move, prob + _style_score(board, move, style) * 0.02)
            for move, prob in ranked[:max(8, k)]
        ]
        chosen = max(candidates, key=lambda item: item[1])[0]
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
        "legal_count": len(legal),
        "is_best": rank == 0,
        "in_top_k": rank is not None and rank < k,
        "dropped_material": dropped_material,
        "best_move_san": board_before.san(best_move),
        "played_move_san": board_before.san(move_played),
        "best_prob": best_prob,
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
