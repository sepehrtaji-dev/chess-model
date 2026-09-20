"""ChessNet — PySide6 front end for the CNN chess model."""

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

import chess
import chess.pgn
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFrame,
                               QHBoxLayout, QLabel, QMainWindow, QPushButton,
                               QVBoxLayout, QWidget)
import chess_coach
import settings as settings_mod
from ui import theme as theme_mod
from ui.board_view import BoardView
from ui.panels import (GameOverCard, ModelPanel, MoveList, NewGameDialog,
                       PlayerCard, PromotionPicker)
from ui.sounds import SoundEngine
from ui.advanced import AnalysisDialog, DifficultySlider, EvaluationBar
from ai_features import normalized_evaluation, move_quality
from ui.workers import AIWorker, HintWorker, ModelLoader

PIECE_VALUE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
               chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
INITIAL_COUNT = {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2,
                 chess.ROOK: 2, chess.QUEEN: 1, chess.KING: 1}


def captured_by(board, color):
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
    back_requested = Signal()

    def __init__(self, theme_name="dark", interactive=True, has_menu=False):
        super().__init__()
        self.theme = theme_mod.THEMES[theme_name]
        self.setWindowTitle("ChessNet — play the CNN")
        self.setMinimumSize(980, 660)
        self.resize(1180, 780)
        self.has_menu = has_menu

        self.board = chess.Board()
        self.history = []
        self.fens = [self.board.fen()]
        self.view_ply = None
        self.human_color = chess.WHITE
        self.mode = "ai"          # "ai" | "two" | "ai_ai"
        saved_settings = settings_mod.load()
        self.difficulty = saved_settings["difficulty"]
        self.difficulty_value = saved_settings["difficulty_value"]
        self.ai_style = saved_settings["ai_style"]
        self.adaptive = saved_settings["adaptive"]
        self.ai_busy = False
        self.model_ready = False
        self._last_coach = None
        self._human_move_ranks = []
        self._think_started = None
        self._thinking_timer = None
        self._ai_move_count = 0
        self._ai_think_times = []

        self._game_id = 0
        self._ai_workers = set()
        self._hint_worker = None

        self.sounds = SoundEngine()

        self._build_ui()
        self._apply_theme()
        # The play board must block interaction once the game is over;
        # lessons need the permissive flag instead.
        self.bv.allow_game_over_positions = False
        self._load_model_async()
        self.new_game(chess.WHITE)
        if interactive:
            QTimer.singleShot(120, self._first_run_dialog)

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

        self.menu_btn = QPushButton("☰ Menu")
        self.menu_btn.setToolTip("Back to the main menu (window close works too)")
        self.menu_btn.setVisible(self.has_menu)
        side.addWidget(self.menu_btn)

        self.card_top = PlayerCard(self.theme)
        self.card_bottom = PlayerCard(self.theme)
        self.move_list = MoveList(self.theme)
        self.move_list.ply_selected.connect(self.set_view_ply)
        self.model_panel = ModelPanel(self.theme)
        self.eval_bar = EvaluationBar(self.theme)

        side.addWidget(self.card_top)
        side.addWidget(self.move_list, 1)
        side.addWidget(self.eval_bar)
        side.addWidget(self.model_panel)
        side.addWidget(self.card_bottom)

        controls = QFrame()
        controls.setObjectName("panel")
        cv = QVBoxLayout(controls)
        cv.setContentsMargins(12, 10, 12, 10)
        cv.setSpacing(8)
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row3 = QHBoxLayout()
        row3.setSpacing(8)
        self.new_btn = QPushButton("New game")
        self.new_btn.setObjectName("primary")
        self.undo_btn = QPushButton("Undo")
        self.flip_btn = QPushButton("Flip")
        self.hint_btn = QPushButton("Hint")
        self.analyze_btn = QPushButton("Analyze")
        self.pgn_btn = QPushButton("PGN")
        self.sound_btn = QPushButton("♪")
        self.sound_btn.setCheckable(True)
        self.sound_btn.setChecked(settings_mod.load()["sound"])
        self.sound_btn.setFixedWidth(38)
        self.anim_btn = QPushButton("✦")
        self.anim_btn.setCheckable(True)
        self.anim_btn.setChecked(settings_mod.load()["animations"])
        self.anim_btn.setFixedWidth(38)
        self.anim_btn.setToolTip("Toggle move animations")
        self.theme_btn = QPushButton("☀")
        self.theme_btn.setCheckable(True)
        self.theme_btn.setFixedWidth(38)

        self.diff_slider = DifficultySlider(
            self.theme,
            DifficultySlider.value_for(self.difficulty)
        )
        self.style_combo = QComboBox()
        self.style_combo.addItems(
            [chess_coach.STYLES[k] for k in chess_coach.STYLES])
        self.style_combo.setCurrentIndex(
            list(chess_coach.STYLES).index(self.ai_style))
        self.style_combo.setToolTip("Choose ChessNet's playing style.")
        self.adaptive_btn = QPushButton("Adaptive")
        self.adaptive_btn.setCheckable(True)
        self.adaptive_btn.setChecked(self.adaptive)
        self.adaptive_btn.setToolTip(
            "Let ChessNet gently adjust difficulty based on your performance."
        )

        row1.addWidget(self.new_btn, 1)
        row1.addWidget(self.undo_btn, 1)
        row1.addWidget(self.flip_btn, 1)
        row2.addWidget(self.hint_btn, 1)
        row2.addWidget(self.analyze_btn, 1)
        row2.addWidget(self.pgn_btn, 1)
        cv.addWidget(self.diff_slider)
        row3.addWidget(self.style_combo, 1)
        row3.addWidget(self.adaptive_btn)
        row3.addWidget(self.anim_btn)
        row3.addWidget(self.sound_btn)
        row3.addWidget(self.theme_btn)
        cv.addLayout(row1)
        cv.addLayout(row2)
        cv.addLayout(row3)
        side.addWidget(controls)

        self.status_lbl = QLabel()
        self.status_lbl.setObjectName("status")
        status_row = QHBoxLayout()
        status_row.setContentsMargins(4, 0, 4, 0)
        status_row.addWidget(self.status_lbl)
        side.addLayout(status_row)

        self.coach_lbl = QLabel("")
        self.coach_lbl.setObjectName("caption")
        self.coach_lbl.setWordWrap(True)
        self.coach_lbl.setContentsMargins(4, 0, 4, 0)
        side.addWidget(self.coach_lbl)

        root.addWidget(sidebar)

        self.menu_btn.clicked.connect(self.close)
        self.new_btn.clicked.connect(self.ask_new_game)
        self.undo_btn.clicked.connect(self.undo)
        self.flip_btn.clicked.connect(
            lambda: self.bv.set_flipped(not self.bv.flipped))
        self.hint_btn.clicked.connect(self.ask_hint)
        self.analyze_btn.clicked.connect(self.analyze_game)
        self.pgn_btn.clicked.connect(self.save_pgn)
        self.sound_btn.toggled.connect(self._toggle_sound)
        self.anim_btn.toggled.connect(self._toggle_animations)
        self.theme_btn.toggled.connect(self._toggle_theme)
        self.style_combo.currentIndexChanged.connect(self._on_style_changed)
        self.adaptive_btn.toggled.connect(self._toggle_adaptive)
        self.diff_slider.changed.connect(self._on_difficulty_changed)

        QShortcut(QKeySequence("Ctrl+N"), self, self.ask_new_game)
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+H"), self, self.ask_hint)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_pgn)
        QShortcut(QKeySequence("F"), self,
                  lambda: self.bv.set_flipped(not self.bv.flipped))
        QShortcut(QKeySequence("Left"), self, lambda: self.step_ply(-1))
        QShortcut(QKeySequence("Right"), self, lambda: self.step_ply(1))
        QShortcut(QKeySequence("Escape"), self, self.go_live)
        QShortcut(QKeySequence("1"), self,
                  lambda: self.diff_slider.set_level("easy"))
        QShortcut(QKeySequence("2"), self,
                  lambda: self.diff_slider.set_level("casual"))
        QShortcut(QKeySequence("3"), self,
                  lambda: self.diff_slider.set_level("medium"))
        QShortcut(QKeySequence("4"), self,
                  lambda: self.diff_slider.set_level("hard"))
        QShortcut(QKeySequence("5"), self,
                  lambda: self.diff_slider.set_level("expert"))

        # setChecked() above fired before the toggled hooks existed, so
        # sync the engine/flag to the restored settings explicitly.
        self.sounds.enabled = self.sound_btn.isChecked()
        self.bv.animations_enabled = self.anim_btn.isChecked()
        self.diff_slider.set_mood(self.difficulty_value, self.ai_style, reset_history=True)
        self._refresh_evaluation(animate=False)

    def _apply_theme(self):
        self.setStyleSheet(theme_mod.qss(self.theme))
        self.bv.set_theme(self.theme)
        self.card_top.set_theme(self.theme)
        self.card_bottom.set_theme(self.theme)
        self.eval_bar.set_theme(self.theme)
        self.diff_slider.set_theme(self.theme)

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

    def _first_run_dialog(self):
        mode, color = NewGameDialog.ask(self.theme, self, first_run=True)
        if color is not None:
            self.new_game(color, mode=mode)

    def ask_new_game(self):
        mode, color = NewGameDialog.ask(self.theme, self)
        if color is not None:
            self.new_game(color, mode=mode)

    def new_game(self, color, mode="ai"):
        self._game_id += 1

        self.mode = mode
        self.human_color = color
        self.board = chess.Board()
        self.history = []
        self.fens = [self.board.fen()]
        self.view_ply = None
        self.ai_busy = False
        self._last_coach = None
        self._human_move_ranks = []
        self._ai_move_count = 0
        self._ai_think_times = []
        self.coach_lbl.setText("")
        self.eval_bar.set_evaluation(normalized_evaluation(self.board), animate=False)
        self.game_over_card.hide()
        self.bv.human_color = color
        self.bv.set_flipped(color == chess.BLACK)
        self.bv.set_view_only(False)
        self.bv.set_position(self.board, animate=False)
        self.move_list.set_moves([])
        self.model_panel.set_idle()
        ai_mode = mode in ("ai", "ai_ai")
        self.diff_slider.setVisible(ai_mode)
        self.style_combo.setVisible(ai_mode)
        self.adaptive_btn.setVisible(ai_mode)
        self.diff_slider.set_mood(self.difficulty_value, self.ai_style)
        self._refresh_cards()
        self._set_controls()
        if mode == "two":
            self.set_status("White to move — pass & play")
        elif mode == "ai_ai":
            self.bv.set_view_only(True)
            self.set_status("ChessNet White is thinking…")
            self._trigger_ai()
        elif color == chess.BLACK:
            self._trigger_ai()
        else:
            self.set_status("Your move — you play White")

    def on_human_move(self, move):
        if self.ai_busy or self.board.is_game_over():
            return
        fen_before = self.board.fen()
        ply_before = len(self.history)
        self._apply_move(move, animate=True)
        self._ask_coach_async(fen_before, move, ply_before)
        self._refresh_evaluation()
        if self.board.is_game_over():
            self._finish_game()
        elif self.mode == "two":
            side = "White" if self.board.turn == chess.WHITE else "Black"
            status = f"{side} to move"
            if self.board.is_check():
                status += " — check!"
                self.set_status(status, error=True)
            else:
                self.set_status(status)
        else:
            self._trigger_ai()

    def _ask_coach_async(self, fen_before, move, ply_before):
        """Evaluate the played move in the background; never block the UI."""
        self._last_coach = None
        self.coach_lbl.setText("")
        game_id = self._game_id
        worker = AIWorker(fen_before, coach_move=move, game_id=game_id)
        self._ai_workers.add(worker)
        worker.finished.connect(lambda w=worker: self._ai_workers.discard(w))
        worker.coach_ok.connect(
            lambda result, gid, ply=ply_before: self._on_coach_ready(
                result, gid, ply))
        worker.failed.connect(
            lambda err, gid=game_id: self._on_coach_error(err, gid))
        worker.start()

    def _on_coach_ready(self, result, game_id, ply_before):
        if game_id != self._game_id or ply_before != len(self.history):
            return
        try:
            quality = move_quality(result)
            self._last_coach = (
                f"<b>{quality}</b> · " + chess_coach.coaching_message(result)
            )
            if result.get("rank") is not None:
                self._human_move_ranks.append(result["rank"])
                self._maybe_adapt_difficulty()
        except Exception:
            self._last_coach = None
        self.coach_lbl.setText(self._last_coach or "")

    def _on_coach_error(self, err, game_id):
        if game_id != self._game_id:
            return
        self._last_coach = None

    def _trigger_ai(self):
        self.ai_busy = True
        if self.mode != "ai_ai":
            self.bv.set_view_only(False)
        self.card_top.set_thinking(True)
        self.model_panel.set_thinking()
        side_name = "White" if self.board.turn == chess.WHITE else "Black"
        self.set_status(
            f"ChessNet {side_name} is thinking…"
            if self.mode == "ai_ai" else "ChessNet is thinking…"
        )
        self._set_controls()

        game_id = self._game_id
        self._think_started = time.perf_counter()
        self._thinking_legal_count = len(list(self.board.legal_moves))
        if self._thinking_timer is None:
            self._thinking_timer = QTimer(self)
            self._thinking_timer.timeout.connect(self._update_thinking_status)
        self._thinking_timer.start(120)
        worker = AIWorker(
            self.board.fen(),
            level=self.difficulty,
            style=self.ai_style
        )
        self._ai_workers.add(worker)
        worker.finished.connect(lambda w=worker: self._ai_workers.discard(w))
        worker.finished_ok.connect(
            lambda move, top: self._on_ai_move(move, top, game_id=game_id))
        worker.failed.connect(
            lambda err: self._on_ai_error(err, game_id=game_id))
        worker.start()

    def _on_ai_move(self, move, top, animate=True, game_id=None):
        if game_id is not None and game_id != self._game_id:
            return

        if self._thinking_timer is not None:
            self._thinking_timer.stop()
        elapsed = (
            time.perf_counter() - self._think_started
            if self._think_started is not None else 0.0
        )
        self._think_started = None
        self.card_top.set_thinking(False)
        prev = self.board.copy()
        san = prev.san(move)
        self._apply_move(move, animate=animate)
        self._ai_move_count += 1
        self._ai_think_times.append(elapsed)
        rows = [(prev.san(m), p, prev.san(m) == san) for m, p in top]
        self.model_panel.set_top(rows)
        self.ai_busy = False
        top_prob = top[0][1] if top else 0.0
        self._set_controls()
        if self.board.is_game_over():
            self._finish_game()
        elif self.mode == "ai_ai":
            next_side = "White" if self.board.turn == chess.WHITE else "Black"
            self.set_status(
                f"ChessNet {next_side} is thinking… · "
                f"last move {elapsed:.2f}s · confidence {top_prob * 100:.0f}%"
            )
            QTimer.singleShot(120, self._trigger_ai)
        elif self.board.is_check():
            self.set_status("Your move — check!", error=True)
        else:
            self.set_status(
                f"Your move · AI {elapsed:.2f}s · confidence {top_prob * 100:.0f}%"
            )

    def _on_ai_error(self, err, game_id=None):
        if game_id is not None and game_id != self._game_id:
            return

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
        if self.mode == "two":
            self.bv.human_color = self.board.turn
        self.bv.set_position(self.board, last_move=move, animate=animate)
        self._refresh_evaluation()
        self.move_list.set_moves([s for _, s in self.history],
                                 len(self.history))
        self._refresh_cards()
        if self.sounds is not None:
            if self.board.is_check():
                self.sounds.play("check")
            elif was_capture:
                self.sounds.play("capture")
            else:
                self.sounds.play("move")

    def undo(self):
        if self.ai_busy or not self.history:
            return
        if self.mode == "two":
            steps = 1
        else:
            steps = 1 if self.board.turn != self.human_color else 2
        if len(self.history) < steps:
            return
        for _ in range(steps):
            self.history.pop()
            self.fens.pop()
            self.board.pop()
        self.view_ply = None
        self._last_coach = None
        self.coach_lbl.setText("")
        self.game_over_card.hide()
        self.bv.set_view_only(False)
        self.bv.set_position(self.board, animate=False)
        self.move_list.set_moves([s for _, s in self.history],
                                 len(self.history))
        self._refresh_cards()
        self._set_controls()
        if self.mode == "two":
            side = "White" if self.board.turn == chess.WHITE else "Black"
            self.set_status(f"{side} to move")
        else:
            self.set_status("Your move")

    def ask_hint(self):
        """Show ChessNet's best move for the side to move."""
        if self.ai_busy or self.board.is_game_over():
            return
        if self._hint_worker is not None and self._hint_worker.isRunning():
            return
        game_id = self._game_id
        self.coach_lbl.setText("ChessNet is thinking…")
        self.set_status("Asking ChessNet for a hint…")
        self._hint_worker = HintWorker(self.board.fen(), game_id=game_id)
        self._hint_worker.hint_ok.connect(self._on_hint_ready)
        self._hint_worker.failed.connect(self._on_hint_error)
        self._hint_worker.start()

    def _on_hint_ready(self, sans, game_id):
        if game_id != self._game_id or not sans:
            return
        san, prob = sans[0]
        side = "White" if self.board.turn == chess.WHITE else "Black"
        self.model_panel.set_top([(san, prob, True)])
        self.coach_lbl.setText(
            f"ChessNet suggests <b>{san}</b> for {side} "
            f"({prob * 100:.0f}% policy confidence).")
        self.set_status("Your move" if self.mode == "ai" else
                        f"{side} to move")

    def _on_hint_error(self, err):
        self.set_status(f"Hint failed: {err}", error=True)
        self.coach_lbl.setText("")

    def save_pgn(self):
        """Export the current game as a PGN file."""
        if not self.history:
            self.set_status("Nothing to save yet — make a move first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save game as PGN", "chessnet_game.pgn", "PGN (*.pgn)")
        if not path:
            return

        game = chess.pgn.Game()
        game.headers["Event"] = "ChessNet casual game"
        game.headers["Site"] = "ChessNet"
        game.headers["Date"] = time.strftime("%Y.%m.%d")
        outcome = self.board.outcome(claim_draw=True)
        result = outcome.result() if outcome is not None else "*"
        game.headers["Result"] = result
        if self.mode == "two":
            game.headers["White"] = "Player 1"
            game.headers["Black"] = "Player 2"
        else:
            game.headers["White"] = ("You" if self.human_color == chess.WHITE
                                     else "ChessNet")
            game.headers["Black"] = ("ChessNet"
                                     if self.human_color == chess.WHITE
                                     else "You")
        game.add_line([m for m, _ in self.history])
        try:
            with open(path, "w", encoding="utf-8") as f:
                print(game, file=f, end="\n\n")
        except OSError as e:
            self.set_status(f"Could not save PGN: {e}", error=True)
            return
        self.set_status(f"Game saved to {Path(path).name}")

    def set_view_ply(self, ply):
        if ply is None or ply >= len(self.history):
            self.go_live()
            return
        self.view_ply = max(0, ply)
        if self.view_ply == 0:
            self.bv.set_position(chess.Board(self.fens[0]), animate=False)
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
            if self.mode == "two":
                side = "White" if self.board.turn == chess.WHITE else "Black"
                self.set_status(f"{side} to move")
            else:
                if self.mode == "ai_ai":
                    side = "White" if self.board.turn == chess.WHITE else "Black"
                    self.set_status(
                        f"ChessNet {side} is thinking…" if self.ai_busy
                        else f"ChessNet {side} to move"
                    )
                else:
                    self.set_status("ChessNet is thinking…" if self.ai_busy
                                    else "Your move")

    def _choose_promotion(self, color, to_square):
        pos = self.bv.map_square_to_global(to_square)
        size = self.bv.board_px() / 8
        return PromotionPicker.pick(self.theme, color, pos, size, self)

    def _refresh_cards(self):
        over = self.board.is_game_over()
        if self.mode == "ai_ai":
            self.card_bottom.set_identity("ChessNet White", "White · AI", "K")
            self.card_top.set_identity("ChessNet Black", "Black · AI", "k")
            white_caps, white_val = captured_by(self.board, chess.WHITE)
            black_caps, black_val = captured_by(self.board, chess.BLACK)
            self.card_bottom.set_captured(white_caps, white_val - black_val)
            self.card_top.set_captured(black_caps, black_val - white_val)
            self.card_bottom.set_turn(
                self.board.turn == chess.WHITE and not over)
            self.card_top.set_turn(
                self.board.turn == chess.BLACK and not over)
            self.card_top.set_thinking(
                self.ai_busy and self.board.turn == chess.BLACK)
            return

        if self.mode == "two":
            self.card_bottom.set_identity("White", "human · pass & play", "K")
            self.card_top.set_identity("Black", "human · pass & play", "k")
            white_caps, white_val = captured_by(self.board, chess.WHITE)
            black_caps, black_val = captured_by(self.board, chess.BLACK)
            self.card_bottom.set_captured(white_caps, white_val - black_val)
            self.card_top.set_captured(black_caps, black_val - white_val)
            self.card_bottom.set_turn(
                self.board.turn == chess.WHITE and not over)
            self.card_top.set_turn(
                self.board.turn == chess.BLACK and not over)
            return

        my_king = "K" if self.human_color == chess.WHITE else "k"
        ai_knight = "N" if self.human_color == chess.BLACK else "n"
        my_side = "White" if self.human_color == chess.WHITE else "Black"
        ai_side = "Black" if my_side == "White" else "White"
        tier = chess_coach.LABELS[self.difficulty]
        model_sub = (f"{ai_side} · ChessNet CNN · {tier} · "
                     + ("ready" if self.model_ready else "loading weights…"))
        self.card_bottom.set_identity("You", f"{my_side} · human", my_king)
        self.card_top.set_identity("ChessNet", model_sub, ai_knight)
        my_caps, my_val = captured_by(self.board, self.human_color)
        ai_caps, ai_val = captured_by(self.board, not self.human_color)
        self.card_bottom.set_captured(my_caps, my_val - ai_val)
        self.card_top.set_captured(ai_caps, ai_val - my_val)
        self.card_bottom.set_turn(
            self.board.turn == self.human_color and not over)
        self.card_top.set_turn(
            self.board.turn != self.human_color and not over)

    def _finish_game(self):
        outcome = self.board.outcome(claim_draw=True)
        if outcome is None:
            return
        if self.mode == "two":
            winner_name = ("White" if outcome.winner == chess.WHITE
                           else "Black") if outcome.winner is not None else None
        else:
            human_won = outcome.winner == self.human_color
            winner_name = ("You" if human_won else "ChessNet") \
                if outcome.winner is not None else None
        if winner_name is not None:
            if self.mode == "two":
                title = f"Checkmate — {winner_name} wins"
            elif winner_name == "You":
                title = "Checkmate — you win!"
            else:
                title = f"Checkmate — {winner_name} wins"
            sub = "Rematch?" if winner_name != "You" else "The CNN is mated."
        else:
            title = "Draw"
            reason = {
                chess.Termination.STALEMATE: "Stalemate",
                chess.Termination.INSUFFICIENT_MATERIAL: "Insufficient material",
                chess.Termination.SEVENTYFIVE_MOVES: "75-move rule",
                chess.Termination.FIVEFOLD_REPETITION: "Fivefold repetition",
            }.get(outcome.termination, outcome.termination.name.capitalize())
            sub = f"{reason}."
        if self.mode in ("ai", "ai_ai"):
            tier = chess_coach.LABELS[self.difficulty]
            style = chess_coach.STYLES.get(self.ai_style, "Balanced")
            value = max(0, min(100, int(self.difficulty_value)))
            if value <= 20:
                mood = "Calm"
            elif value <= 40:
                mood = "Relaxed"
            elif value <= 60:
                mood = "Focused"
            elif value <= 80:
                mood = "Sharp"
            else:
                mood = "Intense"
            avg_think = (sum(self._ai_think_times) / len(self._ai_think_times)
                         if self._ai_think_times else 0.0)
            summary = (f"AI session · {value}% {tier} · {style} · {mood}<br>"
                       f"AI moves: {self._ai_move_count} · "
                       f"Avg thinking: {avg_think:.2f}s")
            sub = f"{sub}<br><br>{summary}"
        self.set_status(f"{title} ({outcome.result()})")
        self.game_over_card.show_result(title, sub)
        self.bv.set_view_only(True)
        self._refresh_cards()
        self._set_controls()
        if self.sounds is not None:
            self.sounds.play("end")

    def _set_controls(self):
        self.undo_btn.setEnabled(
            not self.ai_busy and bool(self.history) and self.mode != "ai_ai"
        )

    def set_status(self, text, error=False):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(
            f"color: {self.theme.danger if error else self.theme.text};")

    def _toggle_sound(self, on):
        engine = getattr(self, "sounds", None)
        if engine is not None:
            engine.enabled = on
        settings_mod.save(sound=on)

    def _toggle_animations(self, on):
        self.bv.animations_enabled = on
        settings_mod.save(animations=on)

    def _toggle_theme(self, want_light):
        self.theme_btn.setText("☾" if want_light else "☀")
        self.theme = theme_mod.THEMES["light" if want_light else "dark"]
        self._apply_theme()
        settings_mod.save(theme="light" if want_light else "dark")

    def _on_difficulty_changed(self, level, value):
        self.difficulty = level
        self.difficulty_value = value
        settings_mod.save(difficulty=self.difficulty, difficulty_value=self.difficulty_value)
        self._refresh_cards()
        self.diff_slider.set_mood(self.difficulty_value, self.ai_style)
        self.set_status(
            f"AI difficulty · {self.difficulty_value}% · "
            f"{chess_coach.LABELS[self.difficulty]}"
        )

    def _on_style_changed(self, index):
        styles = list(chess_coach.STYLES)
        if not 0 <= index < len(styles):
            return
        self.ai_style = styles[index]
        settings_mod.save(ai_style=self.ai_style)
        self.diff_slider.set_mood(self.difficulty_value, self.ai_style)
        self.set_status(
            f"AI style · {chess_coach.STYLES[self.ai_style]} · "
            f"{self.difficulty_value}%"
        )

    def _toggle_adaptive(self, enabled):
        self.adaptive = enabled
        settings_mod.save(adaptive=enabled)
        self.set_status("Adaptive AI enabled" if enabled else "Adaptive AI disabled")

    def _maybe_adapt_difficulty(self):
        if not self.adaptive or self.mode != "ai":
            return
        if not self._human_move_ranks or len(self._human_move_ranks) % 4:
            return
        avg_rank = sum(self._human_move_ranks[-4:]) / 4
        current = chess_coach.ORDER.index(self.difficulty)
        if avg_rank <= 1.5 and current < len(chess_coach.ORDER) - 1:
            current += 1
        elif avg_rank >= 8 and current > 0:
            current -= 1
        else:
            return
        self.diff_slider.set_level(chess_coach.ORDER[current])

    def _refresh_evaluation(self, animate=True):
        self.eval_bar.set_evaluation(normalized_evaluation(self.board), animate=animate)

    def _update_thinking_status(self):
        if not self.ai_busy or self._think_started is None:
            return
        elapsed = time.perf_counter() - self._think_started
        self.set_status(
            f"ChessNet is thinking · {elapsed:.1f}s · "
            f"{getattr(self, '_thinking_legal_count', 0)} legal moves"
        )

    def analyze_game(self):
        if not self.history:
            self.set_status("Make a few moves before analyzing the game.")
            return
        from ai_features import summarize_game
        board_history = [chess.Board(self.fens[i]) for i in range(len(self.history))]
        moves = [move for move, _ in self.history]
        summary = summarize_game(
            board_history, moves, self.human_color,
            lambda board, move: chess_coach.evaluate_human_move(board, move, k=5),
        )
        AnalysisDialog(self.theme, summary, self).exec()
        try:
            text = summary.get("accuracy", "—").rstrip("%")
            accuracy = float(text) if text != "—" else None
        except ValueError:
            accuracy = None
        if self.board.is_game_over():
            outcome = self.board.outcome(claim_draw=True)
            if outcome is not None:
                settings_mod.record_game(outcome.result(), accuracy)

    def closeEvent(self, e):
        for w in list(self._ai_workers):
            if w.isRunning():
                w.wait(2000)
        loader = getattr(self, "loader", None)
        if loader is not None and loader.isRunning():
            loader.wait(2000)
        hint = getattr(self, "_hint_worker", None)
        if hint is not None and hint.isRunning():
            hint.wait(2000)
        if getattr(self, "sounds", None) is not None:
            self.sounds.enabled = False
        if self.has_menu:
            self.back_requested.emit()
        super().closeEvent(e)


def run_screenshot(path, plies, theme_name):
    from chess_ai import get_move_and_top
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow(theme_name, interactive=False)
    try:
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
    except Exception as e:
        print(f"scripted plies skipped (model problem): {e}")
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
    parser.add_argument("--play", action="store_true",
                        help="skip the main menu and go straight to the board")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    theme_name = "light" if args.light else settings_mod.load()["theme"]

    if args.screenshot:
        run_screenshot(Path(args.screenshot), args.plies, theme_name)
        return

    if args.play:
        win = MainWindow(theme_name)
    else:
        from main_menu import MainMenu
        win = MainMenu(theme_name)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
