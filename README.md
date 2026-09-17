# ChessNet — Play the CNN

A polished desktop UI (PySide6) for the supervised chess CNN in this repo.

Play against the trained `ChessNet` model, watch its policy live, review
games, and learn with interactive lessons. The old tkinter GUI
(`chess_gui.py`) still works too.

## Run

```bash
pip install -r requirements.txt
python main_menu.py         # recommended entry point
python chess_app.py         # dark theme (play window only)
python chess_app.py --light # light theme
```

The first launch warm-loads the 86MB checkpoint in a background thread —
the window appears immediately.

## Features

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
  - **Show me** — plays the correct answer move on the board.
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

- **Play options**: choose White / Black / Random; Greedy vs Sampling
  AI mode; undo (full move pair); board flip.

- **Themes**: dark (default) and light, toggle live.

- **Sounds**: move / capture / check / game-end, synthesized at startup
  (no asset files). Toggle with the ♪ button.

- **Stability improvements**: AI inference runs on a worker thread, so
  the UI never freezes. Worker-thread lifetime is properly managed to
  avoid leaks when restarting games or closing windows.

## Lessons

Lessons are implemented in `lessons_window.py` and use the same animated
`BoardView` as the main game window.

Lesson content is defined in `chess_lessons.py`. Difficulty tags live in
`lesson_levels.py`. There are currently **33 lessons** covering:

- Piece movement (pawn, knight, bishop, rook, queen, king)
- Special moves (castling, en passant, promotion)
- Tactics (check, mate, fork, pin, skewer, discovered check, double check)
- Opening principles and development
- Captures, trades, and defence
- Endgame ideas (opposition, active king, pawn breaks)
- Patterns (back-rank, smothered mate ideas, rook lift, outposts)

Each lesson contains:

- a FEN position,
- a title and subtitle,
- an introduction,
- a task description,
- a hint,
- the expected answer move,
- a success message,
- and a check function that validates whether the played move solves the
  lesson.

Some lesson positions may look like “game over” positions to
python-chess, for example positions with only kings and knights. The
lesson mode allows interaction in these positions so learning puzzles
still work correctly.

**Puzzle of the Day** (`daily_puzzle.py`) picks one lesson from the full
set using today's date, so everyone gets the same puzzle on a given day.

## Keyboard

### Main menu

| Key | Action |
| --- | --- |
| Enter | Play with Model |
| Ctrl+L | Lessons |
| Ctrl+P | Puzzle of the Day |

### Main game

| Key | Action |
| --- | --- |
| Ctrl+N | New game |
| Ctrl+Z | Undo move pair |
| ← / → | Step through game history |
| Esc | Back to live position |
| F | Flip board |

### Lessons mode

| Key | Action |
| --- | --- |
| Ctrl+R | Reset current lesson |
| Ctrl+H | Ask AI for top moves |
| Ctrl+I | Show hint |
| Right | Next lesson |
| Esc | Back to main menu |

## How the model plays

`chess_ai.py` runs one forward pass per move: the board is encoded as 15
one-hot 8×8 planes — 12 piece planes plus castling rights and the
en-passant target square (`chess_utils.board_to_tensor`). `ChessNet`
outputs 4096 logits (from-square × to-square), which are softmaxed over
legal moves only. Greedy mode plays the argmax; Sampling mode
draws from the distribution. The same pass yields the top-5 shown in the
insights panel.

## Model performance

Trained on ~20k Lichess games (1.08M positions, players rated 1200+),
predicting the human move from the position, with legal-move masking
during training and a strict game-level validation split (870 games the
model never saw):

| Metric | Score |
| --- | --- |
| Top-1 accuracy | 40.9% |
| Top-5 accuracy | 76.6% |

In other words: 3 out of 4 human moves are among the model's five best
guesses. (A pre-upgrade baseline — 4k games, no masking, leaky split —
reached 32.4% top-1.)

## Recent Updates

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

### v0.2

- Sound toggle crash fixed — sound button no longer crashes when toggled
  rapidly.
- AI worker thread lifetime properly managed — no thread leaks on game
  restart.
- Promotion drag-cancel fixed — dragging promotion piece off-board no
  longer crashes.

## Training pipeline

```bash
python prepare_data.py   # all games.csv -> chess_data.npz (positions,
                         # legal-move lists, game ids)
python train.py          # masked training -> chess_model_best.pth
```

`prepare_data.py` replays every game with python-chess, encoding each
position as a 15-plane tensor and recording the full legal-move list.

`train.py` trains with masked cross-entropy (illegal moves get −1e9
logits), early-stops on validation top-1, and splits by game — never
by position — so validation is leakage-free.

## Screenshot mode

```bash
python chess_app.py --screenshot out.png --plies 16 [--light]
```

Renders the window after scripted model-vs-model plies and exits.

## Credits

- Piece art: [cburnett](https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces)
  (CC BY-SA 3.0), embedded in `ui/pieces.py` and `ui/assets/`.
- Chess rules: [python-chess](https://github.com/niklasf/python-chess).
