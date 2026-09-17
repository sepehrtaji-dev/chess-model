"""Tiny JSON settings store (~/.chessnet_settings.json).

Remembers the user's theme, sound / animation toggles and AI effort
across sessions. Degrades silently to defaults on any error.
"""

import json
from pathlib import Path

SETTINGS_FILE = Path.home() / ".chessnet_settings.json"

DEFAULTS = {
    "theme": "dark",         # dark | light
    "sound": True,
    "animations": True,
    "difficulty": "medium",  # easy | medium | hard
}

_cache = None


def load():
    """Return the current settings dict (validated, defaults filled in)."""
    global _cache
    if _cache is None:
        settings = dict(DEFAULTS)
        try:
            if SETTINGS_FILE.exists():
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    settings.update({k: v for k, v in data.items()
                                     if k in DEFAULTS})
        except Exception:
            pass
        if settings["theme"] not in ("dark", "light"):
            settings["theme"] = "dark"
        if settings["difficulty"] not in ("easy", "medium", "hard"):
            settings["difficulty"] = "medium"
        settings["sound"] = bool(settings["sound"])
        settings["animations"] = bool(settings["animations"])
        _cache = settings
    return dict(_cache)


def save(**updates):
    """Persist a partial update (e.g. save(theme="light"))."""
    global _cache
    settings = load()
    settings.update(updates)
    _cache = dict(settings)
    try:
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2),
                                 encoding="utf-8")
    except Exception:
        pass
