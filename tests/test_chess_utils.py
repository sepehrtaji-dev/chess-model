"""Tests for the position encoding and move index helpers."""

import chess
import numpy as np

from chess_utils import (board_to_tensor, decode_move, encode_move,
                         legal_move_indices)

FENS = [
    chess.STARTING_FEN,
    "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK1NR w KQkq - 4 4",
    "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",
    "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2",  # en passant available
]


def test_tensor_shape_and_plane_count():
    t = board_to_tensor(chess.Board())
    assert t.shape == (15, 8, 8)
    # 32 pieces on the starting board occupy 32 cells across 12 planes.
    assert int(t[:12].sum()) == 32


def test_tensor_is_side_to_move_invariant():
    """The encoder mirrors black-to-move boards, so a position and its
    mirrored white-to-move twin must encode identically."""
    board = chess.Board(FENS[1])
    mirrored = board.mirror()
    assert np.array_equal(board_to_tensor(board),
                          board_to_tensor(mirrored))


def test_encode_decode_roundtrip():
    for fen in FENS:
        board = chess.Board(fen)
        for mv in board.legal_moves:
            if mv.promotion not in (None, chess.QUEEN):
                continue  # decode_move always assumes queen promotion
            assert decode_move(board, encode_move(board, mv)) == mv, (
                f"roundtrip failed for {mv.uci()} in {fen}"
            )


def test_legal_move_indices_match_encode():
    for fen in FENS:
        board = chess.Board(fen)
        assert set(legal_move_indices(board)) == {
            encode_move(board, m) for m in board.legal_moves
        }


def test_decode_defaults_to_queen_promotion():
    board = chess.Board("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    under = chess.Move(chess.A7, chess.A8, promotion=chess.KNIGHT)
    idx = encode_move(board, under)
    assert decode_move(board, idx) == chess.Move(
        chess.A7, chess.A8, promotion=chess.QUEEN)
