"""Lesson difficulty levels and helpers."""

LESSON_LEVELS = {
    "pawn": "beginner",
    "knight": "beginner",
    "bishop": "beginner",
    "rook": "beginner",
    "queen": "beginner",
    "king": "beginner",
    "castle": "beginner",
    "enpassant": "beginner",
    "promote": "beginner",
    "capture_pawn": "beginner",
    "capture_knight": "beginner",
    "center_control": "beginner",
    "develop_bishop": "beginner",
    "castle_queenside": "beginner",
    "check": "intermediate",
    "opening": "intermediate",
    "fork": "intermediate",
    "pin": "intermediate",
    "skewer": "intermediate",
    "simple_trade": "intermediate",
    "defend_piece": "intermediate",
    "discovered_attack": "intermediate",
    "rook_lift": "intermediate",
    "knight_outpost": "intermediate",
    "pawn_break": "intermediate",
    "king_activity": "intermediate",
    "mate": "advanced",
    "discovered_check": "advanced",
    "double_check": "advanced",
    "opposition": "advanced",
    "smothered_mate": "advanced",
    "back_rank_threat": "advanced",
    "queen_mate": "advanced",
}


def get_lesson_level(lesson) -> str:
    """Return the difficulty level of a lesson (beginner|intermediate|advanced)."""
    return LESSON_LEVELS.get(getattr(lesson, "id", ""), "beginner")
