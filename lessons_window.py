"""Interactive lessons window with live ChessNet coaching."""

import chess

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import chess_ai
import chess_coach
from chess_lessons import LESSONS
from ui import theme as theme_mod
from ui.board_view import BoardView
from ui.panels import PromotionPicker
from ui.workers import ModelLoader


class _BoardHost(QFrame):
    MARGIN = 24

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.setMinimumSize(440, 440)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)

        self.board_view = BoardView(theme, self)
        lay.addWidget(self.board_view, 0, Qt.AlignCenter)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refit()

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self._refit)
        QTimer.singleShot(120, self._refit)
        QTimer.singleShot(350, self._refit)

    def _refit(self):
        w = self.width() - self.MARGIN
        h = self.height() - self.MARGIN
        side = min(w, h)

        if side < 200:
            return

        bv = self.board_view

        bv.setMinimumSize(0, 0)
        bv.setMaximumSize(16777215, 16777215)
        bv.setFixedSize(side, side)
        bv.resize_to_fit(side, side)


class _ModelWorker(QThread):
    done = Signal(object, int)

    def __init__(self, fen, kind, lesson_id, uci=None, parent=None):
        super().__init__(parent)
        self._fen = fen
        self._kind = kind
        self._uci = uci
        self._lesson_id = lesson_id

    def run(self):
        try:
            board = chess.Board(self._fen)

            if self._kind == "evaluate":
                move = chess.Move.from_uci(self._uci)
                result = chess_coach.evaluate_human_move(board, move, k=3)
            else:
                top = chess_ai.get_top_moves(board, k=3)
                result = {
                    "top": [(board.san(m), p) for m, p in top],
                    "best_san": board.san(top[0][0]),
                    "best_move": top[0][0],
                }

            self.done.emit(result, self._lesson_id)

        except Exception as e:
            self.done.emit({"error": str(e)}, self._lesson_id)


