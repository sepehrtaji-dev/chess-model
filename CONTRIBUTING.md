# Contributing to ChessNet

This project is maintained by two people. To keep our work smooth:

## Setup

```bash
pip install -r requirements.txt
pip install chess numpy pytest   # test-only deps (torch-free suite)
pytest                           # must pass before every push
```

## Workflow

1. Branch from `master` (`feat/...`, `fix/...`).
2. Make the change; add or update tests in `tests/` when behaviour
   changes. Lesson changes **must** keep `tests/test_lessons.py`
   green — it catches unsolvable positions and wrong answer SANs.
3. Run `pytest -q` locally; CI runs the same suite on every PR.
4. Open a pull request and have the other maintainer review it.
   Two approvals are not required, but no direct pushes to `master`.

## Notes

- `data/chess_data.npz` and `checkpoints/*.pth` are gitignored — never
  commit model weights or datasets.
- Bump `version.txt` and the "Recent Updates" section of the README
  in the same PR as user-facing changes.
- Keep the torch-free test suite torch-free so CI stays fast.
