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
