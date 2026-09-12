import chess
import pandas as pd
import numpy as np
from chess_utils import board_to_tensor, encode_move

CSV_PATH = "games.csv"
MAX_GAMES = 30000
MIN_RATING = 1200
OUT_PATH = "chess_data.npz"

df = pd.read_csv(CSV_PATH)
df = df[(df["white_rating"] >= MIN_RATING) &
        (df["black_rating"] >= MIN_RATING)]
df = df.head(MAX_GAMES)

X_list = []
y_list = []

for i, row in enumerate(df.itertuples()):
    board = chess.Board()
    moves = str(row.moves).split()

    for san in moves:
        try:
            move = board.parse_san(san)
        except Exception:
            break

        X_list.append(board_to_tensor(board))
        y_list.append(encode_move(board, move))

        board.push(move)

    if i % 500 == 0:
        print(f"Processed {i}/{len(df)} games, {len(y_list)} positions so far")

X = np.stack(X_list).astype(np.int8)
y = np.array(y_list, dtype=np.int16)

print("Final dataset:", X.shape, y.shape)
np.savez_compressed(OUT_PATH, X=X, y=y)
print("Saved to", OUT_PATH)
