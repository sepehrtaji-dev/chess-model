"""The chess board: SVG pieces, drag & drop, legal-move hints, animations."""

import chess
from PySide6.QtCore import (QEasingCurve, QPointF, QPropertyAnimation, QRectF,
                            QSizeF, Qt, Signal)
from PySide6.QtGui import (QBrush, QColor, QFont, QPainter, QPen, QPixmap,
                           QRadialGradient)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsObject,
                               QGraphicsRectItem, QGraphicsScene,
                               QGraphicsView)

from .pieces import SVG

MOVE_MS = 260
SNAP_MS = 130


class PieceItem(QGraphicsObject):
    """A chess piece. QGraphicsObject so pos/opacity/scale are animatable."""

    def __init__(self, symbol):
        super().__init__()
        self._symbol = symbol
        self._pixmap = QPixmap(1, 1)
        self._size = 1.0

    def symbol(self):
        return self._symbol

    def set_pixmap(self, pixmap, size):
        self.prepareGeometryChange()
        self._pixmap = pixmap
        self._size = size
        self.update()

    def boundingRect(self):
        return QRectF(0.0, 0.0, self._size, self._size)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(QPointF(0.0, 0.0), self._pixmap)


class BoardView(QGraphicsView):
    """Renders a chess.Board. The human plays by mouse; the app calls
    set_position() for every move, including the AI's."""

    human_move = Signal(object)      # chess.Move
    history_clicked = Signal()       # board clicked while reviewing history

    Z_SQUARE = 0
    Z_LASTMOVE = 1
    Z_HINT = 2
    Z_PIECE = 10
    Z_DRAG = 100

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.board = chess.Board()
        self.human_color = chess.WHITE
        self.flipped = False
        self.view_only = False
        self.animations_enabled = True
        self.choose_promotion = None  # fn(color) -> piece_type or None

        self._S = 76.0
        self._selected = None
        self._legal_for_selected = []
        self._last_move = None
        self._pieces = {}       # square -> PieceItem
        self._animating = []    # running QPropertyAnimations
        self._fading_ghosts = []  # capture fade-out items not tracked in _pieces
        self._press_piece = None
        self._press_start = None
        self._dragging = False
        self._renderers = {s: QSvgRenderer(SVG[s].encode("utf-8"))
                           for s in SVG}

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)

        # overlay items
        self._sel_rect = QGraphicsRectItem()
        self._last_from = QGraphicsRectItem()
        self._last_to = QGraphicsRectItem()
        self._check_item = QGraphicsEllipseItem()
        for it in (self._sel_rect, self._last_from, self._last_to,
                   self._check_item):
            it.setPen(QPen(Qt.NoPen))
            it.setZValue(self.Z_LASTMOVE)
            it.hide()
            self._scene.addItem(it)
        self._hints = []
        self.resize_to_fit(608, 608)

    # ---------- geometry -------------------------------------------------

    def square_to_pos(self, square):
        f, r = chess.square_file(square), chess.square_rank(square)
        if self.flipped:
            f, r = 7 - f, 7 - r
        return QPointF(f * self._S, (7 - r) * self._S)

    def pos_to_square(self, pos):
        f = int(pos.x() // self._S)
        r = 7 - int(pos.y() // self._S)
        if self.flipped:
            f, r = 7 - f, 7 - r
        if not (0 <= f <= 7 and 0 <= r <= 7):
            return None
        return chess.square(f, r)

    def board_px(self):
        return self._S * 8

    def resize_to_fit(self, w, h):
        s = max(32.0, min(w, h) / 8.0)
        if abs(s - self._S) < 0.5:
            return
        self._S = s
        self.setFixedSize(int(self.board_px()) + 2, int(self.board_px()) + 2)
        self.setSceneRect(0.0, 0.0, self.board_px(), self.board_px())
        self._kill_animations()
        self.deselect()
        self.rebuild()

    # ---------- rendering ------------------------------------------------

    def _piece_pixmap(self, symbol):
        dpr = self.devicePixelRatioF()
        px = int(self._S * dpr)
        pm = QPixmap(px, px)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        self._renderers[symbol].render(p, QRectF(0, 0, px, px))
        p.end()
        pm.setDevicePixelRatio(dpr)
        return pm

    def drawBackground(self, painter, rect):
        p = self.theme
        painter.setPen(Qt.NoPen)
        light, dark = QColor(p.board_light), QColor(p.board_dark)
        for r in range(8):
            for f in range(8):
                painter.setBrush(light if (r + f) % 2 == 0 else dark)
                painter.drawRect(QRectF(f * self._S, r * self._S,
                                        self._S, self._S))
        # coordinates inside edge squares, tinted with the opposite color
        font = QFont()
        font.setPointSizeF(max(7.0, self._S * 0.20))
        font.setBold(True)
        painter.setFont(font)
        for i in range(8):
            f = i if not self.flipped else 7 - i
            r = 7 - i if not self.flipped else i
            letter_bg = light if (7 + i) % 2 == 0 else dark
            painter.setPen(dark if letter_bg == light else light)
            painter.drawText(
                QRectF(i * self._S + self._S * 0.58,
                       7 * self._S + self._S * 0.52,
                       self._S * 0.40, self._S * 0.46),
                Qt.AlignCenter, "abcdefgh"[f])
            num_bg = light if (i + 0) % 2 == 0 else dark
            painter.setPen(dark if num_bg == light else light)
            painter.drawText(
                QRectF(self._S * 0.03, i * self._S + self._S * 0.03,
                       self._S * 0.32, self._S * 0.40),
                Qt.AlignCenter, str(r + 1))

    def set_theme(self, theme):
        self.theme = theme
        for sq, item in self._pieces.items():
            item.set_pixmap(self._piece_pixmap(item.symbol()), self._S)
        self._refresh_overlays()
        self.viewport().update()

    # ---------- position management --------------------------------------

    def _kill_animations(self):
        for a in self._animating:
            a.stop()
        self._animating = []
        # .stop() above does NOT emit finished(), so a ghost mid-fade
        # would never get its deleteLater() otherwise — remove any
        # survivors explicitly rather than relying on that signal.
        for ghost in self._fading_ghosts:
            self._scene.removeItem(ghost)
            ghost.deleteLater()
        self._fading_ghosts = []

    def rebuild(self):
        """Full rebuild of piece items at their final squares."""
        self._kill_animations()
        for item in self._pieces.values():
            self._scene.removeItem(item)
        self._pieces.clear()
        for square, piece in self.board.piece_map().items():
            item = PieceItem(piece.symbol())
            item.setZValue(self.Z_PIECE + chess.square_rank(square) * 0.01)
            item.setPos(self.square_to_pos(square))
            item.set_pixmap(self._piece_pixmap(piece.symbol()), self._S)
            self._scene.addItem(item)
            self._pieces[square] = item
        self._refresh_overlays()

    def set_position(self, board, last_move=None, animate=False):
        prev = self.board
        self.board = board
        self.deselect()
        self._last_move = last_move
        if animate and self.animations_enabled and last_move is not None:
            self._animate_transition(prev, board, last_move)
        else:
            self.rebuild()

    def _animate_transition(self, prev, board, move):
        # what physically moves: the played piece, plus the rook on castling
        movers = [(move.from_square, move.to_square)]
        if prev.is_castling(move):
            kf, kt = chess.square_file(move.from_square), \
                chess.square_file(move.to_square)
            r = chess.square_rank(move.from_square)
            rf, rt = (7, 5) if kt > kf else (0, 3)
            movers.append((chess.square(rf, r), chess.square(rt, r)))
        captured_square = None
        if prev.is_en_passant(move):
            captured_square = chess.square(
                chess.square_file(move.to_square),
                chess.square_rank(move.from_square))
        elif prev.is_capture(move):
            captured_square = move.to_square

        self._kill_animations()
        for item in self._pieces.values():
            self._scene.removeItem(item)
        self._pieces.clear()
        final_map = board.piece_map()
        anim_squares = {sq for frm, to in movers for sq in (frm, to)}
        for square, piece in final_map.items():
            if square in anim_squares:
                continue
            item = PieceItem(piece.symbol())
            item.setZValue(self.Z_PIECE + chess.square_rank(square) * 0.01)
            item.setPos(self.square_to_pos(square))
            item.set_pixmap(self._piece_pixmap(piece.symbol()), self._S)
            self._scene.addItem(item)
            self._pieces[square] = item

        # fading captured piece beneath the arriving one
        if captured_square is not None:
            cap_sym = prev.piece_at(captured_square)
            if cap_sym is not None:
                cap = PieceItem(cap_sym.symbol())
                cap.setPos(self.square_to_pos(captured_square))
                cap.set_pixmap(self._piece_pixmap(cap_sym.symbol()), self._S)
                cap.setZValue(self.Z_PIECE - 0.5)
                self._scene.addItem(cap)
                self._fading_ghosts.append(cap)
                fade = QPropertyAnimation(cap, b"opacity", self)
                fade.setDuration(230)
                fade.setStartValue(1.0)
                fade.setEndValue(0.0)
                fade.setEasingCurve(QEasingCurve.OutQuad)

                def _cleanup(g=cap):
                    if g in self._fading_ghosts:
                        self._fading_ghosts.remove(g)
                    self._scene.removeItem(g)
                    g.deleteLater()

                fade.finished.connect(_cleanup)
                self._animating.append(fade)
                fade.start()

        for frm, to in movers:
            piece = final_map.get(to)
            if piece is None:
                continue
            item = PieceItem(piece.symbol())
            item.setPos(self.square_to_pos(frm))
            item.set_pixmap(self._piece_pixmap(piece.symbol()), self._S)
            item.setZValue(self.Z_PIECE + 20)
            self._scene.addItem(item)
            self._pieces[to] = item
            anim = QPropertyAnimation(item, b"pos", self)
            anim.setDuration(MOVE_MS)
            anim.setStartValue(self.square_to_pos(frm))
            anim.setEndValue(self.square_to_pos(to))
            anim.setEasingCurve(QEasingCurve.OutQuint)

            def _land(it=item, sq=to):
                it.setZValue(self.Z_PIECE + chess.square_rank(sq) * 0.01)
                # small settle bounce on arrival, rather than stopping dead
                it.setScale(0.92)
                bounce = QPropertyAnimation(it, b"scale", self)
                bounce.setDuration(200)
                bounce.setStartValue(0.92)
                bounce.setEndValue(1.0)
                bounce.setEasingCurve(QEasingCurve.OutBack)
                self._animating.append(bounce)
                bounce.start()

            anim.finished.connect(_land)
            self._animating.append(anim)
            anim.start()
        self._refresh_overlays()

    # ---------- overlays -------------------------------------------------

    def _refresh_overlays(self):
        p = self.theme
        s = self._S
        self._sel_rect.hide()
        self._last_from.hide()
        self._last_to.hide()
        self._check_item.hide()
        if self._last_move is not None:
            lm = QColor(p.last_move)
            lm.setAlpha(105)
            for item, sq in ((self._last_from, self._last_move.from_square),
                             (self._last_to, self._last_move.to_square)):
                item.setRect(QRectF(self.square_to_pos(sq), QSizeF(s, s)))
                item.setBrush(QBrush(lm))
                item.show()
        if self._selected is not None:
            sel = QColor(p.select)
            sel.setAlpha(115)
            self._sel_rect.setRect(
                QRectF(self.square_to_pos(self._selected), QSizeF(s, s)))
            self._sel_rect.setBrush(QBrush(sel))
            self._sel_rect.show()
        if self.board.is_check():
            kq = self.board.king(self.board.turn)
            if kq is not None:
                pos = self.square_to_pos(kq)
                grad = QRadialGradient(pos.x() + s / 2, pos.y() + s / 2,
                                       s * 0.75)
                c = QColor(p.danger)
                c.setAlpha(150)
                c2 = QColor(p.danger)
                c2.setAlpha(0)
                grad.setColorAt(0.0, c)
                grad.setColorAt(0.55, c)
                grad.setColorAt(1.0, c2)
                self._check_item.setRect(QRectF(pos.x(), pos.y(), s, s))
                self._check_item.setBrush(QBrush(grad))
                self._check_item.show()

    def show_hints(self, moves):
        self.clear_hints()
        hint = QColor(self.theme.hint)
        for mv in moves:
            it = QGraphicsEllipseItem()
            it.setPen(QPen(Qt.NoPen))
            it.setZValue(self.Z_HINT)
            pos = self.square_to_pos(mv.to_square)
            if self.board.piece_at(mv.to_square) is not None:
                # capture: a ring hugging the square border
                m = self._S * 0.055
                it.setRect(QRectF(pos.x() + m, pos.y() + m,
                                  self._S - 2 * m, self._S - 2 * m))
                pen = QPen(hint, self._S * 0.09)
                pen.setCapStyle(Qt.RoundCap)
                it.setPen(pen)
            else:
                d = self._S * 0.30
                cx = pos.x() + (self._S - d) / 2
                cy = pos.y() + (self._S - d) / 2
                it.setRect(QRectF(cx, cy, d, d))
                it.setBrush(QBrush(hint))
            self._scene.addItem(it)
            self._hints.append(it)

    def clear_hints(self):
        for it in self._hints:
            self._scene.removeItem(it)
        self._hints = []

    def select(self, square):
        self._selected = square
        self._legal_for_selected = [
            m for m in self.board.legal_moves if m.from_square == square]
        self._refresh_overlays()
        self.show_hints(self._legal_for_selected)

    def deselect(self):
        self._selected = None
        self._legal_for_selected = []
        self._refresh_overlays()
        self.clear_hints()

    def set_view_only(self, flag):
        self.view_only = flag
        if flag:
            self.deselect()

    def set_flipped(self, flag):
        if self.flipped == flag:
            return
        self.flipped = flag
        self.deselect()
        self._kill_animations()
        self.rebuild()

    # ---------- interaction ----------------------------------------------

    def _human_to_move(self):
        return (not self.view_only and not self.board.is_game_over()
                and self.board.turn == self.human_color)

    def _try_move(self, from_sq, to_sq):
        moves = [m for m in self._legal_for_selected
                 if m.to_square == to_sq]
        if not moves:
            return False
        piece = self.board.piece_at(from_sq)
        needs_promo = (piece is not None
                       and piece.piece_type == chess.PAWN
                       and chess.square_rank(to_sq) in (0, 7))
        if needs_promo:
            promo = (self.choose_promotion(self.board.turn, to_sq)
                     if self.choose_promotion else chess.QUEEN)
            if promo is None:
                self.deselect()
                return True
            move = chess.Move(from_sq, to_sq, promotion=promo)
        else:
            move = moves[0]
        self.deselect()
        self.human_move.emit(move)
        return True

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if self.view_only:
            self.history_clicked.emit()
            return
        if not self._human_to_move():
            return
        sq = self.pos_to_square(self.mapToScene(e.position().toPoint()))
        if sq is None:
            self.deselect()
            return
        if self._selected is not None and sq != self._selected:
            if self._try_move(self._selected, sq):
                return
        piece = self.board.piece_at(sq)
        if sq == self._selected:
            self.deselect()  # second click on the same piece toggles
        elif piece is not None and piece.color == self.human_color:
            self._press_piece = self._pieces.get(sq)
            self._press_start = e.position()
            self._dragging = False
            self.select(sq)
        else:
            self.deselect()

    def mouseMoveEvent(self, e):
        item = self._press_piece
        if item is None or self._selected is None:
            return
        if not self._dragging:
            if (e.position() - self._press_start).manhattanLength() < 5:
                return
            self._dragging = True
            item.setZValue(self.Z_DRAG)
            item.setScale(1.12)
        item.setPos(self.mapToScene(e.position().toPoint())
                    - QPointF(self._S / 2, self._S / 2))

    def _snap_back(self, item, square):
        anim = QPropertyAnimation(item, b"pos", self)
        anim.setDuration(SNAP_MS)
        anim.setEndValue(self.square_to_pos(square))
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def _land(it=item, sq=square):
            it.setZValue(self.Z_PIECE + chess.square_rank(sq) * 0.01)

        anim.finished.connect(_land)
        self._animating.append(anim)
        anim.start()

    def _end_drag(self, pos):
        item = self._press_piece
        self._press_piece = None
        if item is None or not self._dragging:
            return
        self._dragging = False
        item.setScale(1.0)
        frm = self._selected
        target = self.pos_to_square(pos)
        ok = (target is not None and frm is not None and target != frm
              and self._try_move(frm, target))
        if not ok and frm is not None:
            self._snap_back(item, frm)

    def mouseReleaseEvent(self, e):
        if e is not None and e.button() != Qt.LeftButton:
            return
        self._end_drag(self.mapToScene(e.position().toPoint())
                       if e is not None else None)

    def leaveEvent(self, e):
        item = self._press_piece
        if item is not None and self._dragging and self._selected is not None:
            self._dragging = False
            item.setScale(1.0)
            self._snap_back(item, self._selected)
            self._press_piece = None
        super().leaveEvent(e)

    def map_square_to_global(self, square):
        return self.mapToGlobal(self.square_to_pos(square).toPoint())