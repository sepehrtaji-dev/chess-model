"""Regression tests for the interactive lessons.

These would have caught the broken lesson positions (unsolvable
discovered-check / double-check / queen-mate lessons, pin and skewer
lessons whose answers were plain captures).
"""

import chess
import pytest

from chess_lessons import LESSONS

BY_ID = {lesson.id: lesson for lesson in LESSONS}

# Lessons whose check() accepts exactly these UCI moves and nothing else.
UNIQUE_ANSWERS = {
    "castle": {"e1g1"},
    "enpassant": {"e5d6"},
    "fork": {"d5c7"},
    "capture_pawn": {"e4d5"},
    "capture_knight": {"c3d5"},
    "pin": {"d1e2"},
    "skewer": {"a1a5"},
    "castle_queenside": {"e1c1"},
    "center_control": {"e2e4"},
    "develop_bishop": {"f1c4", "f1b5"},
    "simple_trade": {"e3d5"},
    "defend_piece": {"e1e2", "e1d2", "e1f2"},
    "double_check": {"d7f6"},
    "opposition": {"e1e2"},
    "king_activity": {"e1e2", "e1d2", "e1f2"},
}

# Movement-drill lessons that intentionally accept every move of a piece.
ANY_MOVE_OK = {"king"}

# Lessons that require delivering checkmate.
MATE_IDS = {"mate", "queen_mate", "smothered_mate"}


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda l: l.id)
def test_fen_is_valid(lesson):
    assert chess.Board(lesson.fen).status() == chess.STATUS_VALID


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda l: l.id)
def test_answer_is_legal_and_solves(lesson):
    board = chess.Board(lesson.fen)
    move = chess.Move.from_uci(lesson.answer_uci)
    assert move in board.legal_moves, (
        f"{lesson.id}: answer {lesson.answer_uci} is not legal in {lesson.fen}"
    )
    after = board.copy()
    after.push(move)
    assert lesson.check(move, board, after), (
        f"{lesson.id}: answer {lesson.answer_uci} does not pass its own check"
    )


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda l: l.id)
def test_answer_san_matches_uci(lesson):
    board = chess.Board(lesson.fen)
    move = chess.Move.from_uci(lesson.answer_uci)
    assert board.san(move) == lesson.answer_san, (
        f"{lesson.id}: answer_san {lesson.answer_san!r} != real SAN "
        f"{board.san(move)!r}"
    )


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda l: l.id)
def test_check_is_selective(lesson):
    """The check must not accept literally every legal move."""
    if lesson.id in ANY_MOVE_OK:
        pytest.skip("movement drill: every move of the piece is intended "
                    "to pass")
    board = chess.Board(lesson.fen)
    passing = 0
    for mv in board.legal_moves:
        after = board.copy()
        after.push(mv)
        if lesson.check(mv, board, after):
            passing += 1
    assert passing < len(list(board.legal_moves)), (
        f"{lesson.id}: check accepts every legal move"
    )


@pytest.mark.parametrize("lesson_id,expected", sorted(UNIQUE_ANSWERS.items()))
def test_unique_answer_lessons(lesson_id, expected):
    lesson = BY_ID[lesson_id]
    board = chess.Board(lesson.fen)
    passing = set()
    for mv in board.legal_moves:
        after = board.copy()
        after.push(mv)
        if lesson.check(mv, board, after):
            passing.add(mv.uci())
    assert passing == expected, (
        f"{lesson_id}: expected only {expected} to pass, got {passing}"
    )


@pytest.mark.parametrize("lesson_id", sorted(MATE_IDS))
def test_mate_lessons_only_accept_mate(lesson_id):
    lesson = BY_ID[lesson_id]
    board = chess.Board(lesson.fen)
    for mv in board.legal_moves:
        after = board.copy()
        after.push(mv)
        if lesson.check(mv, board, after):
            assert after.is_checkmate(), (
                f"{lesson_id}: {mv.uci()} passes the check but is not mate"
            )


def test_double_check_needs_two_checkers():
    lesson = BY_ID["double_check"]
    board = chess.Board(lesson.fen)
    for mv in board.legal_moves:
        after = board.copy()
        after.push(mv)
        if lesson.check(mv, board, after):
            assert len(after.checkers()) >= 2


def test_discovered_check_answer_is_discovered():
    lesson = BY_ID["discovered_check"]
    board = chess.Board(lesson.fen)
    answer = chess.Move.from_uci(lesson.answer_uci)
    after = board.copy()
    after.push(answer)
    # The knight itself must not be the checker — the bishop is.
    assert not any(p.piece_type == chess.KNIGHT
                   for p in (after.piece_at(sq) for sq in after.checkers()))
    assert after.is_check()


def test_lesson_count():
    assert len(LESSONS) == 33


def test_lesson_levels_cover_all_lessons():
    from lesson_levels import LESSON_LEVELS

    assert {lesson.id for lesson in LESSONS} == set(LESSON_LEVELS)
