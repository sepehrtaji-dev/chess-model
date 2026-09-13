"""ChessNet — PySide6 front end for the CNN chess model.

Run:            python chess_app.py
Screenshot:     python chess_app.py --screenshot out.png [--plies 16] [--light]
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

import chess
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
                               QLabel, QMainWindow, QPushButton, QVBoxLayout,
                               QWidget)

from ui import theme as theme_mod
from ui.board_view import BoardView
from ui.panels import (GameOverCard, ModelPanel, MoveList, NewGameDialog,
                       PlayerCard, PromotionPicker)
from ui.sounds import SoundEngine
from ui.workers import AIWorker, ModelLoader

PIECE_VALUE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
               chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
INITIAL_COUNT = {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2,
                 chess.ROOK: 2, chess.QUEEN: 1, chess.KING: 1}


def captured_by(board, color):
    """Pieces `color` captured, as the opponent's glyphs, by falling value."""
    opp = not color
    left = Counter(p.piece_type for p in board.piece_map().values()
                   if p.color == opp)
    taken = []
    for t, n in INITIAL_COUNT.items():
        taken += [t] * max(0, n - left.get(t, 0))
    taken.sort(key=lambda t: -PIECE_VALUE[t])
    glyphs = [chess.piece_symbol(t) for t in taken]
    if opp == chess.WHITE:
        glyphs = [g.upper() for g in glyphs]
    return glyphs, sum(PIECE_VALUE[t] for t in taken)


class BoardPanel(QFrame):
    """Panel hosting the board (centered) and the game-over card overlay."""

    MARGIN = 24

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        self.board_view = BoardView(theme, self)
        lay.addWidget(self.board_view, 0, Qt.AlignCenter)
        self.overlay = None

    def register_overlay(self, card):
        self.overlay = card

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.board_view.resize_to_fit(self.width() - self.MARGIN,
                                      self.height() - self.MARGIN)
        if self.overlay is not None:
            self.overlay.recenter()


