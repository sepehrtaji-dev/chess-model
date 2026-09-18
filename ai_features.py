"""Lightweight position analysis helpers for the trained ChessNet policy."""

import chess

PIECE_VALUES = {
    chess.PAWN: 1.0,
    chess.KNIGHT: 3.0,
    chess.BISHOP: 3.25,
    chess.ROOK: 5.0,
    chess.QUEEN: 9.0,
    chess.KING: 0.0,
}


def material_score(board):
    score = 0.0
    for piece in board.piece_map().values():
        value = PIECE_VALUES[piece.piece_type]
        score += value if piece.color == chess.WHITE else -value
    return score


def position_score(board):
    """Return a small human-readable heuristic score from White's view."""
    if board.is_checkmate():
        return -100.0 if board.turn == chess.WHITE else 100.0
    if board.is_stalemate() or board.is_insufficient_material():
        return 0.0

    material = material_score(board)
    white_mobility = len(list(board.legal_moves)) if board.turn == chess.WHITE else 0
    flipped = board.copy()
    flipped.turn = chess.BLACK
    black_mobility = len(list(flipped.legal_moves))
    mobility = (white_mobility - black_mobility) * 0.03

    check_bonus = 0.35 if board.is_check() and board.turn == chess.BLACK else 0.0
    check_bonus -= 0.35 if board.is_check() and board.turn == chess.WHITE else 0.0
    return material + mobility + check_bonus


def normalized_evaluation(board):
    """Map the heuristic score to [-1, 1] for the UI evaluation bar."""
    score = position_score(board)
    if score >= 99:
        return 1.0
    if score <= -99:
        return -1.0
    return score / (abs(score) + 4.0)


def move_quality(result):
    if result.get("dropped_material"):
        return "Blunder"
    rank = result.get("rank")
    if rank == 0:
        return "Excellent"
    if rank is not None and rank < 3:
        return "Good"
    if rank is not None and rank < 10:
        return "Inaccuracy"
    return "Mistake"


def summarize_game(board_history, moves, human_color, get_result):
    rows = []
    ranks = []
    best = mistakes = blunders = 0

    for idx, move in enumerate(moves):
        if idx % 2 != (0 if human_color == chess.WHITE else 1):
            continue
        before = board_history[idx]
        result = get_result(before, move)
        quality = move_quality(result)
        if result.get("rank") is not None:
            ranks.append(result["rank"])
        if quality == "Excellent":
            best += 1
        elif quality == "Inaccuracy":
            mistakes += 1
        elif quality == "Mistake":
            mistakes += 1
        elif quality == "Blunder":
            blunders += 1
        rows.append({
            "ply": idx + 1,
            "move": result["played_move_san"],
            "best": result["best_move_san"],
            "quality": quality,
        })

    if ranks:
        accuracy = max(0.0, min(100.0, 100.0 - sum(min(r, 20) for r in ranks) / len(ranks) * 4.0))
        accuracy = f"{accuracy:.0f}%"
    else:
        accuracy = "—"

    if blunders:
        message = "ChessNet found a few critical moments worth practicing."
    elif mistakes:
        message = "Your game had some positions where a stronger move was available."
    else:
        message = "Your moves stayed close to ChessNet's strongest policy choices."

    return {
        "accuracy": accuracy,
        "best": best,
        "mistakes": mistakes,
        "blunders": blunders,
        "message": message,
        "rows": rows,
    }
