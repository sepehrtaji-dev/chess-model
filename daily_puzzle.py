"""Puzzle of the Day — pick one lesson deterministically from today's date."""

from datetime import date

from chess_lessons import LESSONS
from lesson_levels import get_lesson_level


def _day_seed(d: date | None = None) -> int:
    """Stable integer seed for a calendar day (UTC date)."""
    d = d or date.today()
    # YYYYMMDD as int — simple and stable across machines
    return d.year * 10000 + d.month * 100 + d.day


def get_daily_lesson_index(d: date | None = None) -> int:
    """Return the index into LESSONS for Puzzle of the Day."""
    if not LESSONS:
        return 0
    return _day_seed(d) % len(LESSONS)


def get_daily_lesson(d: date | None = None):
    """Return the Lesson object for today."""
    return LESSONS[get_daily_lesson_index(d)]


def daily_puzzle_summary(d: date | None = None) -> str:
    """Short label for the menu card / window title."""
    lesson = get_daily_lesson(d)
    level = get_lesson_level(lesson)
    return f"{lesson.title} · {level.capitalize()}"
