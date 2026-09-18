"""Background workers so the UI never freezes during model inference."""

from PySide6.QtCore import QThread, Signal

import chess

from chess_ai import get_move_and_top, get_model, get_top_moves


class AIWorker(QThread):
    """Runs one ChessNet forward pass off the UI thread.

    Two modes:
    - default: pick the AI's move (coach level or plain policy).
    - coach_move: evaluate a human move against the policy for coaching.
    """

    finished_ok = Signal(object, list)
    coach_ok = Signal(object, int)
    failed = Signal(str)

    def __init__(self, fen, sample=False, level=None, style="balanced", parent=None,
                 coach_move=None, game_id=None):
        super().__init__(parent)
        self._fen = fen
        self._sample = sample
        self._level = level
        self._style = style
        self._coach_move = coach_move
        self._game_id = game_id

    def run(self):
        try:
            board = chess.Board(self._fen)

            if self._coach_move is not None:
                from chess_coach import evaluate_human_move
                result = evaluate_human_move(board, self._coach_move, k=3)
                self.coach_ok.emit(result, self._game_id)
                return

            if self._level:
                from chess_coach import get_coach_move_and_top
                move, top = get_coach_move_and_top(
                    board, self._level, style=self._style, k=5
                )
            else:
                move, top = get_move_and_top(board, k=5, sample=self._sample)
            self.finished_ok.emit(move, top)
        except Exception as e:
            self.failed.emit(str(e))


class HintWorker(QThread):
    """Best model move for the current position, for the Hint button."""

    hint_ok = Signal(list, int)   # [(san, prob)], game_id
    failed = Signal(str)

    def __init__(self, fen, game_id=None, parent=None):
        super().__init__(parent)
        self._fen = fen
        self._game_id = game_id

    def run(self):
        try:
            board = chess.Board(self._fen)
            _, top = get_move_and_top(board, k=1, sample=False)
            sans = [(board.san(m), p) for m, p in top]
            self.hint_ok.emit(sans, self._game_id)
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
