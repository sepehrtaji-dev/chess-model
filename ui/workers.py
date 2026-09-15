"""Background workers so the UI never freezes during model inference."""

from PySide6.QtCore import QThread, Signal

import chess

from chess_ai import get_move_and_top, get_model


class AIWorker(QThread):
    finished_ok = Signal(object, list)
    failed = Signal(str)

    def __init__(self, fen, sample=False, level=None, parent=None):
        super().__init__(parent)
        self._fen = fen
        self._sample = sample
        self._level = level

    def run(self):
        try:
            board = chess.Board(self._fen)
            if self._level:
                from chess_coach import get_coach_move_and_top
                move, top = get_coach_move_and_top(board, self._level, k=5)
            else:
                move, top = get_move_and_top(board, k=5, sample=self._sample)
            self.finished_ok.emit(move, top)
        except Exception as e:
            self.failed.emit(str(e))


class ModelLoader(QThread):
    loaded = Signal()
    failed = Signal(str)

    def run(self):
        try:
            get_model()
            self.loaded.emit()
        except Exception as e:
            self.failed.emit(str(e))