import chess
import tkinter as tk
from tkinter import messagebox
from chess_ai import get_ai_move

SQUARE_SIZE = 64
LIGHT = "#EEEED2"
DARK = "#769656"
HIGHLIGHT = "#F6F669"

UNICODE_PIECES = {
    "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}


class ChessGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Play vs CNN Chess Model")

        self.board = chess.Board()
        self.selected_square = None

        self.canvas = tk.Canvas(
            root, width=SQUARE_SIZE*8, height=SQUARE_SIZE*8)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)

        self.status_label = tk.Label(
            root, text="Your move (White)", font=("Arial", 12))
        self.status_label.pack(pady=5)

        self.draw_board()

    def draw_board(self):
        self.canvas.delete("all")
        for rank in range(8):
            for file in range(8):
                x1 = file * SQUARE_SIZE
                y1 = rank * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE

                square = chess.square(file, 7 - rank)
                color = LIGHT if (rank + file) % 2 == 0 else DARK
                if square == self.selected_square:
                    color = HIGHLIGHT

                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=color, outline="")

                piece = self.board.piece_at(square)
                if piece:
                    symbol = UNICODE_PIECES[piece.symbol()]
                    self.canvas.create_text(
                        x1 + SQUARE_SIZE/2, y1 + SQUARE_SIZE/2,
                        text=symbol, font=("Arial", 32)
                    )

    def on_click(self, event):
        if self.board.turn != chess.WHITE or self.board.is_game_over():
            return

        file = event.x // SQUARE_SIZE
        rank = 7 - (event.y // SQUARE_SIZE)
        square = chess.square(file, rank)

        if self.selected_square is None:
            piece = self.board.piece_at(square)
            if piece and piece.color == chess.WHITE:
                self.selected_square = square
                self.draw_board()
        else:
            move = chess.Move(self.selected_square, square)

            piece = self.board.piece_at(self.selected_square)
            if piece and piece.piece_type == chess.PAWN and chess.square_rank(square) == 7:
                move = chess.Move(self.selected_square,
                                  square, promotion=chess.QUEEN)

            if move in self.board.legal_moves:
                self.board.push(move)
                self.selected_square = None
                self.draw_board()
                self.check_game_over()
                if not self.board.is_game_over():
                    self.root.after(300, self.ai_move)
            else:
                self.selected_square = None
                self.draw_board()

    def ai_move(self):
        self.status_label.config(text="Model is thinking...")
        self.root.update()

        move = get_ai_move(self.board)
        self.board.push(move)
        self.draw_board()
        self.check_game_over()

        if not self.board.is_game_over():
            self.status_label.config(text="Your move (White)")

    def check_game_over(self):
        if self.board.is_checkmate():
            winner = "Black (Model)" if self.board.turn == chess.WHITE else "White (You)"
            messagebox.showinfo("Game Over", f"Checkmate! {winner} wins.")
        elif self.board.is_stalemate():
            messagebox.showinfo("Game Over", "Stalemate — draw.")
        elif self.board.is_insufficient_material():
            messagebox.showinfo("Game Over", "Draw — insufficient material.")


if __name__ == "__main__":
    root = tk.Tk()
    app = ChessGUI(root)
    root.mainloop()
