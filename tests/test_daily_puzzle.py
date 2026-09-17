"""Puzzle of the Day must be deterministic and in range."""

from datetime import date, timedelta

from chess_lessons import LESSONS
from daily_puzzle import (daily_puzzle_summary, get_daily_lesson,
                          get_daily_lesson_index)


def test_same_day_same_puzzle():
    d = date(2026, 9, 17)
    assert get_daily_lesson_index(d) == get_daily_lesson_index(d)
    assert get_daily_lesson(d) is get_daily_lesson(d)


def test_puzzle_in_range_for_a_year():
    d = date(2026, 1, 1)
    for _ in range(365):
        idx = get_daily_lesson_index(d)
        assert 0 <= idx < len(LESSONS)
        d += timedelta(days=1)


def test_summary_mentions_lesson_and_level():
    text = daily_puzzle_summary()
    assert text and "·" in text
