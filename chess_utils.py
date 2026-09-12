import chess
import numpy as np


def board_to_tensor(board):
    b = board if board.turn == chess.WHITE else board.mirror()
    tensor = np.zeros((15, 8, 8), dtype=np.float32)
    for square, piece in b.piece_map().items():
        row = 7 - chess.square_rank(square)
        col = chess.square_file(square)
        idx = (piece.piece_type - 1) + (0 if piece.color == chess.WHITE else 6)
        tensor[idx, row, col] = 1.0
    if b.has_kingside_castling_rights(chess.WHITE):
        tensor[12, :] = 1.0
    if b.has_queenside_castling_rights(chess.WHITE):
        tensor[13, :] = 1.0
    if b.ep_square is not None:
        row = 7 - chess.square_rank(b.ep_square)
        col = chess.square_file(b.ep_square)
        tensor[14, row, col] = 1.0
    return tensor


def encode_move(board, move):
    if board.turn == chess.WHITE:
        frm, to = move.from_square, move.to_square
    else:
        frm, to = chess.square_mirror(
            move.from_square), chess.square_mirror(move.to_square)
    return frm * 64 + to


def decode_move(board, idx):
    frm, to = idx // 64, idx % 64
    if board.turn == chess.BLACK:
        frm, to = chess.square_mirror(frm), chess.square_mirror(to)
    piece = board.piece_at(frm)
    if piece and piece.piece_type == chess.PAWN and chess.square_rank(to) in (0, 7):
        return chess.Move(frm, to, promotion=chess.QUEEN)
    return chess.Move(frm, to)


def legal_move_indices(board):
    if board.turn == chess.WHITE:
        return [m.from_square * 64 + m.to_square for m in board.legal_moves]
    return [chess.square_mirror(m.from_square) * 64
            + chess.square_mirror(m.to_square) for m in board.legal_moves]
