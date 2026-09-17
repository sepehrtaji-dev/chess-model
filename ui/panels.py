"""Side-panel widgets: player cards, move list, model insights, dialogs."""

import math

import chess
from PySide6.QtCore import (QEasingCurve, QPoint, QRectF, QSize, Qt,
                            QTimer, QVariantAnimation, Signal)
from PySide6.QtGui import (QBrush, QColor, QFont, QPainter, QPen, QPixmap)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFrame,
                               QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QSizePolicy, QVBoxLayout, QWidget,
                               QGraphicsOpacityEffect, QProgressBar)

from .pieces import SVG
from .theme import MONO_STACK

_renderers = {}


def render_piece(symbol, size, dpr=1.0):
    if symbol not in _renderers:
        _renderers[symbol] = QSvgRenderer(SVG[symbol].encode("utf-8"))
    px = int(size * dpr)
    pm = QPixmap(px, px)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    _renderers[symbol].render(p, QRectF(0, 0, px, px))
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def avatar_pixmap(symbol, size, bg, fg, dpr=1.0):
    px = int(size * dpr)
    pm = QPixmap(px, px)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(bg))
    p.drawRoundedRect(QRectF(0, 0, px, px), px * 0.28, px * 0.28)
    piece = render_piece(symbol, size * 0.74, dpr)
    off = (size - size * 0.74) / 2
    p.drawPixmap(QPoint(int(off * dpr), int(off * dpr)), piece)
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


class PlayerCard(QFrame):
    """Avatar, name, captured pieces, material balance, thinking state."""

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setObjectName("panel")
        self.setMinimumHeight(76)
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)

        self.avatar = QLabel()
        self.avatar.setFixedSize(46, 46)
        root.addWidget(self.avatar)

        left = QVBoxLayout()
        left.setSpacing(1)
        self.name_lbl = QLabel()
        self.name_lbl.setObjectName("title")
        left.addWidget(self.name_lbl)
        self.sub_lbl = QLabel()
        self.sub_lbl.setObjectName("caption")
        left.addWidget(self.sub_lbl)
        root.addLayout(left)
        root.addStretch(1)

        right = QVBoxLayout()
        right.setSpacing(4)
        right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.turn_pill = QLabel("to move")
        self.turn_pill.hide()
        self.think_bar = QProgressBar()
        self.think_bar.setRange(0, 0)
        self.think_bar.setFixedSize(92, 4)
        self.think_bar.hide()
        top_right = QHBoxLayout()
        top_right.setAlignment(Qt.AlignRight)
        top_right.addWidget(self.turn_pill)
        top_right.addWidget(self.think_bar)
        right.addLayout(top_right)
        self.captured_lbl = QLabel()
        self.captured_lbl.setObjectName("caption")
        right.addWidget(self.captured_lbl, 0, Qt.AlignRight)
        root.addLayout(right)

    def set_identity(self, name, subtitle, avatar_symbol):
        self._avatar_symbol = avatar_symbol
        self._name = name
        self._sub = subtitle
        self.name_lbl.setText(name)
        self.sub_lbl.setText(subtitle)
        dpr = self.devicePixelRatioF()
        self.avatar.setPixmap(avatar_pixmap(
            avatar_symbol, 46, self.theme.elevated, self.theme.text, dpr))

    def set_captured(self, symbols, diff):
        dpr = self.devicePixelRatioF()
        h = 20
        text = ""
        if symbols:
            pm = QPixmap(int(h * len(symbols) * 0.72), int(h))
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            for i, s in enumerate(symbols):
                p.drawPixmap(QPoint(int(i * h * 0.72), 0),
                             render_piece(s, h, dpr))
            p.end()
            self.captured_lbl.setPixmap(pm)
        else:
            self.captured_lbl.setPixmap(QPixmap())
        if diff > 0:
            self.captured_lbl.setToolTip(f"+{diff} material")
        else:
            self.captured_lbl.setToolTip("")

    def set_turn(self, mine):
        if mine and not self.turn_pill.isVisible():
            self.turn_pill.setStyleSheet(
                f"background: {self.theme.accent};"
                f"color: {self.theme.accent_text};"
                "border-radius: 7px; padding: 2px 10px;"
                "font-size: 10px; font-weight: 700;")
        self.turn_pill.setVisible(mine)

    def set_thinking(self, flag):
        self.think_bar.setVisible(flag)

    def set_theme(self, theme):
        self.theme = theme
        if getattr(self, "_avatar_symbol", None):
            self.set_identity(self._name, self._sub, self._avatar_symbol)


