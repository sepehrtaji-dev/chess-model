"""Masked training for ChessNet.

Game-level validation split, masked cross-entropy over legal moves,
early stopping on masked validation top-1, best checkpoint saving.
"""

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from model import ChessNet

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "chess_data.npz"
CHECKPOINT_PATH = ROOT / "checkpoints" / "chess_model_best.pth"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BATCH_SIZE = 256
EPOCHS = 30
LR = 1e-3
WEIGHT_DECAY = 1e-4
PATIENCE = 6            # early stopping on validation top-1
VAL_FRACTION = 0.05     # fraction of GAMES held out for validation
NEG = -1e9
SEED = 42


class ChessDataset(Dataset):
    def __init__(self, indices, X, y, legal_flat, legal_offsets):
        self.indices = indices
        self.X = X
        self.y = y
        self.legal_flat = legal_flat
        self.legal_offsets = legal_offsets

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, i):
        idx = self.indices[i]
        mask = np.zeros(4096, dtype=np.float32)
        start, end = self.legal_offsets[idx], self.legal_offsets[idx + 1]
        mask[self.legal_flat[start:end]] = 1.0
        return (torch.from_numpy(self.X[idx].astype(np.float32)),
                torch.tensor(self.y[idx], dtype=torch.long),
                torch.from_numpy(mask))


def mask_logits(logits, mask):
    return logits.masked_fill(mask == 0, NEG)


def accuracy(logits, yb, k=None):
    """Top-1 (or top-k) accuracy; call AFTER mask_logits()."""
    if k is None:
        return (logits.argmax(1) == yb).float().mean().item()
    topk = logits.topk(k, dim=1).indices
    return (topk == yb.unsqueeze(1)).any(1).float().mean().item()


def run_epoch(model, loader, criterion, optimizer=None):
    training = optimizer is not None
    model.train() if training else model.eval()
    total_loss, top1, top5, n = 0.0, 0, 0, 0
    with torch.set_grad_enabled(training):
        for xb, yb, mb in loader:
            xb, yb, mb = xb.to(DEVICE), yb.to(DEVICE), mb.to(DEVICE)
            logits = mask_logits(model(xb), mb)  # single forward pass
            loss = criterion(logits, yb)
            if training:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            bs = xb.size(0)
            total_loss += loss.item() * bs
            top1 += (logits.argmax(1) == yb).sum().item()
            top5 += accuracy(logits, yb, k=5) * bs
            n += bs
    return total_loss / n, top1 / n, top5 / n


def main():
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    rng = np.random.default_rng(SEED)

    if not DATA_PATH.exists():
        raise SystemExit(
            f"{DATA_PATH.name} not found — run `python prepare_data.py` first."
        )
    data = np.load(DATA_PATH)
    X, y = data["X"], data["y"]
    legal_flat, legal_offsets = data["legal_flat"], data["legal_offsets"]
    game_ids = data["game_ids"]

    # Strict game-level split: a game never appears in both splits.
    games = np.unique(game_ids)
    rng.shuffle(games)
    val_count = max(1, int(len(games) * VAL_FRACTION))
    val_games = games[:val_count]
    val_mask = np.isin(game_ids, val_games)
    val_idx = np.where(val_mask)[0]
    train_idx = np.where(~val_mask)[0]
    print(f"device: {DEVICE} | train positions: {len(train_idx)} | "
          f"val positions: {len(val_idx)} ({val_count} games held out)")

    train_ds = ChessDataset(train_idx, X, y, legal_flat, legal_offsets)
    val_ds = ChessDataset(val_idx, X, y, legal_flat, legal_offsets)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE)

    model = ChessNet().to(DEVICE)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR,
                                  weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=3)

    best_val = 0.0
    patience_left = PATIENCE
    for epoch in range(EPOCHS):
        train_loss, train_top1, train_top5 = run_epoch(
            model, train_loader, criterion, optimizer)
        with torch.no_grad():
            val_loss, val_top1, val_top5 = run_epoch(
                model, val_loader, criterion)
        scheduler.step(val_top1)

        marker = ""
        if val_top1 > best_val:
            best_val = val_top1
            patience_left = PATIENCE
            CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), CHECKPOINT_PATH)
            marker = "  <- saved"
        else:
            patience_left -= 1

        print(f"Epoch {epoch + 1}: train_loss={train_loss:.4f} "
              f"train_top1={train_top1:.4f} train_top5={train_top5:.4f} | "
              f"val_loss={val_loss:.4f} val_top1={val_top1:.4f} "
              f"val_top5={val_top5:.4f}{marker}", flush=True)

        if patience_left <= 0:
            print(f"Early stopping — no val improvement for {PATIENCE} epochs.")
            break

    print(f"Best masked val top-1: {best_val:.4f}")
    print(f"Checkpoint: {CHECKPOINT_PATH}")


if __name__ == "__main__":
    main()
