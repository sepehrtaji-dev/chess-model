"""Replay data/games.csv into data/chess_data.npz.

Each position is encoded as a 15-plane tensor; the target is the played
move index and the full legal-move list is recorded for masked training.
"""

from pathlib import Path

import chess
import numpy as np
import pandas as pd
from array import array

from chess_utils import board_to_tensor, encode_move, legal_move_indices

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "games.csv"
OUT_PATH = ROOT / "data" / "chess_data.npz"
MIN_RATING = 1200
GAMES_LIMIT = 4000  # the released model used the first 4k games rated 1200+


def main():
    if not CSV_PATH.exists():
        raise SystemExit(
            f"{CSV_PATH} not found — place a Lichess games export "
            f"(columns: white_rating, black_rating, moves) there."
        )

    df = pd.read_csv(CSV_PATH)
    df = df[(df["white_rating"] >= MIN_RATING)
            & (df["black_rating"] >= MIN_RATING)]
    df = df.head(GAMES_LIMIT)
    print(f"games: {len(df)}")

    X_list = []
    y_list = []
    game_ids = array("i")
    legal_flat = array("i")
    legal_offsets = array("q", [0])

    for i, row in enumerate(df.itertuples()):
        board = chess.Board()
        moves = str(row.moves).split()

        for san in moves:
            try:
                move = board.parse_san(san)
            except Exception:
                break

            X_list.append(board_to_tensor(board).astype(np.int8))
            y_list.append(encode_move(board, move))
            game_ids.append(i)
            legal_flat.extend(legal_move_indices(board))
            legal_offsets.append(len(legal_flat))

            board.push(move)

        if i % 500 == 0:
            print(f"{i}/{len(df)} games, {len(y_list)} positions", flush=True)

    X = np.stack(X_list)
    y = np.array(y_list, dtype=np.int32)
    game_ids = np.frombuffer(game_ids, dtype=np.int32)
    legal_flat = np.frombuffer(legal_flat, dtype=np.int32)
    legal_offsets = np.frombuffer(legal_offsets, dtype=np.int64)

    print("dataset:", X.shape, y.shape)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT_PATH, X=X, y=y, game_ids=game_ids,
                        legal_flat=legal_flat, legal_offsets=legal_offsets)
    print("saved to", OUT_PATH)


if __name__ == "__main__":
    main()