class MoveList(QScrollArea):
    """Scrollable SAN move list; clicking a ply reviews that position."""

    ply_selected = Signal(int)

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.container = QFrame()
        self.container.setObjectName("panel")
        self.box = QVBoxLayout(self.container)
        self.box.setContentsMargins(10, 10, 10, 10)
        self.box.setSpacing(2)
        self.box.addStretch(1)
        self.setWidget(self.container)
        self._sans = []

    def set_moves(self, sans, current_ply=None):
        self._sans = sans
        while self.box.count() > 1:
            item = self.box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for i in range(0, len(sans), 2):
            row = QFrame()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)
            num = QLabel(f"{i // 2 + 1}.")
            num.setObjectName("caption")
            num.setFixedWidth(28)
            h.addWidget(num)
            for j in range(2):
                ply = i + j
                if ply >= len(sans):
                    break
                btn = QPushButton(sans[ply])
                btn.setObjectName("moveBtn")
                btn.setCursor(Qt.PointingHandCursor)
                btn.setCheckable(True)
                btn.setChecked(current_ply == ply + 1)
                btn.clicked.connect(
                    lambda _=False, p=ply: self.ply_selected.emit(p + 1))
                h.addWidget(btn)
            self.box.insertWidget(self.box.count() - 1, row)
        if current_ply:
            self.scroll_to_bottom()

    def scroll_to_bottom(self):
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def highlight(self, current_ply):
        for row in self.findChildren(QPushButton):
            row.setChecked(False)
        if current_ply:
            idx = current_ply - 1
            rows = [b for b in self.container.findChildren(QPushButton)]
            if 0 <= idx < len(rows):
                rows[idx].setChecked(True)
                self.ensureWidgetVisible(rows[idx])


class PolicyBars(QWidget):
    """Painted top-5 policy bars with animated fill."""

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._rows = []          # (san, target_frac, chosen)
        self._starts = []
        self._targets = []
        self._fracs = []
        self._anim = None
        self.setMinimumHeight(5 * 34)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(self, rows, animate=True):
        # rows: [(san, prob, chosen)]
        self._rows = rows
        self._starts = list(self._fracs) if self._fracs else [0.0] * len(rows)
        self._fracs = list(self._starts[:len(rows)])
        if self._anim is not None:
            self._anim.stop()
            self._anim = None
        if animate and rows:
            self._targets = [r[1] for r in rows]
            self._anim = QVariantAnimation(self)
            self._anim.setDuration(450)
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.setEasingCurve(QEasingCurve.OutCubic)
            self._anim.valueChanged.connect(self._on_tick)
            self._anim.start()
        else:
            self._fracs = [r[1] for r in rows]
        self.update()

    def _on_tick(self, t):
        self._fracs = [s + (tg - s) * t for s, tg
                       in zip(self._starts, self._targets)]
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        th = self.theme
        mono = QFont(MONO_STACK.strip('"').split('", "')[0])
        mono.setPointSizeF(11)
        mono.setBold(True)
        h = 34
        for i, (san, frac_target, chosen) in enumerate(self._rows):
            y = i * h + 3
            frac = self._fracs[i] if i < len(self._fracs) else frac_target
            # track
            track = QColor(th.border)
            track.setAlpha(120)
            p.setPen(Qt.NoPen)
            p.setBrush(track)
            p.drawRoundedRect(QRectF(64, y + 6, self.width() - 64, 16), 8, 8)
            # fill
            fill = QColor(th.accent)
            if chosen:
                fill = QColor(th.accent)
            else:
                fill.setAlpha(170)
            p.setBrush(fill)
            w = max(16.0, (self.width() - 64) * max(frac, 0.0))
            p.drawRoundedRect(QRectF(64, y + 6, w, 16), 8, 8)
            # san
            p.setPen(QColor(chosen and th.accent or th.text))
            p.setFont(mono)
            p.drawText(QRectF(0, y, 58, 28),
                       Qt.AlignLeft | Qt.AlignVCenter, san)
            # pct
            pct = QColor(th.muted)
            p.setPen(pct)
            pct_font = QFont()
            pct_font.setPointSizeF(9.5)
            p.setFont(pct_font)
            p.drawText(QRectF(64, y, self.width() - 70, 28),
                       Qt.AlignRight | Qt.AlignVCenter,
                       f"{frac_target * 100:.1f}%")
        p.end()


