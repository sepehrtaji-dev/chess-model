import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader, random_split
from model import ChessNet

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BATCH_SIZE = 256
EPOCHS = 15
LR = 1e-3
patience = 3

data = np.load("chess_data.npz")
X = torch.tensor(data["X"], dtype=torch.float32)
y = torch.tensor(data["y"], dtype=torch.long)

dataset = TensorDataset(X, y)
val_size = int(len(dataset) * 0.05)
train_size = len(dataset) - val_size
train_ds, val_ds = random_split(dataset, [train_size, val_size])

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

model = ChessNet().to(DEVICE)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)

patience_counter = 0
best_val_acc = 0
for epoch in range(EPOCHS):
    model.train()
    total_loss, correct, total = 0, 0, 0
    for xb, yb in train_loader:
        xb, yb = xb.to(DEVICE), yb.to(DEVICE)
        optimizer.zero_grad()
        out = model(xb)
        loss = criterion(out, yb)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * xb.size(0)
        correct += (out.argmax(1) == yb).sum().item()
        total += xb.size(0)

    model.eval()
    val_correct, val_total = 0, 0
    with torch.no_grad():
        for xb, yb in val_loader:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            out = model(xb)
            val_correct += (out.argmax(1) == yb).sum().item()
            val_total += xb.size(0)

    print(f"Epoch {epoch+1}/{EPOCHS} | Train Loss: {total_loss/total:.4f} "
          f"Train Acc: {correct/total:.4f} | Val Acc: {val_correct/val_total:.4f}")
    if val_correct/val_total > best_val_acc:
        best_val_acc = val_correct/val_total
        torch.save(model.state_dict(), "chess_model_best.pth")
        patience_counter = 0
    else:
        patience_counter += 1
        if patience_counter >= patience:
            print(
                f"Early stopping at epoch {epoch+1}, best val acc: {best_val_acc:.4f}")
            break

torch.save(model.state_dict(), "chess_model.pth")
print("Saved chess_model.pth")