class LessonsWindow(QMainWindow):
    back_requested = Signal()

    def __init__(self, theme_name="dark", parent=None):
        super().__init__(parent)

        self.theme = theme_mod.THEMES[theme_name]

        self.lesson_idx = 0
        self.lesson = LESSONS[0]
        self.board = chess.Board(self.lesson.fen)

        self.attempts = 0
        self.solved = set()

        self._locked = False
        self._model_ready = False
        self._lesson_id = 0
        self._workers = set()
        self._seen_answer = False

        self._build_ui()
        self._apply_theme()
        self._load_model_async()

        QTimer.singleShot(0, lambda: self._load_lesson(0))

    def _build_ui(self):
        self.setWindowTitle("ChessNet — Lessons")
        self.setMinimumSize(1120, 740)
        self.resize(1320, 860)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(16)
        self.setCentralWidget(central)

        left = QFrame()
        left.setObjectName("panel")
        left.setFixedWidth(240)

        lv = QVBoxLayout(left)
        lv.setContentsMargins(12, 12, 12, 12)
        lv.setSpacing(10)

        self.back_btn = QPushButton("← Main menu")
        self.back_btn.clicked.connect(self._back)
        lv.addWidget(self.back_btn)

        head = QLabel("Lessons")
        head.setObjectName("title")
        hf = head.font()
        hf.setPointSizeF(15)
        hf.setBold(True)
        head.setFont(hf)
        lv.addWidget(head)

        self.progress_lbl = QLabel("")
        self.progress_lbl.setObjectName("caption")
        lv.addWidget(self.progress_lbl)

        self.nav_scroll = QScrollArea()
        self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setFrameShape(QFrame.NoFrame)

        self.nav_body = QWidget()
        self.nav_box = QVBoxLayout(self.nav_body)
        self.nav_box.setContentsMargins(0, 0, 0, 0)
        self.nav_box.setSpacing(4)
        self.nav_box.addStretch(1)

        self.nav_scroll.setWidget(self.nav_body)
        lv.addWidget(self.nav_scroll, 1)

        root.addWidget(left)

        self.board_host = _BoardHost(self.theme)
        root.addWidget(self.board_host, 1)

        self.bv = self.board_host.board_view
        self.bv.human_move.connect(self._on_move)
        self.bv.choose_promotion = self._choose_promotion

        # Lessons may use positions python-chess marks as game over,
        # for example insufficient material, but still require moves.
        self.bv.allow_game_over_positions = True

        right = QFrame()
        right.setObjectName("panel")
        right.setFixedWidth(380)

        rv = QVBoxLayout(right)
        rv.setContentsMargins(18, 16, 18, 16)
        rv.setSpacing(10)

        self.title_lbl = QLabel()
        self.title_lbl.setObjectName("title")
        tf = self.title_lbl.font()
        tf.setPointSizeF(17)
        tf.setBold(True)
        self.title_lbl.setFont(tf)
        self.title_lbl.setWordWrap(True)
        rv.addWidget(self.title_lbl)

        self.sub_lbl = QLabel()
        self.sub_lbl.setObjectName("caption")
        self.sub_lbl.setWordWrap(True)
        rv.addWidget(self.sub_lbl)

        rv.addSpacing(4)

        self.intro_lbl = QLabel()
        self.intro_lbl.setWordWrap(True)
        rv.addWidget(self.intro_lbl)

        rv.addSpacing(6)

        task_box = QFrame()
        task_box.setObjectName("panel")

        tb = QVBoxLayout(task_box)
        tb.setContentsMargins(12, 10, 12, 10)
        tb.setSpacing(4)

        task_head = QLabel("Your turn")
        task_head.setObjectName("caption")
        tb.addWidget(task_head)

        self.task_lbl = QLabel()
        self.task_lbl.setWordWrap(True)
        tb.addWidget(self.task_lbl)

        rv.addWidget(task_box)
        rv.addStretch(1)

        self.feedback_lbl = QLabel()
        self.feedback_lbl.setWordWrap(True)
        self.feedback_lbl.setObjectName("caption")
        self.feedback_lbl.setTextFormat(Qt.RichText)
        rv.addWidget(self.feedback_lbl)

        row_a = QHBoxLayout()
        row_a.setSpacing(8)

        self.ai_btn = QPushButton("Ask AI")
        self.ai_btn.setEnabled(False)

        self.hint_btn = QPushButton("Hint")

        row_a.addWidget(self.ai_btn)
        row_a.addWidget(self.hint_btn)
        rv.addLayout(row_a)

        row_b = QHBoxLayout()
        row_b.setSpacing(8)

        self.show_btn = QPushButton("Show me")
        self.reset_btn = QPushButton("Reset")

        row_b.addWidget(self.show_btn)
        row_b.addWidget(self.reset_btn)
        rv.addLayout(row_b)

        self.next_btn = QPushButton("Next lesson →")
        self.next_btn.setObjectName("primary")
        self.next_btn.setEnabled(False)
        rv.addWidget(self.next_btn)

        self.model_lbl = QLabel("loading model…")
        self.model_lbl.setObjectName("caption")
        rv.addWidget(self.model_lbl)

        root.addWidget(right)

        self.ai_btn.clicked.connect(self._ask_ai)
        self.hint_btn.clicked.connect(self._show_hint)
        self.show_btn.clicked.connect(self._show_answer)
        self.reset_btn.clicked.connect(self._reset)
        self.next_btn.clicked.connect(self._next)
        self.back_btn.clicked.connect(self._back)

        QShortcut(QKeySequence("Escape"), self, self._back)
        QShortcut(QKeySequence("Ctrl+R"), self, self._reset)
        QShortcut(QKeySequence("Right"), self, self._next)
        QShortcut(QKeySequence("Ctrl+H"), self, self._ask_ai)
        QShortcut(QKeySequence("Ctrl+I"), self, self._show_hint)

    def _apply_theme(self):
        self.setStyleSheet(theme_mod.qss(self.theme))
        self.bv.set_theme(self.theme)

    def _load_model_async(self):
        self.loader = ModelLoader()
        self.loader.loaded.connect(self._on_model_ready)
        self.loader.failed.connect(self._on_model_failed)
        self.loader.start()

    def _on_model_ready(self):
        self._model_ready = True
        self.model_lbl.setText("model ready")
        self.ai_btn.setEnabled(True)

    def _on_model_failed(self, err):
        self._model_ready = False
        self.model_lbl.setText(f"model failed: {err}")
        self.ai_btn.setEnabled(False)

    def _set_board_interactive(self, enabled):
        self._locked = not enabled
        self.bv.set_view_only(not enabled)

    def _after_wrong_if_current(self, lesson_id):
        if lesson_id == self._lesson_id:
            self._after_wrong()

    def _after_demo_if_current(self, lesson_id):
        if lesson_id == self._lesson_id:
            self._after_demo()

    def _load_lesson(self, idx):
        idx = max(0, min(idx, len(LESSONS) - 1))

        self._lesson_id += 1
        self.lesson_idx = idx
        self.lesson = LESSONS[idx]

        self.attempts = 0
        self._seen_answer = False

        self.board = chess.Board(self.lesson.fen)

        print(
            "[lesson] load", idx,
            "game_over=", self.board.is_game_over(),
            "insufficient=", self.board.is_insufficient_material(),
            "legal=", len(list(self.board.legal_moves)),
        )

        self.bv.human_color = self.board.turn
        self.bv.set_flipped(self.board.turn == chess.BLACK)
        self._set_board_interactive(True)
        self.bv.set_position(self.board, animate=False)

        self.title_lbl.setText(self.lesson.title)
        self.sub_lbl.setText(
            f"Lesson {idx + 1} of {len(LESSONS)} · {self.lesson.subtitle}"
        )
        self.intro_lbl.setText(self.lesson.intro)
        self.task_lbl.setText(self.lesson.task)
        self.feedback_lbl.setText("")

        self.next_btn.setEnabled(False)
        self.next_btn.setText(
            "Next lesson →" if idx < len(LESSONS) - 1 else "Back to menu"
        )

        self._refresh_nav()

        QTimer.singleShot(0, self.board_host._refit)
        QTimer.singleShot(100, self.board_host._refit)

    def _refresh_nav(self):
        while self.nav_box.count() > 1:
            item = self.nav_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        for i, lesson in enumerate(LESSONS):
            mark = "✓" if i in self.solved else "·"

            btn = QPushButton(f"{mark}  {i + 1}. {lesson.title}")
            btn.setObjectName("moveBtn")
            btn.setCheckable(True)
            btn.setChecked(i == self.lesson_idx)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("text-align: left; padding-left: 8px;")
            btn.clicked.connect(lambda _=False, k=i: self._load_lesson(k))

            self.nav_box.insertWidget(self.nav_box.count() - 1, btn)

        self.progress_lbl.setText(f"{len(self.solved)} of {len(LESSONS)} solved")

    def _on_move(self, move):
        print("[lesson] human_move:", move, "locked:", self._locked)

        # Do NOT check self.board.is_game_over() here.
        # Some lesson positions can be marked game over by python-chess
        # while still having legal moves for teaching purposes.
        if self._locked:
            return

        if move not in self.board.legal_moves:
            print("[lesson] rejected: not legal for current board")
            print("legal moves:", [self.board.san(m) for m in self.board.legal_moves])
            return

        before = self.board.copy()
        after = before.copy()
        after.push(move)

        ok = self.lesson.check(move, before, after)

        self.board = after
        self.bv.set_position(self.board, last_move=move, animate=True)

        self.attempts += 1

        if ok:
            self._solved()
        else:
            self._set_board_interactive(False)
            self._coach_wrong_move(before, move)

    def _coach_wrong_move(self, before, move):
        if not self._model_ready:
            self.feedback_lbl.setText(
                f"<span style='color:{self.theme.danger}'>Not quite.</span> "
                f"Hint: {self.lesson.hint}"
            )

            QTimer.singleShot(
                2200,
                lambda lid=self._lesson_id: self._after_wrong_if_current(lid),
            )
            return

        self.feedback_lbl.setText("Let me look at that with you…")

        worker = _ModelWorker(
            before.fen(),
            "evaluate",
            self._lesson_id,
            uci=move.uci(),
        )

        self._workers.add(worker)
        worker.done.connect(self._on_eval_ready)
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        worker.start()

    def _on_eval_ready(self, result, lesson_id):
        if lesson_id != self._lesson_id:
            return

        if "error" in result:
            self.feedback_lbl.setText(f"Hint: {self.lesson.hint}")

            QTimer.singleShot(
                1800,
                lambda lid=self._lesson_id: self._after_wrong_if_current(lid),
            )
            return

        played_san = result["played_move_san"]
        best_san = result["best_move_san"]

        parts = [f"<b>{played_san}</b> isn't what this lesson is about."]

        if result["dropped_material"]:
            parts.append("It leaves a piece undefended.")
        elif result["in_top_k"]:
            parts.append("It's playable, but not the teaching move.")
        else:
            parts.append("The model rates it well below its top pick.")

        if best_san == self.lesson.answer_san:
            parts.append(f"ChessNet agrees: <b>{best_san}</b> is the move.")
        else:
            parts.append(f"ChessNet prefers <b>{best_san}</b> here.")

        if self.attempts >= 2:
            parts.append(f"Hint: {self.lesson.hint}")

        self.feedback_lbl.setText(
            f"<span style='color:{self.theme.danger}'>"
            + " ".join(parts)
            + "</span>"
        )

        QTimer.singleShot(
            3600,
            lambda lid=self._lesson_id: self._after_wrong_if_current(lid),
        )

    def _after_wrong(self):
        self.board = chess.Board(self.lesson.fen)

        self.bv.human_color = self.board.turn
        self.bv.set_flipped(self.board.turn == chess.BLACK)
        self._set_board_interactive(True)
        self.bv.set_position(self.board, animate=False)

        if self.attempts >= 3:
            self.feedback_lbl.setText(
                "Try a different piece — or press Show me to watch the move."
            )
        else:
            self.feedback_lbl.setText("Try again.")

        self._check_next_available()

    def _solved(self):
        self.solved.add(self.lesson_idx)

        self.feedback_lbl.setText(
            f"<span style='color:{self.theme.accent}'>✓ "
            f"{self.lesson.success}</span>"
        )

        self._set_board_interactive(False)
        self.next_btn.setEnabled(True)
        self._refresh_nav()

    def _reset(self):
        self.attempts = 0
        self._lesson_id += 1

        self.board = chess.Board(self.lesson.fen)

        self.bv.human_color = self.board.turn
        self.bv.set_flipped(self.board.turn == chess.BLACK)
        self._set_board_interactive(True)
        self.bv.set_position(self.board, animate=False)

        self.feedback_lbl.setText("")

        self.next_btn.setEnabled(False)
        self._check_next_available()

    def _show_hint(self):
        if self._locked:
            return

        try:
            move = chess.Move.from_uci(self.lesson.answer_uci)
        except ValueError:
            return

        self.feedback_lbl.setText(f"Hint: {self.lesson.hint}")
        self.bv.set_position(self.board, last_move=move, animate=False)

    def _show_answer(self):
        if self._locked:
            return

        try:
            move = chess.Move.from_uci(self.lesson.answer_uci)
        except ValueError:
            return

        if move not in self.board.legal_moves:
            self._reset()
            return

        self._lesson_id += 1
        self._seen_answer = True

        self._set_board_interactive(False)

        self.board.push(move)
        self.bv.set_position(self.board, last_move=move, animate=True)

        self.feedback_lbl.setText(
            f"Watch: <b>{self.lesson.answer_san}</b>. {self.lesson.success}"
        )

        QTimer.singleShot(
            2600,
            lambda lid=self._lesson_id: self._after_demo_if_current(lid),
        )

    def _after_demo(self):
        self._reset()
        self.feedback_lbl.setText("Now you try it.")
        self._check_next_available()

    def _ask_ai(self):
        if self._locked or not self._model_ready:
            return

        self._set_board_interactive(False)
        self.feedback_lbl.setText("Asking ChessNet…")

        worker = _ModelWorker(self.board.fen(), "best", self._lesson_id)

        self._workers.add(worker)
        worker.done.connect(self._on_hint_ready)
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        worker.start()

    def _on_hint_ready(self, result, lesson_id):
        if lesson_id != self._lesson_id:
            return

        self._set_board_interactive(True)

        if "error" in result or not result.get("top"):
            self.feedback_lbl.setText(f"Hint: {self.lesson.hint}")
            return

        top = result["top"]
        best_san = top[0][0]
        others = " · ".join(f"{san} ({p * 100:.0f}%)" for san, p in top)

        self.feedback_lbl.setText(
            f"ChessNet would play <b>{best_san}</b> here. Top picks: {others}."
        )

    def _check_next_available(self):
        if (
            self.lesson_idx in self.solved
            or self._seen_answer
            or self.attempts >= 3
        ):
            self.next_btn.setEnabled(True)

    def _next(self):
        if self.lesson_idx < len(LESSONS) - 1:
            self._load_lesson(self.lesson_idx + 1)
        else:
            self._back()

    def closeEvent(self, e):
        for w in list(self._workers):
            if w.isRunning():
                w.wait(2000)

        if getattr(self, "loader", None) is not None and self.loader.isRunning():
            self.loader.wait(2000)

        super().closeEvent(e)

    def _back(self):
        self.back_requested.emit()
        self.close()

    def _choose_promotion(self, color, to_square):
        pos = self.bv.map_square_to_global(to_square)
        size = self.bv.board_px() / 8
        return PromotionPicker.pick(self.theme, color, pos, size, self)