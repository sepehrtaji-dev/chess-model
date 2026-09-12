import chess
import numpy as np
import pandas as pd
from array import array

from chess_utils import board_to_tensor, encode_move, legal_move_indices

CSV_PATH = "games.csv"
MIN_RATING = 1200
OUT_PATH = "chess_data.npz"

df = pd.read_csv(CSV_PATH)
df = df[(df["white_rating"] >= MIN_RATING)
        & (df["black_rating"] >= MIN_RATING)]
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

    if i % 2000 == 0:
        print(f"{i}/{len(df)} games, {len(y_list)} positions", flush=True)

X = np.stack(X_list)
y = np.array(y_list, dtype=np.int32)
game_ids = np.frombuffer(game_ids, dtype=np.int32)
legal_flat = np.frombuffer(legal_flat, dtype=np.int32)
legal_offsets = np.frombuffer(legal_offsets, dtype=np.int64)

print("dataset:", X.shape, y.shape)
np.savez_compressed(OUT_PATH, X=X, y=y, game_ids=game_ids,
                    legal_flat=legal_flat, legal_offsets=legal_offsets)
print("saved to", OUT_PATH)
