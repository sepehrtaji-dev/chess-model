import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from model import ChessNet

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BATCH_SIZE = 256
EPOCHS = 30
LR = 1e-3
PATIENCE = 6
VAL_FRACTION = 0.05
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
            logits = mask_logits(model(xb), mb)
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

    data = np.load("chess_data.npz")
    X, y = data["X"], data["y"]
    legal_flat, legal_offsets = data["legal_flat"], data["legal_offsets"]
    game_ids = data["game_ids"]

    rng = np.random.default_rng(SEED)
    games = np.unique(game_ids)
    rng.shuffle(games)
    val_count = int(len(games) * VAL_FRACTION)
    val_games = games[:val_count]
    val_idx = np.where(np.isin(game_ids, val_games))[0]
    train_idx = np.where(~np.isin(game_ids, val_games))[0]
    print(f"train positions: {len(train_idx)} | val positions: {len(val_idx)} "
          f"({val_count} games held out)")

    train_ds = ChessDataset(train_idx, X, y, legal_flat, legal_offsets)
    val_ds = ChessDataset(val_idx, X, y, legal_flat, legal_offsets)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE)

    model = ChessNet().to(DEVICE)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=3)

    best_val = 0.0
    patience_counter = 0
    for epoch in range(EPOCHS):
        train_loss, train_acc, _ = run_epoch(model, train_loader, criterion, optimizer)
        val_loss, val_acc, val_top5 = run_epoch(model, val_loader, criterion)
        scheduler.step(val_acc)
        marker = ""
        if val_acc > best_val:
            best_val = val_acc
            torch.save(model.state_dict(), "chess_model_best.pth")
            patience_counter = 0
            marker = "  <- saved"
        else:
            patience_counter += 1
        print(f"Epoch {epoch + 1}/{EPOCHS} | Train Loss: {train_loss:.4f} "
              f"Train Acc: {train_acc:.4f} | Val Acc: {val_acc:.4f} "
              f"| Val Top-5: {val_top5:.4f}{marker}", flush=True)
        if patience_counter >= PATIENCE:
            print(f"Early stopping at epoch {epoch + 1}")
            break

    print(f"\nTraining complete. Best val top-1: {best_val:.4f}")
    print("Best model saved as chess_model_best.pth")


if __name__ == "__main__":
    main()
