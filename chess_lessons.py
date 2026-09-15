"""Interactive chess lessons: content + move-checking predicates."""

from dataclasses import dataclass
from typing import Callable

import chess


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    subtitle: str
    intro: str
    fen: str
    task: str
    hint: str
    success: str
    answer_uci: str
    answer_san: str
    check: Callable[[chess.Move, chess.Board, chess.Board], bool]


def _uci(*accepted):
    accepted = set(a for a in accepted if a)
    return lambda move, before, after: move.uci() in accepted


def _any_piece(piece_type):
    def check(move, before, after):
        piece = before.piece_at(move.from_square)
        return piece is not None and piece.piece_type == piece_type
    return check


def _is_check(move, before, after):
    return after.is_check()


def _is_mate(move, before, after):
    return after.is_checkmate()


def _is_promotion(move, before, after):
    return move.promotion is not None


LESSONS = [
    Lesson(
        id="pawn",
        title="The Pawn",
        subtitle="forward one, or two from home",
        intro=("Pawns move straight forward one square at a time. From their "
               "home rank they may dash two squares if the path is clear. "
               "They never move sideways or backwards, and they capture "
               "diagonally."),
        fen="4k3/8/8/8/8/8/4P3/4K3 w - - 0 1",
        task="Push the pawn forward — one or two squares. Try the two-square "
             "dash from e2 to e4.",
        hint="Click the pawn on e2, then click e3 (one step) or e4 (two steps).",
        success=("The one-square step is always available. The two-square dash "
                 "is only allowed from the pawn's starting rank."),
        answer_uci="e2e4", answer_san="e4",
        check=_any_piece(chess.PAWN),
    ),
    Lesson(
        id="knight",
        title="The Knight",
        subtitle="the L-shaped jumper",
        intro=("The knight moves in an L — two squares one way, then one "
               "square at a right angle. It is the only piece that can jump "
               "over others."),
        fen="4k3/8/8/8/8/8/8/1N2K3 w - - 0 1",
        task="Hop the knight. Any L-shaped move counts — c3 is the classic "
             "developing square.",
        hint="From b1 the knight can reach a3 or c3. Try c3.",
        success=("c3 is the knight's favourite square — from there it eyes e4 "
                 "and d5. Every knight move is the same L, every time."),
        answer_uci="b1c3", answer_san="Nc3",
        check=_any_piece(chess.KNIGHT),
    ),
    Lesson(
        id="bishop",
        title="The Bishop",
        subtitle="the diagonal slider",
        intro=("Bishops glide any distance along a diagonal. Each bishop is "
               "locked to one colour of square for the whole game — you start "
               "with one on each colour."),
        fen="4k3/8/8/8/8/8/8/2B1K3 w - - 0 1",
        task="Slide the bishop along a diagonal — any diagonal. Try c1 to g5.",
        hint="Follow the diagonal up-right: d2, e3, f4, g5. Or go the other "
             "way to b2 or a3.",
        success=("Bishops stay on one colour forever — that's why you need "
                 "both of them."),
        answer_uci="c1g5", answer_san="Bg5",
        check=_any_piece(chess.BISHOP),
    ),
    Lesson(
        id="rook",
        title="The Rook",
        subtitle="the straight-line slider",
        intro=("Rooks move any number of squares along a rank (row) or a file "
               "(column), as long as nothing blocks the path."),
        fen="4k3/8/8/8/8/8/8/R3K3 w - - 0 1",
        task="Move the rook along a file or a rank. Try sending it all the "
             "way up to a8.",
        hint="Click the rook, then click a far square on the a-file or the "
             "first rank.",
        success="Rooks love open files — that's where they do their best work.",
        answer_uci="a1a8", answer_san="Ra8+",
        check=_any_piece(chess.ROOK),
    ),
    Lesson(
        id="queen",
        title="The Queen",
        subtitle="rook and bishop combined",
        intro=("The queen moves any distance along a rank, a file, or a "
               "diagonal. She is the strongest piece on the board — worth "
               "about nine pawns."),
        fen="4k3/8/8/8/8/8/8/3QK3 w - - 0 1",
        task="Move the queen. She can go straight like a rook, or diagonally "
             "like a bishop. Try d1 to d8.",
        hint="Click the queen, then any square on her rank, file, or diagonal.",
        success="One queen, many threats — she controls whole lines at once.",
        answer_uci="d1d8", answer_san="Qd8+",
        check=_any_piece(chess.QUEEN),
    ),
    Lesson(
        id="king",
        title="The King",
        subtitle="one square at a time",
        intro=("The king moves exactly one square in any direction. He cannot "
               "step into check — a square attacked by an enemy piece — and "
               "if he is trapped, that is checkmate."),
        fen="4k3/8/8/8/8/8/8/4K3 w - - 0 1",
        task="Step the king one square in any direction.",
        hint="Click the king, then any adjacent square.",
        success=("Slow but crucial — the king is your most important piece. "
                 "Lose him and the game is over."),
        answer_uci="e1e2", answer_san="Ke2",
        check=_any_piece(chess.KING),
    ),
    Lesson(
        id="castle",
        title="Castling",
        subtitle="the only two-piece move",
        intro=("Once per game, if neither the king nor the chosen rook has "
               "moved and the squares between them are empty, the king slides "
               "two squares toward a rook and the rook jumps over him."),
        fen="r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
        task="Castle kingside — the king jumps two squares toward the h1 rook.",
        hint="Grab the king on e1 and drop it on g1.",
        success=("Castling tucks your king away and activates a rook in one "
                 "move. Do it early in every game."),
        answer_uci="e1g1", answer_san="O-O",
        check=_uci("e1g1"),
    ),
    Lesson(
        id="enpassant",
        title="En passant",
        subtitle="the odd one out",
        intro=("If a pawn tries to sneak past an enemy pawn by using its "
               "double step, the enemy pawn may capture it as if it had only "
               "moved one square. This must be done immediately."),
        fen="4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2",
        task="Black just played d7-d5. Capture the pawn en passant.",
        hint="Move your e5 pawn diagonally onto the empty d6 square.",
        success=("En passant — French for 'in passing' — the trickiest pawn "
                 "rule. It must be played right away, or the chance is gone."),
        answer_uci="e5d6", answer_san="exd6 e.p.",
        check=_uci("e5d6"),
    ),
    Lesson(
        id="promote",
        title="Promotion",
        subtitle="the pawn's reward",
        intro=("A pawn that reaches the far rank is promoted — it becomes a "
               "queen, rook, bishop, or knight of its colour. Almost always "
               "you want a queen."),
        fen="4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
        task="Push a7 to a8 and promote. Pick any piece — the queen is "
             "usually the strongest choice.",
        hint="Play the move, then pick a piece from the picker.",
        success="A new queen on a8 — most games end soon after a promotion.",
        answer_uci="a7a8q", answer_san="a8=Q+",
        check=_is_promotion,
    ),
    Lesson(
        id="check",
        title="Check",
        subtitle="attacking the king",
        intro=("Check is a direct attack on the king. You must escape it on "
               "the very next move — by moving the king, blocking the attack, "
               "or capturing the attacker."),
        fen="4k3/8/8/8/8/8/8/Q3K3 w - - 0 1",
        task="Give check to the black king on e8 with your queen.",
        hint="The a-file, the 8th rank, and the a4-e8 diagonal all reach him.",
        success=("Check! Your opponent now has to respond — you have the "
                 "initiative."),
        answer_uci="a1a8", answer_san="Qa8+",
        check=_is_check,
    ),
    Lesson(
        id="mate",
        title="Checkmate",
        subtitle="the game-ender",
        intro=("Checkmate is check the king cannot escape. The game ends "
               "immediately. The pattern below is the classic back-rank mate "
               "— the king is trapped by his own pawns."),
        fen="6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1",
        task="Deliver checkmate in one move.",
        hint="Slide the rook to the 8th rank — the king's own pawns block "
             "every escape.",
        success=("Back-rank mate! One of the most common finishes in chess — "
                 "watch for it in your own games."),
        answer_uci="a1a8", answer_san="Ra8#",
        check=_is_mate,
    ),
    Lesson(
        id="opening",
        title="Opening Principles",
        subtitle="how to start a game",
        intro=("Three rules cover most openings: (1) control the centre, "
               "(2) develop your minor pieces, (3) castle early to keep your "
               "king safe. Knights before bishops — they know where they "
               "belong sooner."),
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        task="Develop a knight. Nf3 is the most popular first move for White.",
        hint="From g1, the knight goes to f3 or h3. From b1, to c3 or a3. "
             "Choose f3.",
        success=("Nf3 develops a piece and eyes e5 — a perfect opening move."),
        answer_uci="g1f3", answer_san="Nf3",
        check=_any_piece(chess.KNIGHT),
    ),
    Lesson(
        id="fork",
        title="The Fork",
        subtitle="one move, two threats",
        intro=("A fork is a single move that attacks two enemy pieces at "
               "once. The opponent can only save one. Knights are the "
               "deadliest forkers — their L-shape reaches squares nothing "
               "else can match."),
        fen="k3q3/8/8/1N6/8/8/8/4K3 w - - 0 1",
        task="Fork the black king and queen with your knight.",
        hint="Find the square where your knight attacks a8 and e8 at once.",
        success="Nc7+ forks king and queen — the queen is lost.",
        answer_uci="b5c7", answer_san="Nc7+",
        check=_uci("b5c7"),
    ),
]