class MainWindow(QMainWindow):
    def __init__(self, theme_name="dark", interactive=True):
        super().__init__()
        self.theme = theme_mod.THEMES[theme_name]
        self.setWindowTitle("ChessNet — play the CNN")
        self.setMinimumSize(980, 660)
        self.resize(1180, 780)

        self.board = chess.Board()
        self.history = []      # [(chess.Move, san)]
        self.fens = [self.board.fen()]
        self.view_ply = None   # None = live
        self.human_color = chess.WHITE
        self.sample_mode = False
        self.ai_busy = False
        self.model_ready = False
        # self.sounds = SoundEngine()

        # Incremented every time a new game starts. AI results carry the
        # id of the game they were computed for; if a result comes back
        # after the id has moved on (user hit "New game" mid-think), it's
        # discarded instead of being applied to the wrong board.
        self._game_id = 0
        self._ai_worker = None

        self._build_ui()
        self._apply_theme()
        self._load_model_async()
        self.new_game(chess.WHITE)
        if interactive:
            QTimer.singleShot(120, self._first_run_dialog)

    # ---------- UI construction ------------------------------------------

    def _build_ui(self):
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)
        self.setCentralWidget(central)

        self.board_panel = BoardPanel(self.theme)
        root.addWidget(self.board_panel, 1)
        self.bv = self.board_panel.board_view
        self.bv.human_move.connect(self.on_human_move)
        self.bv.history_clicked.connect(self.go_live)
        self.bv.choose_promotion = self._choose_promotion

        self.game_over_card = GameOverCard(self.theme, self.board_panel)
        self.board_panel.register_overlay(self.game_over_card)
        self.game_over_card.new_game_requested.connect(self.ask_new_game)
        self.game_over_card.review_requested.connect(
            self.game_over_card.hide)

        sidebar = QWidget()
        sidebar.setFixedWidth(330)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(12)

        self.card_top = PlayerCard(self.theme)
        self.card_bottom = PlayerCard(self.theme)
        self.move_list = MoveList(self.theme)
        self.move_list.ply_selected.connect(self.set_view_ply)
        self.model_panel = ModelPanel(self.theme)

        side.addWidget(self.card_top)
        side.addWidget(self.move_list, 1)
        side.addWidget(self.model_panel)
        side.addWidget(self.card_bottom)

        controls = QFrame()
        controls.setObjectName("panel")
        cv = QVBoxLayout(controls)
        cv.setContentsMargins(12, 10, 12, 10)
        cv.setSpacing(8)
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.new_btn = QPushButton("New game")
        self.new_btn.setObjectName("primary")
        self.undo_btn = QPushButton("Undo")
        self.flip_btn = QPushButton("Flip")
        self.sound_btn = QPushButton("♪")
        self.sound_btn.setCheckable(True)
        self.sound_btn.setChecked(True)
        self.sound_btn.setFixedWidth(38)
        self.theme_btn = QPushButton("☀")
        self.theme_btn.setCheckable(True)
        self.theme_btn.setFixedWidth(38)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Greedy", "Sampling"])
        self.mode_combo.setToolTip(
            "Greedy: the model always plays its top move.\n"
            "Sampling: moves are drawn proportionally to its policy.")
        row1.addWidget(self.new_btn, 1)
        row1.addWidget(self.undo_btn, 1)
        row1.addWidget(self.flip_btn, 1)
        row2.addWidget(self.mode_combo, 1)
        row2.addWidget(self.sound_btn)
        row2.addWidget(self.theme_btn)
        cv.addLayout(row1)
        cv.addLayout(row2)
        side.addWidget(controls)

        self.status_lbl = QLabel()
        self.status_lbl.setObjectName("status")
        status_row = QHBoxLayout()
        status_row.setContentsMargins(4, 0, 4, 0)
        status_row.addWidget(self.status_lbl)
        side.addLayout(status_row)
        root.addWidget(sidebar)

        self.new_btn.clicked.connect(self.ask_new_game)
        self.undo_btn.clicked.connect(self.undo)
        self.flip_btn.clicked.connect(
            lambda: self.bv.set_flipped(not self.bv.flipped))
        self.sound_btn.toggled.connect(
            lambda on: setattr(self.sounds, "enabled", on))
        self.theme_btn.toggled.connect(self._toggle_theme)
        self.mode_combo.currentIndexChanged.connect(
            lambda i: setattr(self, "sample_mode", i == 1))

        QShortcut(QKeySequence("Ctrl+N"), self, self.ask_new_game)
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("F"), self,
                  lambda: self.bv.set_flipped(not self.bv.flipped))
        QShortcut(QKeySequence("Left"), self, lambda: self.step_ply(-1))
        QShortcut(QKeySequence("Right"), self, lambda: self.step_ply(1))
        QShortcut(QKeySequence("Escape"), self, self.go_live)

    def _apply_theme(self):
        self.setStyleSheet(theme_mod.qss(self.theme))
        self.bv.set_theme(self.theme)
        self.card_top.set_theme(self.theme)
        self.card_bottom.set_theme(self.theme)

    # ---------- model -----------------------------------------------------

    def _load_model_async(self):
        self.loader = ModelLoader()
        self.loader.loaded.connect(self._on_model_ready)
        self.loader.failed.connect(self._on_model_failed)
        self.loader.start()

    def _on_model_ready(self):
        self.model_ready = True
        self._refresh_cards()

    def _on_model_failed(self, err):
        self.set_status(f"Model failed to load: {err}", error=True)

    # ---------- game flow ---------------------------------------------------

    def _first_run_dialog(self):
        color = NewGameDialog.ask(self.theme, self, first_run=True)
        if color is not None:
            self.new_game(color)

    def ask_new_game(self):
        color = NewGameDialog.ask(self.theme, self)
        if color is not None:
            self.new_game(color)

    def new_game(self, color):
        # Bump the game id first, and clear ai_busy immediately. Any
        # AIWorker still running for the previous game will finish and
        # emit its signal eventually, but _on_ai_move / _on_ai_error will
        # see a stale game_id and drop the result instead of applying a
        # now-illegal move to this fresh board.
        self._game_id += 1
        self._ai_worker = None

        self.human_color = color
        self.board = chess.Board()
        self.history = []
        self.fens = [self.board.fen()]
        self.view_ply = None
        self.ai_busy = False
        self.game_over_card.hide()
        self.bv.human_color = color
        self.bv.set_flipped(color == chess.BLACK)
        self.bv.set_view_only(False)
        self.bv.set_position(self.board, animate=False)
        self.move_list.set_moves([])
        self.model_panel.set_idle()
        self._refresh_cards()
        self._set_controls()
        if color == chess.BLACK:
            self._trigger_ai()
        else:
            self.set_status("Your move — you play White")

    def on_human_move(self, move):
        if self.ai_busy or self.board.is_game_over():
            return
        self._apply_move(move, animate=True)
        if self.board.is_game_over():
            self._finish_game()
        else:
            self._trigger_ai()

    def _trigger_ai(self):
        self.ai_busy = True
        self.bv.set_view_only(False)
        self.card_top.set_thinking(True)
        self.model_top_pending = True
        self.model_panel.set_thinking()
        self.set_status("ChessNet is thinking…")
        self._set_controls()

        game_id = self._game_id
        self._ai_worker = AIWorker(self.board.fen(), self.sample_mode)
        self._ai_worker.finished_ok.connect(
            lambda move, top: self._on_ai_move(move, top, game_id=game_id))
        self._ai_worker.failed.connect(
            lambda err: self._on_ai_error(err, game_id=game_id))
        self._ai_worker.start()

    def _on_ai_move(self, move, top, animate=True, game_id=None):
        # game_id is None only for the scripted screenshot path, which
        # calls this directly and never races with new_game().
        if game_id is not None and game_id != self._game_id:
            return  # stale result from a game that's since been reset

        self.card_top.set_thinking(False)
        prev = self.board.copy()  # _apply_move mutates self.board in place
        san = prev.san(move)
        self._apply_move(move, animate=animate)
        rows = [(prev.san(m), p, prev.san(m) == san) for m, p in top]
        self.model_panel.set_top(rows)
        self.ai_busy = False
        self._set_controls()
        if self.board.is_game_over():
            self._finish_game()
        elif self.board.is_check():
            self.set_status("Your move — check!", error=True)
        else:
            self.set_status("Your move")

    def _on_ai_error(self, err, game_id=None):
        if game_id is not None and game_id != self._game_id:
            return  # stale error from a game that's since been reset

        self.ai_busy = False
        self.card_top.set_thinking(False)
        self._set_controls()
        self.set_status(f"Model error: {err}", error=True)

    def _apply_move(self, move, animate=True):
        prev = self.board
        was_capture = prev.is_capture(move)
        san = prev.san(move)
        self.board.push(move)
        self.history.append((move, san))
        self.fens.append(self.board.fen())
        self.view_ply = None
        self.bv.set_position(self.board, last_move=move, animate=animate)
        self.move_list.set_moves([s for _, s in self.history],
                                 len(self.history))
        self._refresh_cards()
        # if self.board.is_game_over():
        #     self.sounds.play("end")
        # elif self.board.is_check():
        #     self.sounds.play("check")
        # elif was_capture:
        #     self.sounds.play("capture")
        # else:
        #     self.sounds.play("move")

    def undo(self):
        if self.ai_busy or not self.history or self.board.is_game_over():
            return
        # revert to the human's previous turn: their move + the AI reply
        steps = 1 if self.board.turn != self.human_color else 2
        if len(self.history) < steps:
            return
        for _ in range(steps):
            self.history.pop()
            self.fens.pop()
            self.board.pop()
        self.view_ply = None
        self.game_over_card.hide()
        self.bv.set_view_only(False)
        self.bv.set_position(self.board, animate=False)
        self.move_list.set_moves([s for _, s in self.history],
                                 len(self.history))
        self._refresh_cards()
        self._set_controls()
        self.set_status("Your move")

    

    def set_view_ply(self, ply):
        if ply is None or ply >= len(self.history):
            self.go_live()
            return
        self.view_ply = max(0, ply)
        if self.view_ply == 0:
            self.bv.set_position(chess.Board(), animate=False)
        else:
            self.bv.set_position(
                chess.Board(self.fens[self.view_ply]),
                last_move=self.history[self.view_ply - 1][0], animate=False)
        self.bv.set_view_only(True)
        self.move_list.highlight(self.view_ply)
        self.set_status(f"Reviewing {self.view_ply}/{len(self.history)}"
                        "  ·  ←/→ browse, Esc live")

    def step_ply(self, delta):
        cur = self.view_ply if self.view_ply is not None \
            else len(self.history)
        self.set_view_ply(cur + delta)

    def go_live(self):
        self.view_ply = None
        self.bv.set_view_only(False)
        self.bv.set_position(self.board,
                             last_move=self.history[-1][0]
                             if self.history else None, animate=False)
        self.move_list.highlight(len(self.history))
        self.move_list.scroll_to_bottom()
        if not self.board.is_game_over():
            self.set_status("ChessNet is thinking…" if self.ai_busy
                            else "Your move")

    def _choose_promotion(self, color, to_square):
        pos = self.bv.map_square_to_global(to_square)
        size = self.bv.board_px() / 8
        return PromotionPicker.pick(self.theme, color, pos, size, self)

    # ---------- presentation ------------------------------------------------

    def _refresh_cards(self):
        my_king = "K" if self.human_color == chess.WHITE else "k"
        ai_knight = "N" if self.human_color == chess.BLACK else "n"
        my_side = "White" if self.human_color == chess.WHITE else "Black"
        ai_side = "Black" if my_side == "White" else "White"
        model_sub = (f"{ai_side} · ChessNet CNN · "
                     + ("ready" if self.model_ready else "loading weights…"))
        self.card_bottom.set_identity("You", f"{my_side} · human", my_king)
        self.card_top.set_identity("ChessNet", model_sub, ai_knight)
        my_caps, my_val = captured_by(self.board, self.human_color)
        ai_caps, ai_val = captured_by(self.board, not self.human_color)
        self.card_bottom.set_captured(my_caps, my_val - ai_val)
        self.card_top.set_captured(ai_caps, ai_val - my_val)
        over = self.board.is_game_over()
        self.card_bottom.set_turn(
            self.board.turn == self.human_color and not over)
        self.card_top.set_turn(
            self.board.turn != self.human_color and not over)

    def _finish_game(self):
        outcome = self.board.outcome(claim_draw=True)
        if outcome is None:
            return
        if outcome.winner is not None:
            human_won = outcome.winner == self.human_color
            if human_won:
                title, sub = "Checkmate — you win!", "The CNN is mated."
            else:
                title, sub = "Checkmate — ChessNet wins", "Rematch?"
        else:
            title = "Draw"
            reason = {
                chess.Termination.STALEMATE: "Stalemate",
                chess.Termination.INSUFFICIENT_MATERIAL: "Insufficient material",
                chess.Termination.SEVENTYFIVE_MOVES: "75-move rule",
                chess.Termination.FIVEFOLD_REPETITION: "Fivefold repetition",
            }.get(outcome.termination, outcome.termination.name.capitalize())
            sub = f"{reason}."
        self.set_status(f"{title} ({outcome.result()})")
        self.game_over_card.show_result(title, sub)
        self.bv.set_view_only(True)
        self._refresh_cards()
        self._set_controls()

    def _set_controls(self):
        self.undo_btn.setEnabled(
            not self.ai_busy and bool(self.history)
            and not self.board.is_game_over())

    def set_status(self, text, error=False):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(
            f"color: {self.theme.danger if error else self.theme.text};")

    def _toggle_theme(self, want_light):
        self.theme_btn.setText("☾" if want_light else "☀")
        self.theme = theme_mod.THEMES["light" if want_light else "dark"]
        self._apply_theme()


