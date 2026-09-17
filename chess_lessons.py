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


def _is_double_check(move, before, after):
    return after.is_check() and len(after.checkers()) >= 2


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
        answer_uci="e5d6", answer_san="exd6",
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
        fen="k3q3/8/8/3N4/8/8/8/7K w - - 0 1",
        task="Fork the black king and queen with your knight.",
        hint="Find the square where your knight attacks a8 and e8 at once.",
        success="Nc7+ forks king and queen — the queen is lost.",
        answer_uci="d5c7", answer_san="Nc7+",
        check=_uci("d5c7"),
    ),
    # ========== 20 NEW LESSONS ==========
    Lesson(
        id="capture_pawn",
        title="Pawn Captures",
        subtitle="diagonal only",
        intro=("Pawns capture one square diagonally forward. They never capture "
               "straight ahead. This is the only way a pawn changes file."),
        fen="4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1",
        task="Capture the black pawn on d5 with your e4 pawn.",
        hint="Move the e4 pawn diagonally to d5.",
        success="Pawns capture diagonally — remember that rule forever.",
        answer_uci="e4d5", answer_san="exd5",
        check=_uci("e4d5"),
    ),
    Lesson(
        id="capture_knight",
        title="Knight Captures",
        subtitle="jump and take",
        intro=("Knights capture the same way they move: any L-shaped landing "
               "square that holds an enemy piece. They jump over everything."),
        fen="4k3/8/8/3p4/8/2N5/8/4K3 w - - 0 1",
        task="Capture the black pawn on d5 with your knight.",
        hint="From c3 the knight can jump to d5, a4, b5, e4, e2, a2, b1 or d1.",
        success="The knight jumps over pieces and captures on the landing square.",
        answer_uci="c3d5", answer_san="Nxd5",
        check=_uci("c3d5"),
    ),
    Lesson(
        id="pin",
        title="The Pin",
        subtitle="frozen in place",
        intro=("A pin happens when a piece cannot move without exposing a more "
               "valuable piece behind it. Absolute pins against the king are "
               "especially powerful."),
        fen="4k3/8/8/8/4n3/8/8/3QK3 w - - 0 1",
        task="Pin the black knight to its king with your queen.",
        hint="Bring the queen to the e-file: d1 to e2 aims at the knight, "
             "with the black king behind it.",
        success="The knight is pinned — moving it would put the king in check.",
        answer_uci="d1e2", answer_san="Qe2",
        check=_uci("d1e2"),
    ),
    Lesson(
        id="skewer",
        title="The Skewer",
        subtitle="the reverse pin",
        intro=("A skewer attacks a valuable piece so that when it moves away, "
               "a less valuable piece behind it is captured. It is the opposite "
               "of a pin."),
        fen="8/8/8/4k2q/8/8/8/R3K3 w - - 0 1",
        task="Skewer the black king and queen with your rook.",
        hint="Check the king along the 5th rank — when it steps aside, the "
             "queen behind it falls.",
        success="Ra5+ is a skewer: the king must move, then the queen drops.",
        answer_uci="a1a5", answer_san="Ra5+",
        check=_uci("a1a5"),
    ),
    Lesson(
        id="discovered_check",
        title="Discovered Check",
        subtitle="the hidden battery",
        intro=("A discovered check occurs when you move one piece and thereby "
               "uncover an attack from another piece behind it. The opponent "
               "must deal with the check."),
        fen="4k3/3N4/2B5/8/8/8/8/4K3 w - - 0 1",
        task="Move the knight to give a discovered check with the bishop.",
        hint="The knight stands between the bishop on c6 and the black king — "
             "any knight move opens the c6–e8 diagonal.",
        success="The knight moved and the bishop now checks the king — a classic discovery.",
        answer_uci="d7e5", answer_san="Ne5+",
        check=_is_check,
    ),
    Lesson(
        id="double_check",
        title="Double Check",
        subtitle="two attackers at once",
        intro=("Double check is a discovered check where the moving piece also "
               "gives check. The king must move — nothing else can stop two "
               "checks at the same time."),
        fen="4k3/3N4/2B5/8/8/8/8/4K3 w - - 0 1",
        task="Give double check: move the knight so both it and the bishop "
             "attack the king.",
        hint="Find the knight square that itself checks e8 while clearing the "
             "bishop's diagonal — f6 works.",
        success="Double check! The king has no choice but to move.",
        answer_uci="d7f6", answer_san="Nf6+",
        check=_is_double_check,
    ),
    Lesson(
        id="castle_queenside",
        title="Queenside Castling",
        subtitle="the long castle",
        intro=("You can also castle queenside (O-O-O). The king moves two squares "
               "toward the a-file rook and the rook jumps over. More space is "
               "needed between them."),
        fen="r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
        task="Castle queenside (long castle).",
        hint="Move the king from e1 to c1.",
        success="O-O-O! The king is safer and the rook is activated on the d-file.",
        answer_uci="e1c1", answer_san="O-O-O",
        check=_uci("e1c1"),
    ),
    Lesson(
        id="center_control",
        title="Control the Centre",
        subtitle="e4 and d4",
        intro=("Controlling the centre (e4, d4, e5, d5) gives your pieces more "
               "space and options. Pawns on e4 and d4 are the classic way to "
               "claim the middle of the board."),
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        task="Occupy the centre with a pawn — play e4.",
        hint="Push the e-pawn two squares.",
        success="e4 claims space and opens lines for the queen and bishop.",
        answer_uci="e2e4", answer_san="e4",
        check=_uci("e2e4"),
    ),
    Lesson(
        id="develop_bishop",
        title="Develop the Bishop",
        subtitle="out of the starting square",
        intro=("Developing means moving a piece from its starting square to an "
               "active one. Bishops like long diagonals. Get them out early."),
        fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1",
        task="Develop the light-squared bishop to c4 or b5.",
        hint="The bishop on f1 can go to c4 (Italian) or b5 (Ruy Lopez style).",
        success="The bishop is developed and eyes the black kingside.",
        answer_uci="f1c4", answer_san="Bc4",
        check=_uci("f1c4", "f1b5"),
    ),
    Lesson(
        id="simple_trade",
        title="Trading Pieces",
        subtitle="equal exchange",
        intro=("Trading means exchanging pieces of similar value. Sometimes you "
               "want to simplify the position; sometimes you avoid trades to "
               "keep attacking chances."),
        fen="4k3/8/8/3n4/8/4N3/8/4K3 w - - 0 1",
        task="Trade your knight for the black knight.",
        hint="Capture on d5.",
        success="Equal trade. The position is simplified.",
        answer_uci="e3d5", answer_san="Nxd5",
        check=_uci("e3d5"),
    ),
    Lesson(
        id="defend_piece",
        title="Defending a Piece",
        subtitle="protect what is attacked",
        intro=("When an opponent attacks one of your pieces, you can capture the "
               "attacker, move the piece away, or defend it so the capture "
               "becomes an equal trade."),
        fen="4k3/8/8/3n4/8/4P3/8/4K3 w - - 0 1",
        task="Defend your pawn so that if the knight takes it, you can recapture.",
        hint="Move the king closer or bring another piece to protect e3.",
        success="Now the pawn is protected — the knight capture is no longer free.",
        answer_uci="e1e2", answer_san="Ke2",
        check=_uci("e1e2", "e1d2", "e1f2"),
    ),
    Lesson(
        id="discovered_attack",
        title="Discovered Attack",
        subtitle="uncovering a threat",
        intro=("Similar to discovered check, but the uncovered piece attacks a "
               "non-king target. The moving piece can create a second threat."),
        fen="4k3/8/8/3q4/2N5/1B6/8/4K3 w - - 0 1",
        task="Move the knight to uncover the bishop's attack on the black queen.",
        hint="The knight blocks the b3–d5 diagonal — any knight move opens it.",
        success="The bishop now attacks the queen — a discovered attack.",
        answer_uci="c4e5", answer_san="Ne5",
        check=_any_piece(chess.KNIGHT),
    ),
    Lesson(
        id="opposition",
        title="King Opposition",
        subtitle="face to face",
        intro=("Opposition is when two kings face each other with one square "
               "between them. The side that does not have to move has the "
               "opposition and can restrict the other king."),
        fen="4k3/8/8/8/8/8/8/4K3 w - - 0 1",
        task="Take the opposition: step your king forward to face the "
             "black king.",
        hint="Move the king from e1 to e2 — the two kings now stand on the "
             "same file.",
        success="You have the opposition — a key idea in king-and-pawn endings.",
        answer_uci="e1e2", answer_san="Ke2",
        check=_uci("e1e2"),
    ),
    Lesson(
        id="rook_lift",
        title="Rook Lift",
        subtitle="up and over",
        intro=("A rook lift is when a rook moves up a file and then swings across "
               "a rank to join an attack, often on the kingside."),
        fen="4k3/8/8/8/8/8/8/R3K3 w - - 0 1",
        task="Lift the rook up the a-file (or any open path).",
        hint="Move the rook to a3, a4 or further up.",
        success="Rooks can swing across the board once they reach an open rank.",
        answer_uci="a1a3", answer_san="Ra3",
        check=_any_piece(chess.ROOK),
    ),
    Lesson(
        id="knight_outpost",
        title="Knight Outpost",
        subtitle="a permanent home",
        intro=("An outpost is a square protected by a pawn where an enemy pawn "
               "cannot chase the piece away. Knights love outposts in the "
               "centre or near the enemy king."),
        fen="4k3/8/8/3N4/8/8/8/4K3 w - - 0 1",
        task="Keep the knight on its strong central square or improve it.",
        hint="The knight is already well placed — any safe move maintains activity.",
        success="Central knights are powerful — they control many key squares.",
        answer_uci="d5c7", answer_san="Nc7+",
        check=_any_piece(chess.KNIGHT),
    ),
    Lesson(
        id="smothered_mate",
        title="Smothered Mate Pattern",
        subtitle="the king has no air",
        intro=("Smothered mate occurs when a knight checks a king that is "
               "completely blocked by its own pieces and has no escape square."),
        fen="6rk/6pp/8/6N1/8/8/8/4K3 w - - 0 1",
        task="Deliver smothered mate in one move with your knight.",
        hint="Jump to f7 — the black king is boxed in by its own rook and pawns.",
        success="Smothered mate! The king's own army blocked every escape square.",
        answer_uci="g5f7", answer_san="Nf7#",
        check=_is_mate,
    ),
    Lesson(
        id="back_rank_threat",
        title="Back-Rank Threat",
        subtitle="the silent danger",
        intro=("Even when you cannot deliver mate yet, threatening the back rank "
               "forces the opponent to create luft (an escape square) or defend."),
        fen="6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1",
        task="Attack the back rank with your rook.",
        hint="Slide the rook to the 8th rank — the king's own pawns block "
             "every escape.",
        success=("Back-rank mate! One of the most common finishes in chess — "
                 "watch for it in your own games."),
        answer_uci="a1a8", answer_san="Ra8#",
        check=_is_check,
    ),
    Lesson(
        id="pawn_break",
        title="Pawn Break",
        subtitle="opening the position",
        intro=("A pawn break is a pawn move that challenges the opponent's pawn "
               "structure and opens lines for your pieces."),
        fen="4k3/3p4/8/3P4/8/8/8/4K3 w - - 0 1",
        task="Challenge the black pawn structure or advance your own pawn.",
        hint="You can capture or push further depending on the goal.",
        success="Pawn breaks change the character of the position.",
        answer_uci="d5d6", answer_san="d6",
        check=_any_piece(chess.PAWN),
    ),
    Lesson(
        id="king_activity",
        title="Active King",
        subtitle="the endgame hero",
        intro=("In the endgame the king becomes a strong attacking piece. Bring "
               "it toward the centre or toward enemy pawns."),
        fen="4k3/8/8/8/8/8/8/4K3 w - - 0 1",
        task="Activate your king by stepping it toward the centre.",
        hint="Step to e2, d2 or f2 — every step toward the middle is progress.",
        success="An active king often decides the endgame.",
        answer_uci="e1e2", answer_san="Ke2",
        check=_uci("e1e2", "e1d2", "e1f2"),
    ),
    Lesson(
        id="queen_mate",
        title="Queen Checkmate",
        subtitle="the most common mate",
        intro=("The queen is the most powerful mating piece. With help from "
               "another piece or by restricting the king, she delivers mate "
               "on many patterns."),
        fen="7k/8/6K1/8/8/8/8/1Q6 w - - 0 1",
        task="Checkmate the black king with your queen.",
        hint="Bring the queen to the 8th rank — your king on g6 covers every "
             "escape square.",
        success="Queen + king is a basic and powerful mating force.",
        answer_uci="b1b8", answer_san="Qb8#",
        check=_is_mate,
    ),
]
