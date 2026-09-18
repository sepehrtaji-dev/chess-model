"""Palette + global QSS for the app. Dark is the default; light is a toggle."""

FONT_STACK = '"Segoe UI Variable Text", "Segoe UI", "Inter", system-ui, sans-serif'
MONO_STACK = '"Cascadia Mono", "Consolas", "Courier New", monospace'


class Palette:
    def __init__(self, name, window, panel, elevated, border, text, muted,
                 accent, accent_hover, accent_text, danger, board_light,
                 board_dark, last_move, select, hint):
        self.name = name
        self.window = window
        self.panel = panel
        self.elevated = elevated
        self.border = border
        self.text = text
        self.muted = muted
        self.accent = accent
        self.accent_hover = accent_hover
        self.accent_text = accent_text
        self.danger = danger
        self.board_light = board_light
        self.board_dark = board_dark
        self.last_move = last_move
        self.select = select
        self.hint = hint

    def coord_on_light(self):
        return self.board_dark

    def coord_on_dark(self):
        return self.board_light


DARK = Palette(
    name="dark",
    window="#101318",
    panel="#191e26",
    elevated="#212834",
    border="#2b3442",
    text="#e9edf3",
    muted="#8d97a8",
    accent="#f2b544",
    accent_hover="#ffc95e",
    accent_text="#231a05",
    danger="#e05d5d",
    board_light="#ecd9b9",
    board_dark="#a5714a",
    last_move="#f2b544",
    select="#f2b544",
    hint="rgba(16, 19, 24, 0.28)",
)

LIGHT = Palette(
    name="light",
    window="#edeef2",
    panel="#ffffff",
    elevated="#f6f7fa",
    border="#d8dde6",
    text="#1b2330",
    muted="#5c6675",
    accent="#c98a12",
    accent_hover="#b27a0d",
    accent_text="#ffffff",
    danger="#c0392b",
    board_light="#f0dcbc",
    board_dark="#b58863",
    last_move="#f2b544",
    select="#f2b544",
    hint="rgba(20, 25, 35, 0.25)",
)

THEMES = {"dark": DARK, "light": LIGHT}


def qss(p):
    return f"""
    * {{
        font-family: {FONT_STACK};
        outline: none;
    }}
    QMainWindow, QDialog {{
        background: {p.window};
    }}
    QFrame#panel {{
        background: {p.panel};
        border: 1px solid {p.border};
        border-radius: 14px;
    }}
    QLabel#title {{
        color: {p.text};
        font-size: 15px;
        font-weight: 600;
    }}
    QLabel#caption {{
        color: {p.muted};
        font-size: 11px;
    }}
    QLabel#status {{
        color: {p.text};
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton {{
        background: {p.elevated};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 9px;
        padding: 8px 14px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        border-color: {p.accent};
        color: {p.accent};
    }}
    QPushButton:disabled {{
        color: {p.muted};
        border-color: {p.border};
    }}
    QPushButton#primary {{
        background: {p.accent};
        color: {p.accent_text};
        border: none;
    }}
    QPushButton#primary:hover {{
        background: {p.accent_hover};
        color: {p.accent_text};
    }}
    QPushButton#moveBtn {{
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 4px 8px;
        font-family: {MONO_STACK};
        font-size: 13px;
        font-weight: 600;
        color: {p.text};
        text-align: left;
    }}
    QPushButton#moveBtn:hover {{
        background: {p.elevated};
    }}
    QPushButton#moveBtn:checked {{
        background: {p.accent};
        color: {p.accent_text};
    }}
    QSlider::groove:horizontal {{
        height: 7px;
        background: {p.border};
        border-radius: 4px;
    }}
    QSlider::sub-page:horizontal {{
        background: {p.accent};
        border-radius: 4px;
    }}
    QSlider::add-page:horizontal {{
        background: {p.elevated};
        border-radius: 4px;
    }}
    QSlider::handle:horizontal {{
        width: 18px;
        height: 18px;
        margin: -6px 0;
        background: {p.panel};
        border: 2px solid {p.accent};
        border-radius: 9px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {p.accent};
    }}
    QComboBox {{
        background: {p.elevated};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 9px;
        padding: 7px 12px;
        font-size: 12px;
        font-weight: 600;
    }}
    QComboBox:hover {{
        border-color: {p.accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox QAbstractItemView {{
        background: {p.panel};
        color: {p.text};
        border: 1px solid {p.border};
        selection-background-color: {p.accent};
        selection-color: {p.accent_text};
        outline: none;
    }}
    QScrollArea {{
        background: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {p.border};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p.muted};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QToolTip {{
        background: {p.elevated};
        color: {p.text};
        border: 1px solid {p.border};
        padding: 6px 8px;
        border-radius: 6px;
    }}
    """
