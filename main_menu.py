"""ChessNet main menu — Play with Model / Lessons / Puzzle of the Day."""

import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
                               QMainWindow, QPushButton, QVBoxLayout, QWidget)

from daily_puzzle import daily_puzzle_summary, get_daily_lesson_index
from ui import theme as theme_mod
from ui.panels import render_piece
import settings as settings_mod


class MenuCard(QFrame):
    clicked = Signal()

    def __init__(self, title, subtitle, glyph, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setObjectName("menuCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(240, 240)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        self.icon_lbl = QLabel()
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setPixmap(render_piece(glyph, 88,
                                             self.devicePixelRatioF()))
        lay.addWidget(self.icon_lbl, 1)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("title")
        tf = title_lbl.font()
        tf.setPointSizeF(18)
        tf.setBold(True)
        title_lbl.setFont(tf)
        title_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(title_lbl)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setObjectName("caption")
        sub_lbl.setWordWrap(True)
        sub_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub_lbl)

        self._apply_theme()

    def _apply_theme(self):
        th = self.theme
        self.setStyleSheet(f"""
            QFrame#menuCard {{
                background: {th.elevated};
                border: 1px solid {th.border};
                border-radius: 16px;
            }}
            QFrame#menuCard:hover {{
                border: 1px solid {th.accent};
            }}
        """)

    def set_theme(self, theme):
        self.theme = theme
        self._apply_theme()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class MainMenu(QMainWindow):
    def __init__(self, theme_name="dark"):
        super().__init__()
        self._theme_name = theme_name
        self.theme = theme_mod.THEMES[theme_name]
        self.setWindowTitle("ChessNet")
        self.setMinimumSize(900, 560)
        self.resize(1020, 640)
        self._build_ui()
        self._apply_theme()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(44, 36, 44, 44)
        root.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel("ChessNet")
        title.setObjectName("title")
        tf = title.font()
        tf.setPointSizeF(30)
        tf.setBold(True)
        title.setFont(tf)
        top.addWidget(title)
        top.addStretch(1)

        self.theme_btn = QPushButton("☀")
        self.theme_btn.setCheckable(True)
        self.theme_btn.setFixedWidth(38)
        self.theme_btn.setChecked(self._theme_name == "light")
        self.theme_btn.toggled.connect(self._toggle_theme)
        top.addWidget(self.theme_btn)
        root.addLayout(top)

        sub = QLabel("Learn the game, solve today's puzzle, or take on the trained CNN.")
        sub.setObjectName("caption")
        root.addWidget(sub)
        root.addSpacing(18)

        cards = QHBoxLayout()
        cards.setSpacing(18)

        self.play_card = MenuCard(
            "Play with Model",
            "Choose your side and an effort level, then play the trained CNN.",
            "N", self.theme)
        self.lessons_card = MenuCard(
            "Lessons",
            "Interactive step-by-step tutorials — from how a pawn moves "
            "to checkmate patterns.",
            "K", self.theme)
        self.puzzle_card = MenuCard(
            "Puzzle of the Day",
            daily_puzzle_summary(),
            "Q", self.theme)

        self.play_card.clicked.connect(self._open_play)
        self.lessons_card.clicked.connect(self._open_lessons)
        self.puzzle_card.clicked.connect(self._open_daily_puzzle)

        cards.addWidget(self.play_card, 1)
        cards.addWidget(self.lessons_card, 1)
        cards.addWidget(self.puzzle_card, 1)
        root.addLayout(cards, 1)

        foot = QLabel(
            "Shortcuts — Play: Enter · Lessons: Ctrl+L · Puzzle: Ctrl+P · "
            "Lessons nav: ←/→ · Reset: Ctrl+R."
        )
        foot.setObjectName("caption")
        root.addWidget(foot)

        QShortcut(QKeySequence("Return"), self, self._open_play)
        QShortcut(QKeySequence("Ctrl+L"), self, self._open_lessons)
        QShortcut(QKeySequence("Ctrl+P"), self, self._open_daily_puzzle)

    def _apply_theme(self):
        self.setStyleSheet(theme_mod.qss(self.theme))

    def _toggle_theme(self, want_light):
        self.theme_btn.setText("☾" if want_light else "☀")
        self._theme_name = "light" if want_light else "dark"
        self.theme = theme_mod.THEMES[self._theme_name]
        self._apply_theme()
        self.play_card.set_theme(self.theme)
        self.lessons_card.set_theme(self.theme)
        self.puzzle_card.set_theme(self.theme)
        settings_mod.save(theme=self._theme_name)

    def _open_play(self):
        from chess_app import MainWindow
        self.game = MainWindow(self._theme_name, interactive=True,
                               has_menu=True)
        self.game.back_requested.connect(self._show_again)
        self.game.show()
        self.hide()

    def _open_lessons(self):
        from lessons_window import LessonsWindow
        self.lessons = LessonsWindow(self._theme_name, parent=None)
        self.lessons.back_requested.connect(self._show_again)
        self.lessons.show()
        self.hide()

    def _open_daily_puzzle(self):
        from lessons_window import LessonsWindow
        idx = get_daily_lesson_index()
        self.lessons = LessonsWindow(self._theme_name, parent=None)
        self.lessons.back_requested.connect(self._show_again)
        self.lessons.show()
        # Load today's puzzle after the window's initial lesson load.
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.lessons.open_lesson(idx))
        self.lessons.setWindowTitle(
            f"ChessNet — Puzzle of the Day · {daily_puzzle_summary()}"
        )
        self.hide()

    def _show_again(self):
        # Pick up a theme that may have been changed inside the
        # play/lessons windows while this menu was hidden.
        saved = settings_mod.load()["theme"]
        if saved != self._theme_name:
            self.theme_btn.blockSignals(True)
            self.theme_btn.setChecked(saved == "light")
            self.theme_btn.blockSignals(False)
            self._toggle_theme(saved == "light")
        self.show()
        self.raise_()
        self.activateWindow()


def main():
    app = QApplication(sys.argv)
    win = MainMenu(settings_mod.load()["theme"])
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
