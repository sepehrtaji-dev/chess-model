"""Tiny persistent settings store for ChessNet."""

import json
from pathlib import Path

SETTINGS_FILE = Path.home() / ".chessnet_settings.json"

DEFAULTS = {
    "theme": "dark",
    "sound": True,
    "animations": True,
    "difficulty": "medium",
    "difficulty_value": 50,
    "ai_style": "balanced",
    "adaptive": False,
    "games": 0,
    "wins": 0,
    "losses": 0,
    "draws": 0,
    "accuracy_sum": 0.0,
}

_cache = None


def load():
    global _cache
    if _cache is None:
        settings = dict(DEFAULTS)
        try:
            if SETTINGS_FILE.exists():
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    settings.update({k: v for k, v in data.items() if k in DEFAULTS})
        except Exception:
            pass

        if settings["theme"] not in ("dark", "light"):
            settings["theme"] = "dark"
        if settings["difficulty"] not in (
            "easy", "casual", "medium", "hard", "expert"
        ):
            settings["difficulty"] = "medium"
        if not isinstance(settings["difficulty_value"], (int, float)):
            settings["difficulty_value"] = 50
        settings["difficulty_value"] = max(0, min(100, int(settings["difficulty_value"])))
        if settings["ai_style"] not in (
            "balanced", "aggressive", "defensive", "tactical", "positional"
        ):
            settings["ai_style"] = "balanced"
        settings["sound"] = bool(settings["sound"])
        settings["animations"] = bool(settings["animations"])
        settings["adaptive"] = bool(settings["adaptive"])
        for key in ("games", "wins", "losses", "draws"):
            try:
                settings[key] = max(0, int(settings[key]))
            except Exception:
                settings[key] = 0
        try:
            settings["accuracy_sum"] = max(0.0, float(settings["accuracy_sum"]))
        except Exception:
            settings["accuracy_sum"] = 0.0
        _cache = settings
    return dict(_cache)


def save(**updates):
    global _cache
    settings = load()
    settings.update(updates)
    _cache = dict(settings)
    try:
        SETTINGS_FILE.write_text(
            json.dumps(settings, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def record_game(result, accuracy=None):
    settings = load()
    settings["games"] += 1
    if result == "1-0":
        settings["wins"] += 1
    elif result == "0-1":
        settings["losses"] += 1
    else:
        settings["draws"] += 1
    if accuracy is not None:
        settings["accuracy_sum"] += float(accuracy)
    save(**settings)


def average_accuracy():
    settings = load()
    if settings["games"] <= 0:
        return 0.0
    return settings["accuracy_sum"] / settings["games"]