class ModelPanel(QFrame):
    """'Model insights': top-5 policy moves after each AI reply."""

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setObjectName("panel")
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)
        head = QHBoxLayout()
        title = QLabel("Model insights")
        title.setObjectName("title")
        head.addWidget(title)
        head.addStretch(1)
        self.state_lbl = QLabel("")
        self.state_lbl.setObjectName("caption")
        head.addWidget(self.state_lbl)
        root.addLayout(head)
        cap = QLabel("ChessNet policy · softmax over legal moves")
        cap.setObjectName("caption")
        root.addWidget(cap)
        self.bars = PolicyBars(theme)
        root.addWidget(self.bars)
        self.set_idle()

    def set_idle(self):
        self.state_lbl.setText("waiting")
        self.bars.setEnabled(True)
        self.bars.set_data([], animate=False)

    def set_thinking(self):
        self.state_lbl.setText("thinking…")

    def set_top(self, rows):
        # rows: [(san, prob, chosen)]
        self.state_lbl.setText("policy")
        self.bars.set_data(rows, animate=True)


class GameOverCard(QFrame):
    """Centered translucent result card overlaid on the board."""

    new_game_requested = Signal()
    review_requested = Signal()

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setObjectName("panel")
        self.setFixedWidth(320)
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(6)
        self.title = QLabel()
        self.title.setObjectName("title")
        self.title.setAlignment(Qt.AlignCenter)
        font = self.title.font()
        font.setPointSizeF(15)
        font.setBold(True)
        self.title.setFont(font)
        root.addWidget(self.title)
        self.sub = QLabel()
        self.sub.setObjectName("caption")
        self.sub.setWordWrap(True)
        self.sub.setAlignment(Qt.AlignCenter)
        root.addWidget(self.sub)
        btns = QHBoxLayout()
        btns.setSpacing(8)
        self.review_btn = QPushButton("Review board")
        self.new_btn = QPushButton("New game")
        self.new_btn.setObjectName("primary")
        btns.addWidget(self.review_btn)
        btns.addWidget(self.new_btn)
        root.addLayout(btns)
        self.new_btn.clicked.connect(self.new_game_requested)
        self.review_btn.clicked.connect(self.review_requested)
        self.hide()

    def recenter(self):
        parent = self.parentWidget()
        if parent is None:
            return
        self.move((parent.width() - self.width()) // 2,
                  (parent.height() - self.height()) // 2)

    def show_result(self, title, sub):
        self.title.setText(title)
        self.sub.setText(sub)
        self.adjustSize()
        self.show()
        self.raise_()
        self.recenter()
        eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(eff)
        anim = QVariantAnimation(self)
        anim.setDuration(260)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.valueChanged.connect(lambda v: eff.setOpacity(v))
        anim.start(QVariantAnimation.DeleteWhenStopped)


class PromotionPicker(QDialog):
    """Tiny frameless popup with the four promotion pieces."""

    def __init__(self, theme, color, global_pos, square_px, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet(
            f"background: {theme.elevated}; border: 1px solid "
            f"{theme.border}; border-radius: 10px;")
        self.result_piece = None
        h = QHBoxLayout(self)
        h.setContentsMargins(8, 8, 8, 8)
        h.setSpacing(4)
        order = [chess.QUEEN, chess.ROOK, chess.KNIGHT, chess.BISHOP]
        sym_of = {chess.QUEEN: "Q", chess.ROOK: "R",
                  chess.KNIGHT: "N", chess.BISHOP: "B"}
        for piece in order:
            sym = sym_of[piece] if color == chess.WHITE \
                else sym_of[piece].lower()
            btn = QPushButton()
            btn.setFlat(True)
            btn.setFixedSize(int(square_px * 0.9), int(square_px * 0.9))
            btn.setIcon(render_piece(sym, square_px * 0.8,
                                     self.devicePixelRatioF()))
            btn.setIconSize(QSize(int(square_px * 0.8),
                                  int(square_px * 0.8)))
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda _=False, p=piece: self._pick(p))
            h.addWidget(btn)
        self.adjustSize()
        self._place_at(global_pos)

    def _place_at(self, pos):
        """Open next to the target square without leaving the screen."""
        screen = QApplication.primaryScreen().availableGeometry()
        x, y = pos.x(), pos.y()
        if x + self.width() > screen.right():
            x -= self.width()          # would overflow right → open left
        if y + self.height() > screen.bottom():
            y -= self.height() + 8     # would overflow bottom → open above
        self.move(max(screen.left(), int(x)), max(screen.top(), int(y)))

    def _pick(self, piece):
        self.result_piece = piece
        self.accept()

    @staticmethod
    def pick(theme, color, global_pos, square_px, parent=None):
        dlg = PromotionPicker(theme, color, global_pos, square_px, parent)
        dlg.exec()
        return dlg.result_piece


class NewGameDialog(QDialog):
    """Choose the game mode: vs the model (pick a side) or two players."""

    def __init__(self, theme, parent=None, first_run=False):
        super().__init__(parent)
        self.theme = theme
        self.chosen_color = None
        self.chosen_mode = "ai"  # "ai" | "two"
        self.setWindowTitle("New game")
        self.setModal(True)
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)
        title = QLabel("New game")
        title.setObjectName("title")
        f = title.font()
        f.setPointSizeF(16)
        f.setBold(True)
        title.setFont(f)
        root.addWidget(title, 0, Qt.AlignLeft)
        sub = QLabel("Versus the model — choose your side.")
        sub.setObjectName("caption")
        root.addWidget(sub, 0, Qt.AlignLeft)
        cards = QHBoxLayout()
        cards.setSpacing(10)
        options = [("White", "K", chess.WHITE), ("Random", "n", None),
                   ("Black", "q", chess.BLACK)]
        for label, sym, color in options:
            card = QPushButton()
            card.setFixedHeight(92)
            lay = QVBoxLayout(card)
            lay.setSpacing(6)
            icon = QLabel()
            icon.setPixmap(render_piece(sym, 34, self.devicePixelRatioF()))
            icon.setAlignment(Qt.AlignCenter)
            lay.addWidget(icon)
            txt = QLabel(label)
            txt.setObjectName("caption")
            txt.setAlignment(Qt.AlignCenter)
            lay.addWidget(txt)
            card.clicked.connect(
                lambda _=False, c=color: self._choose(c))
            cards.addWidget(card, 1)
        root.addLayout(cards)

        two_btn = QPushButton("👥  Two players — pass & play")
        two_btn.setToolTip("Share the board: the game flips control "
                           "between both human players.")
        two_btn.clicked.connect(self._choose_two)
        root.addWidget(two_btn, 0, Qt.AlignLeft)

        if not first_run:
            cancel = QPushButton("Cancel")
            cancel.clicked.connect(self.reject)
            root.addWidget(cancel, 0, Qt.AlignRight)

    def _choose(self, color):
        import random
        self.chosen_mode = "ai"
        self.chosen_color = color if color is not None else random.choice(
            [chess.WHITE, chess.BLACK])
        self.accept()

    def _choose_two(self):
        self.chosen_mode = "two"
        self.chosen_color = chess.WHITE
        self.accept()

    @staticmethod
    def ask(theme, parent=None, first_run=False):
        """Return (mode, color); color is None when cancelled."""
        dlg = NewGameDialog(theme, parent, first_run)
        dlg.exec()
        return dlg.chosen_mode, dlg.chosen_color