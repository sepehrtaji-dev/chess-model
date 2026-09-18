"""Advanced ChessNet UI widgets: difficulty, evaluation and analysis."""

from PySide6.QtCore import Qt, Signal, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget
)


class DifficultySlider(QWidget):
    changed = Signal(str, int)

    LEVELS = (
        ("Easy", "easy"),
        ("Casual", "casual"),
        ("Medium", "medium"),
        ("Hard", "hard"),
        ("Expert", "expert"),
    )

    def __init__(self, theme, value=50, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setSingleStep(25)
        self.slider.setPageStep(25)
        self.slider.setValue(int(value))
        self.slider.setCursor(Qt.PointingHandCursor)

        self.title = QLabel()
        self.title.setObjectName("title")
        self.value_lbl = QLabel()
        self.value_lbl.setObjectName("caption")

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.addWidget(self.title)
        head.addStretch(1)
        head.addWidget(self.value_lbl)

        labels = QHBoxLayout()
        labels.setContentsMargins(0, 0, 0, 0)
        for name, _ in self.LEVELS:
            label = QLabel(name)
            label.setObjectName("caption")
            label.setAlignment(Qt.AlignCenter)
            labels.addWidget(label, 1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)
        root.addLayout(head)
        root.addWidget(self.slider)
        root.addLayout(labels)

        self.slider.valueChanged.connect(self._changed)
        self._changed(self.slider.value())

    @classmethod
    def value_for(cls, level):
        names = [name for _, name in cls.LEVELS]
        try:
            idx = names.index(level)
        except ValueError:
            idx = 2
        return idx * 25

    @classmethod
    def level_for(cls, value):
        idx = min(4, max(0, int(round(value / 25))))
        return cls.LEVELS[idx][1]

    @classmethod
    def label_for(cls, value):
        idx = min(4, max(0, int(round(value / 25))))
        return cls.LEVELS[idx][0]

    def _changed(self, value):
        label = self.label_for(value)
        self.title.setText("AI difficulty")
        self.value_lbl.setText(label)
        self.slider.setToolTip(
            "Drag to tune how strongly ChessNet plays. "
            "The setting changes sampling, safeguards and move selection."
        )
        self.changed.emit(self.level_for(value), value)

    def set_level(self, level):
        self.slider.blockSignals(True)
        self.slider.setValue(self.value_for(level))
        self.slider.blockSignals(False)
        self._changed(self.slider.value())

    def set_theme(self, theme):
        self.theme = theme


class EvaluationBar(QWidget):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.value = 0.0
        self.target = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(260)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._tick)
        self._anim.finished.connect(self._animation_finished)
        self.setMinimumHeight(30)
        self.setMaximumHeight(30)
        self.setToolTip("Position evaluation · positive favors White")

    def set_evaluation(self, score, animate=True):
        self.target = max(-1.0, min(1.0, float(score)))
        self._anim.stop()
        if animate:
            self._anim.setStartValue(self.value)
            self._anim.setEndValue(self.target)
            self._anim.start()
        else:
            self.value = self.target
            self.update()

    def _tick(self, value):
        self.value = float(value)
        self.update()

    def _animation_finished(self):
        self.value = self.target
        self.update()

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        mid = w / 2.0
        radius = 7
        track = QColor(self.theme.border)
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(0, 5, w, 20, radius, radius)

        if self.value >= 0:
            fill_w = (w / 2.0) * self.value
            p.setBrush(QColor(self.theme.accent))
            p.drawRoundedRect(mid, 5, max(0.0, fill_w), 20, radius, radius)
        else:
            fill_w = (w / 2.0) * (-self.value)
            p.setBrush(QColor(self.theme.muted))
            p.drawRoundedRect(mid - fill_w, 5, fill_w, 20, radius, radius)

        p.setPen(QColor(self.theme.text))
        p.drawLine(int(mid), 3, int(mid), 27)

        font = QFont()
        font.setPointSizeF(9)
        font.setBold(True)
        p.setFont(font)
        label = "White +" if self.value > 0.02 else "Black +" if self.value < -0.02 else "Equal"
        p.drawText(0, 0, int(mid) - 5, h, Qt.AlignVCenter | Qt.AlignLeft, label)
        p.end()


class AnalysisDialog(QDialog):
    def __init__(self, theme, summary, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("ChessNet — Game Analysis")
        self.setMinimumWidth(430)
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(10)

        title = QLabel("Game analysis")
        title.setObjectName("title")
        f = title.font()
        f.setPointSizeF(17)
        f.setBold(True)
        title.setFont(f)
        root.addWidget(title)

        metrics = QHBoxLayout()
        for name, value in (
            ("Accuracy", summary.get("accuracy", "—")),
            ("Best", str(summary.get("best", 0))),
            ("Mistakes", str(summary.get("mistakes", 0))),
            ("Blunders", str(summary.get("blunders", 0))),
        ):
            box = QVBoxLayout()
            val = QLabel(value)
            val.setObjectName("title")
            val.setAlignment(Qt.AlignCenter)
            cap = QLabel(name)
            cap.setObjectName("caption")
            cap.setAlignment(Qt.AlignCenter)
            box.addWidget(val)
            box.addWidget(cap)
            metrics.addLayout(box, 1)
        root.addLayout(metrics)

        coach = QLabel(summary.get("message", "No analysis available."))
        coach.setObjectName("caption")
        coach.setWordWrap(True)
        root.addWidget(coach)

        rows = summary.get("rows", [])
        if rows:
            details = QVBoxLayout()
            for row in rows[:8]:
                text = QLabel(
                    f"Move {row['ply']}: {row['move']} · "
                    f"{row['quality']} · best: {row['best']}"
                )
                text.setObjectName("caption")
                details.addWidget(text)
            root.addLayout(details)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, 0, Qt.AlignRight)
