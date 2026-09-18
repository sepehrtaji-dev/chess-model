# ChessNet — Play the CNN

A polished desktop UI (PySide6) for the supervised chess CNN in this repo.
Play against the trained `ChessNet` model, play pass-and-play with a
friend on one board, watch the model's policy live, review games, export
them to PGN, and learn with interactive lessons. The old tkinter GUI
(`chess_gui.py`) still works too.

![dark theme](shot1.png)

## Run

### Docker

Build the image:

```bash
docker build -t chessnet:0.7 .
```

The GUI needs access to a display server. On Linux with X11, run:

```bash
xhost +local:docker
docker run --rm -it \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v "$(pwd)/checkpoints:/app/checkpoints:ro" \
  chessnet:0.7
```

The trained checkpoint is intentionally not included in the image. Mount
`checkpoints/` as shown above so `checkpoints/chess_model_best.pth`
is available at runtime.


Requires **Python 3.10+**.

```bash
pip install -r requirements.txt
python main_menu.py         # recommended entry point
python chess_app.py         # dark theme (play window only)
python chess_app.py --light # light theme
```

You need a trained checkpoint at `checkpoints/chess_model_best.pth`
(86 MB). If it is missing, the app tells you exactly what to run:

```bash
python prepare_data.py      # data/games.csv -> data/chess_data.npz
python train.py             # masked training -> checkpoints/chess_model_best.pth
```

## Features

- **Two-player pass & play**: share the board with a friend — control
  flips to the side to move after every move. The model can still coach
  both sides.

- **Hint**: ask ChessNet for its best move in any position
  (**Ctrl+H**), with the policy confidence shown in the insights panel.

- **PGN export**: save the current game to a `.pgn` file
  (**Ctrl+S** or the PGN button) — open it in any chess tool.

- **Puzzle of the Day**: each calendar day maps to one of the 33 lessons
  (deterministic). Open it from the main menu card or with **Ctrl+P**.

- **Interactive Lessons**: a learning mode with **33 structured chess
  puzzles**. Each lesson gives you a position, a task, hints, and live
  ChessNet coaching. If you make a wrong move, the model can explain why
  the move is not the teaching idea and suggest better candidate moves.
  You can also press **Show me** to watch the correct move animated on
  the board.

- **Lesson levels & progress**:
  - Filter by **Beginner / Intermediate / Advanced**
  - **Random** lesson button (prefers unsolved)
  - Progress saved to `~/.chessnet_lesson_progress.json`

- **Lesson coaching tools**:
  - **Ask AI** — asks ChessNet for its top candidate moves.
  - **Hint** — shows the lesson hint.
  - **Show me** — plays the correct answer move animated on the board.
  - **Reset** — restarts the current lesson.
  - **Progress tracking** — solved lessons are marked in the lesson list.

- **Board**: SVG pieces (cburnett set), drag & drop or click-to-move,
  legal-move dots, capture rings, last-move + check highlights, smooth
  animated moves (with capture fades and castling), promotion picker.

- **Model insights**: after every AI reply, the panel shows the model's
  top-5 candidate moves with animated softmax probability bars — you can
  literally watch the network's policy.

- **Move list**: numbered SAN moves; click any move (or use ←/→, Esc for
  live) to review earlier positions.

- **Player cards**: avatars, captured pieces, material advantage,
  turn indicator, "thinking" state.

- **Play options**: choose White / Black / Random or **two players**;
  Low / Medium / High AI effort; undo (full move pair); board flip;
  animation toggle.

- **Themes**: dark (default) and light, toggle live.

- **Sounds**: move / capture / check / game-end, synthesized at startup
  (no asset files). Toggle with the ♪ button.

- **Stability improvements**: AI inference runs on a worker thread, so
  the UI never freezes. Worker-thread lifetime is properly managed to
  avoid leaks when restarting games or closing windows.

### AI Difficulty & Analysis (v0.8+)

