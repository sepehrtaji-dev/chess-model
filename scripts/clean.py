import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder

df = pd.read_csv("data/games.csv")

print("Initial shape:", df.shape)

df = df.drop_duplicates()
df = df.drop_duplicates(subset=["id"])
df = df.dropna()

df = df[df["turns"] > 0]
df = df[df["white_rating"].between(400, 3200)]
df = df[df["black_rating"].between(400, 3200)]
df = df[df["moves"].str.strip().str.len() > 0]

df["created_at"] = pd.to_numeric(df["created_at"], errors="coerce")
df["last_move_at"] = pd.to_numeric(df["last_move_at"], errors="coerce")
df = df.dropna(subset=["created_at", "last_move_at"])
df = df[df["last_move_at"] >= df["created_at"]]

df["rated"] = df["rated"].astype(str).str.upper().map({"TRUE": 1, "FALSE": 0})
df = df.dropna(subset=["rated"])
df["rated"] = df["rated"].astype(int)

df[["increment_base", "increment_bonus"]] = df["increment_code"].str.split(
    "+", expand=True).astype(int)
df = df.drop(columns=["increment_code"])

df["n_moves_played"] = df["moves"].apply(lambda x: len(x.split()))
df["first_move"] = df["moves"].apply(lambda x: x.split()[0])
df["last_move"] = df["moves"].apply(lambda x: x.split()[-1])

df = df.drop(columns=["id", "moves"])

df = df.reset_index(drop=True)

string_cols = df.select_dtypes(include="object").columns.tolist()
print("\nString columns found and will be encoded:", string_cols)

encoders = {}
for col in string_cols:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col].astype(str))
    encoders[col] = le

    mapping_df = pd.DataFrame({
        col: le.classes_,
        col + "_code": range(len(le.classes_))
    })
    mapping_df.to_csv(f"mapping_{col}.csv", index=False)

print("\nRemaining dtypes:")
print(df.dtypes)

assert df.select_dtypes(
    include="object").shape[1] == 0, "There are still string columns left!"

print("\nFinal shape:", df.shape)
df.to_csv("games_cleaned.csv", index=False)
print("Saved fully numeric dataset to games_cleaned.csv")
