"""Background workers so the UI never freezes during model inference."""

from PySide6.QtCore import QThread, Signal

import chess

from chess_ai import get_move_and_top, get_model


class AIWorker(QThread):
    """Runs one model inference for the given FEN."""

    finished_ok = Signal(object, list)  # chess.Move, [(chess.Move, float)]
    failed = Signal(str)

    def __init__(self, fen, sample=False, parent=None):
        super().__init__(parent)
        self._fen = fen
        self._sample = sample

    def run(self):
        try:
            board = chess.Board(self._fen)
            move, top = get_move_and_top(board, k=5, sample=self._sample)
            self.finished_ok.emit(move, top)
        except Exception as e:
            self.failed.emit(str(e))


class ModelLoader(QThread):
    """Warm-loads the 86MB checkpoint at startup so the first reply is fast."""

    loaded = Signal()
    failed = Signal(str)

    def run(self):
        try:
            get_model()
            self.loaded.emit()
        except Exception as e:
            self.failed.emit(str(e))