- **AI Difficulty Slider**: Smooth five-step difficulty slider
  (Easy / Casual / Medium / Hard / Expert) replacing the old combo box.
  The slider controls how strongly ChessNet plays — sampling, safeguards,
  and move selection all adapt smoothly.

- **AI Styles**: Choose from five distinct playing styles:
  - **Balanced** — solid, principled play
  - **Aggressive** — prefers attacks, sacrifices, and complications
  - **Defensive** — solid, prophylactic, safety-first
  - **Tactical** — seeks tactics, sacrifices, and sharp play
  - **Positional** — long-term strategy, prophylaxis, structure

- **Adaptive Difficulty**: optional mode that adjusts AI strength
  dynamically based on your play — ramps up when you're winning,
  eases off when you're struggling.

- **Animated Evaluation Bar**: live position evaluation bar that
  smoothly animates between scores, showing White/Black advantage
  in real-time during play.

- **Animated Position Evaluation & Live AI Thinking Telemetry**:
  watch the evaluation bar animate smoothly as the AI thinks, with
  live updates showing the AI's thought process.

- **Move Quality Feedback & Game Analysis**: after the game, get a
  detailed post-game analysis with:
  - **Accuracy score** (percentage of moves matching or near ChessNet's top choices)
  - **Best moves** / **Inaccuracies** / **Mistakes** / **Blunders** counts
  - Per-move quality labels: **Excellent**, **Good**, **Inaccuracy**, **Mistake**, **Blunder**
  - Per-move comparison: your move vs. ChessNet's best move
  - Coach summary with actionable feedback

- **Move Quality Feedback**: after each move, see instant feedback
  (Excellent / Good / Inaccuracy / Mistake / Blunder) with the
  engine's preferred move shown.

- **Game Analysis Dialog**: post-game analysis dialog showing
  accuracy, move-by-move breakdown, and coach feedback.

- **Adaptive Difficulty Mode**: optional mode that adjusts AI
  strength dynamically based on your performance.

- **Persistent Player Statistics**: accuracy tracking and
  game-by-game history saved across sessions.

- **Animated Position Evaluation & Live AI Thinking Telemetry**:
  evaluation bar updates in real-time with smooth animation during
  AI thinking.

- **Evaluation Bar Animation**: smooth, animated evaluation bar
  that smoothly transitions between scores.

- **AI Styles**: five distinct playing styles (Balanced, Aggressive,
  Defensive, Tactical, Positional) implemented as distinct search
  and evaluation parameter profiles.

- **Adaptive Difficulty Mode**: optional auto-adjusting difficulty
  that scales with your performance.

- **Persistent Player Statistics**: accuracy tracking and
  game-by-game history saved across sessions.

- **Animated Position Evaluation & Live AI Thinking Telemetry**:
  evaluation bar updates in real-time with smooth animation during
  AI thinking.

- **Evaluation Bar Animation**: smooth, animated evaluation bar
  that smoothly transitions between scores.

- **AI Styles**: five distinct playing styles (Balanced, Aggressive,
  Defensive, Tactical, Positional) implemented as distinct search
  and evaluation parameter profiles.

- **Adaptive Difficulty Mode**: optional auto-adjusting difficulty
  that scales with your performance.

- **Persistent Player Statistics**: accuracy tracking and
  game-by-game history saved across sessions.

## Model performance

Trained on ~20k Lichess games (1.08M positions, players rated 1200+),
predicting the human move from the position, with legal-move masking
during training and a strict game-level validation split (870 games the
model never saw):

| Metric | Score |
|---|---|
| Top-1 accuracy | 40.9% |
| Top-5 accuracy | 76.6% |

In other words: 3 out of 4 human moves are among the model's five best
guesses. (A pre-upgrade baseline — 4k games, no masking, leaky split —
reached 32.4% top-1.)

## Training pipeline

```bash
python prepare_data.py   # all games.csv -> chess_data.npz (positions,
                         # legal-move lists, game ids)
python train.py          # masked training -> chess_model_best.pth
```

`prepare_data.py` replays every game with python-chess, encoding each
position as a 15-plane tensor and recording the full legal-move list.

`train.py` trains with masked cross-entropy (illegal moves get −1e9
logits), evaluates masked top-1/top-5 on a strict game-level validation
split (5% of games the model never saw), early-stops on validation
top-1 with an LR plateau scheduler, and saves the **best** checkpoint —
not the last one.

## Tests & CI

The lesson content, move encoding and daily puzzle are covered by a
torch-free test suite (lesson positions were regression-prone — several
shipped positions were mathematically unsolvable before v0.6):

```bash
pip install chess numpy pytest
pytest
```

A GitHub Actions workflow (`.github/workflows/ci.yml`) runs the suite
on every push and pull request.

## Screenshot mode

```bash
python chess_app.py --screenshot out.png --plies 16 [--light]
```

Renders the window after scripted model-vs-model plies and exits.

## Recent Updates

### v0.8 — AI Upgrade

- Replaced the difficulty ComboBox with a smooth five-step AI difficulty slider.
- Added AI styles: Balanced, Aggressive, Defensive, Tactical, and Positional.
- Added adaptive difficulty mode.
- Added animated position evaluation and live AI thinking telemetry.
- Added move-quality feedback and a game analysis view.
- Added persistent player statistics and accuracy tracking.

### v0.7 — Docker support

- Added a production-ready `Dockerfile` for the ChessNet desktop app.
- Documented Linux/X11 Docker usage and read-only checkpoint mounting.
- The image uses Python 3.11 and installs the system libraries required by PySide6.

### v0.6 — Bug-fix release, two-player mode & quality-of-life

**Fixed**

- Seven lesson positions were mathematically broken and shipped
  unsolvable or misleading: **Discovered Check** and **Double Check**
  (the bishop could never check the king on e8), **Queen Checkmate**
  (no mate-in-1 existed), **Pin** and **Skewer** (the "answer" was a
  plain capture, not a pin/skewer), plus the **Fork** position (white
  started in check with the knight pinned) and **Trading Pieces**
  (the knights did not attack each other). All 33 lessons are now
  covered by regression tests (`tests/`).
- The **Hint** button in lessons visually revealed the answer on the
  board — it now shows only the text hint.
- Closing the play/lessons window left the hidden main menu running
  with no way back (zombie app). Both windows now return to the menu,
  from the close button, the X button, or the new **☰ Menu** button.
- Background AI threads are now waited on window close — closing
  mid-inference no longer risks a "QThread destroyed while running"
  crash.
- The move-coaching evaluation ran a model forward pass **on the UI
  thread** on every human move (UI freeze). It now runs on a worker.
- The sound engine existed but was never created — the ♪ button toggled
  nothing. Sounds are now actually wired: move, capture, check and
  game-end.
- `train.py` multiplied logits by the 0/1 legal mask instead of
  masking with −1e9, ran a second unmasked forward pass per batch,
  never used its early-stopping/scheduler definitions, saved the last
  instead of the best model, and crashed on CPU-only machines
  (hardcoded `cuda`). Fully rewritten.
- `prepare_data.py` executed at import time and used cwd-relative
  paths; both pipeline scripts now use script-relative paths and a
  `main()` guard.
- A missing checkpoint now produces a clear, actionable error message.
- The play board no longer allows interaction after the game ended.
- Undo now works after game over (to take back a mate).

**Added**

- **Two-player pass & play** mode in the new-game dialog.
- **Hint** button in the play window (Ctrl+H).
- **PGN export** (Ctrl+S).
- **Animation toggle** button.
- **Settings persistence** (theme, sound, animations, AI effort) in
  `~/.chessnet_settings.json`.
- Torch-free test suite (`tests/`, 160+ tests) and a GitHub Actions
  CI workflow.
- Progress saving now happens on lesson close as well.

### v0.5 — Puzzle of the Day & Lesson Levels

- Added **Puzzle of the Day** on the main menu (daily lesson from date).
- Added lesson difficulty levels with filter and Random button.
- Lesson progress persists across sessions.

### v0.4 — Expanded Lessons

- Expanded the interactive lesson set from 13 to **33 lessons**.
- Added new lessons covering captures, pins, skewers, discovered and
  double checks, queenside castling, centre control, development,
  trading, defence, opposition, rook lifts, outposts, back-rank threats,
  pawn breaks, active king, and more mating patterns.

### v0.3 — Lessons Update

- Added a full **Interactive Lessons** mode.
- Added live ChessNet coaching for wrong lesson moves.
- Added **Ask AI**, **Hint**, **Show me**, and **Reset** lesson controls.
- Added lesson progress tracking and solved-lesson checkmarks.
- Added lesson keyboard shortcuts.
- Fixed lesson board interaction for positions that python-chess marks
  as game over because of insufficient material.
- Improved board click handling so pieces remain clickable in lesson
  puzzles.
- Improved lesson state handling so the board does not stay locked after
  wrong moves, AI hints, or answer animations.
- Improved lesson state handling so the board does not stay locked after
  wrong moves, AI hints, or answer animations.

### v0.2

- Sound toggle crash fixed — sound button no longer crashes when toggled
  rapidly.
- AI worker thread lifetime properly managed — no thread leaks on game
  restart.
- Promotion drag-cancel fixed — dragging promotion piece off-board no
  longer crashes.

## Model performance

Trained on ~20k Lichess games (1.08M positions, players rated 1200+),
predicting the human move from the position, with legal-move masking
during training and a strict game-level validation split (870 games the
model never saw):

| Metric | Score |
|---|---|
| Top-1 accuracy | 40.9% |
| Top-5 accuracy | 76.6% |

In other words: 3 out of 4 human moves are among the model's five best
guesses. (A pre-upgrade baseline — 4k games, no masking, leaky split —
reached 32.4% top-1.)

## Training pipeline

```bash
python prepare_data.py   # all games.csv -> chess_data.npz (positions,
                         # legal-move lists, game ids)
python train.py          # masked training -> chess_model_best.pth
```

`prepare_data.py` replays every game with python-chess, encoding each
position as a 15-plane tensor and recording the full legal-move list.

`train.py` trains with masked cross-entropy (illegal moves get −1e9
logits), evaluates masked top-1/top-5 on a strict game-level validation
split (5% of games the model never saw), early-stops on validation
top-1 with an LR plateau scheduler, and saves the **best** checkpoint —
not the last one.

## Tests & CI

The lesson content, move encoding and daily puzzle are covered by a
torch-free test suite (lesson positions were regression-prone — several
shipped positions were mathematically unsolvable before v0.6):

```bash
pip install chess numpy pytest
pytest
```

A GitHub Actions workflow (`.github/workflows/ci.yml`) runs the suite
on every push and pull request.

## Screenshot mode

```bash
python chess_app.py --screenshot out.png --plies 16 [--light]
```

Renders the window after scripted model-vs-model plies and exits.

## AI Assistance

This project was developed with assistance from multiple AI systems during different stages of coding, debugging, documentation, and feature development:

- **ChatGPT 5.6**
- **Claude Sonnet 5**
- **Qwen 3.8 Max**
- **Grok**
- **GLM**

These AI systems were used as development assistants; the project code and final integration were reviewed and maintained by the project contributors.

## Credits

- Piece art: [cburnett](https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces)
  (CC BY-SA 3.0), embedded in `ui/pieces.py` and `ui/assets/`.
- Chess rules: [python-chess](https://github.com/niklasf/python-chess).

## Maintainers

- [@sepehrtaji-dev](https://github.com/sepehrtaji-dev) — original author
- [@MarziehNaseri2022](https://github.com/MarziehNaseri2022) — fixes, tests,
  two-player mode, PGN export, settings