def run_screenshot(path, plies, theme_name):
    """Render the window (optionally after scripted plies) and save it."""
    from chess_ai import get_move_and_top
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow(theme_name, interactive=False)
    for _ in range(plies // 2):
        if win.board.is_game_over():
            break
        move, top = get_move_and_top(win.board, k=5, sample=False)
        win._on_ai_move(move, top, animate=False)
        app.processEvents()
        if win.board.is_game_over():
            break
        reply, _ = get_move_and_top(win.board, k=5, sample=False)
        win._apply_move(reply, animate=False)
        app.processEvents()
    win.game_over_card.hide()
    win.show()
    app.processEvents()
    QTimer.singleShot(500, lambda: (win.grab().save(str(path)), app.quit()))
    app.exec()
    print(f"saved {path}")


def main():
    parser = argparse.ArgumentParser(description="ChessNet UI")
    parser.add_argument("--screenshot", metavar="PATH",
                        help="render the window to an image and exit")
    parser.add_argument("--plies", type=int, default=16,
                        help="scripted plies before screenshot")
    parser.add_argument("--light", action="store_true",
                        help="use the light theme")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    if args.screenshot:
        run_screenshot(Path(args.screenshot), args.plies,
                       "light" if args.light else "dark")
        return
    win = MainWindow("light" if args.light else "dark")
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()