import pygame
import chess
import chess.engine
import os
import sys
from typing import Optional, Tuple, List
import time

# Initialize Pygame
pygame.init()

# Constants
WINDOW_SIZE = 1000  # Increased to accommodate move history
BOARD_SIZE = 600
SQUARE_SIZE = BOARD_SIZE // 8
MARGIN = 50
PIECE_SIZE = SQUARE_SIZE - 10
BOTTOM_PANEL_HEIGHT = 100
SIDE_PANEL_WIDTH = 300
TIMER_HEIGHT = 80

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
HIGHLIGHT = (247, 247, 105, 150)
MOVE_HIGHLIGHT = (106, 168, 79, 150)
BORDER_COLOR = (50, 50, 50)
PANEL_COLOR = (240, 240, 240)
TEXT_COLOR = (50, 50, 50)
POPUP_BG = (0, 0, 0, 180)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER = (100, 160, 210)

# Create window
screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
pygame.display.set_caption("AI Chess Game")

class ChessGame:
    def __init__(self):
        self.board = chess.Board()
        self.selected_square = None
        self.valid_moves = []
        self.last_move = None
        self.game_over = False
        self.ai_thinking = False
        self.move_history = []
        self.captured_pieces = {'w': [], 'b': []}
        self.selected_piece = None
        self.selected_piece_pos = None
        self.player_color = None
        self.white_time = 600  # 10 minutes
        self.black_time = 600
        self.last_time = time.time()
        self.game_started = False
        self.checkmate_popup = False
        self.winner = None
        
        # Load piece images
        self.piece_images = self.load_piece_images()
        self.engine = self.init_stockfish()

    def load_piece_images(self):
        pieces = {}
        for color in ['w', 'b']:
            for piece in ['p', 'r', 'n', 'b', 'q', 'k']:
                try:
                    image = pygame.image.load(f'pieces/{color}{piece}.png')
                    pieces[f'{color}{piece}'] = pygame.transform.smoothscale(image, (PIECE_SIZE, PIECE_SIZE))
                except:
                    print(f"Warning: Could not load image for {color}{piece}")
        return pieces

    def init_stockfish(self):
        print("\nSearching for Stockfish in these locations:")
        possible_paths = [
            os.path.join(os.getcwd(), 'stockfish', 'stockfish.exe'),
            os.path.join(os.getcwd(), 'stockfish.exe'),
            r'C:\Program Files (x86)\Stockfish\stockfish.exe'
        ]
        
        for path in possible_paths:
            print(f"- {path}")
            if os.path.exists(path):
                print(f"\nTrying to load Stockfish from: {path}")
                try:
                    engine = chess.engine.SimpleEngine.popen_uci(path)
                    print(f"Successfully loaded Stockfish from: {path}")
                    return engine
                except Exception as e:
                    print(f"Failed to load Stockfish from {path}: {str(e)}")
        
        print("\nStockfish not found. Please ensure Stockfish is installed and the path is correct.")
        return None

    def draw_color_selection(self):
        screen.fill(PANEL_COLOR)
        font = pygame.font.SysFont('Arial', 48)
        title = font.render("Choose Your Color", True, TEXT_COLOR)
        title_rect = title.get_rect(center=(WINDOW_SIZE//2, 200))
        screen.blit(title, title_rect)

        # White button
        white_rect = pygame.Rect(WINDOW_SIZE//4, 300, 200, 60)
        white_text = font.render("White", True, BLACK)
        white_text_rect = white_text.get_rect(center=white_rect.center)
        
        # Black button
        black_rect = pygame.Rect(WINDOW_SIZE*3//4 - 200, 300, 200, 60)
        black_text = font.render("Black", True, WHITE)
        black_text_rect = black_text.get_rect(center=black_rect.center)

        # Draw buttons with hover effect
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.rect(screen, BUTTON_HOVER if white_rect.collidepoint(mouse_pos) else BUTTON_COLOR, white_rect)
        pygame.draw.rect(screen, BUTTON_HOVER if black_rect.collidepoint(mouse_pos) else BUTTON_COLOR, black_rect)
        
        screen.blit(white_text, white_text_rect)
        screen.blit(black_text, black_text_rect)
        
        return white_rect, black_rect

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def update_timer(self):
        if not self.game_started or self.game_over:
            return
            
        current_time = time.time()
        elapsed = current_time - self.last_time
        
        if self.board.turn == chess.WHITE:
            self.white_time -= elapsed
        else:
            self.black_time -= elapsed
            
        self.last_time = current_time

        # Check for time out
        if self.white_time <= 0:
            self.game_over = True
            self.winner = "Black"
            self.checkmate_popup = True
        elif self.black_time <= 0:
            self.game_over = True
            self.winner = "White"
            self.checkmate_popup = True

    def draw_timers(self):
        font = pygame.font.SysFont('Arial', 36)
        white_time = self.format_time(max(0, self.white_time))
        black_time = self.format_time(max(0, self.black_time))
        
        # White timer
        white_text = font.render(f"White: {white_time}", True, TEXT_COLOR)
        screen.blit(white_text, (BOARD_SIZE + MARGIN + 20, 20))
        
        # Black timer
        black_text = font.render(f"Black: {black_time}", True, TEXT_COLOR)
        screen.blit(black_text, (BOARD_SIZE + MARGIN + 20, 70))

    def draw_move_history(self):
        history_surface = pygame.Surface((SIDE_PANEL_WIDTH - 40, WINDOW_SIZE - TIMER_HEIGHT - 40))
        history_surface.fill(WHITE)
        
        font = pygame.font.SysFont('Arial', 16)
        y_offset = 10
        
        # Draw column headers
        header_font = pygame.font.SysFont('Arial', 18, bold=True)
        white_header = header_font.render("White", True, TEXT_COLOR)
        black_header = header_font.render("Black", True, TEXT_COLOR)
        history_surface.blit(white_header, (10, y_offset))
        history_surface.blit(black_header, (SIDE_PANEL_WIDTH//2 + 10, y_offset))
        y_offset += 30
        
        # Draw moves in two columns
        for i in range(0, len(self.move_history), 2):
            move_number = i//2 + 1
            move_text = f"{move_number}. {self.move_history[i]}"
            text = font.render(move_text, True, BLACK)
            history_surface.blit(text, (10, y_offset))
            
            if i + 1 < len(self.move_history):
                move_text = f"{self.move_history[i+1]}"
                text = font.render(move_text, True, (70, 70, 70))
                history_surface.blit(text, (SIDE_PANEL_WIDTH//2 + 10, y_offset))
            
            y_offset += 25
            if y_offset + 25 > history_surface.get_height():
                break
            
        screen.blit(history_surface, (BOARD_SIZE + MARGIN + 20, TIMER_HEIGHT + 20))
        
        # Draw border
        pygame.draw.rect(screen, BORDER_COLOR, 
                        (BOARD_SIZE + MARGIN + 20, TIMER_HEIGHT + 20, 
                         SIDE_PANEL_WIDTH - 40, WINDOW_SIZE - TIMER_HEIGHT - 40), 1)
        
        # Draw vertical separator
        pygame.draw.line(screen, BORDER_COLOR,
                        (BOARD_SIZE + MARGIN + 20 + SIDE_PANEL_WIDTH//2, TIMER_HEIGHT + 20),
                        (BOARD_SIZE + MARGIN + 20 + SIDE_PANEL_WIDTH//2, WINDOW_SIZE - 20), 1)

    def draw_checkmate_popup(self):
        if not self.checkmate_popup:
            return
            
        # Create semi-transparent overlay
        overlay = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        overlay.fill(POPUP_BG)
        screen.blit(overlay, (0, 0))
        
        # Create popup at the bottom
        popup_width, popup_height = 400, 200
        popup_rect = pygame.Rect((WINDOW_SIZE - popup_width)//2, 
                               WINDOW_SIZE - popup_height - 50,  # Position at bottom
                               popup_width, popup_height)
        pygame.draw.rect(screen, PANEL_COLOR, popup_rect)
        pygame.draw.rect(screen, BORDER_COLOR, popup_rect, 2)
        
        # Draw text
        font = pygame.font.SysFont('Arial', 36)
        if self.winner:
            text = f"{self.winner} wins!"
        else:
            text = "Draw!"
            
        text_surface = font.render(text, True, TEXT_COLOR)
        text_rect = text_surface.get_rect(center=(WINDOW_SIZE//2, WINDOW_SIZE - popup_height - 20))
        screen.blit(text_surface, text_rect)
        
        # Draw button
        button_rect = pygame.Rect((WINDOW_SIZE - 200)//2, 
                                WINDOW_SIZE - 100,
                                200, 50)
        pygame.draw.rect(screen, BUTTON_COLOR, button_rect)
        
        button_text = font.render("New Game", True, WHITE)
        button_text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, button_text_rect)
        
        return button_rect

    def draw_board(self):
        screen.fill(PANEL_COLOR)
        
        # Draw board border
        pygame.draw.rect(screen, BORDER_COLOR, 
                        (MARGIN - 2, MARGIN - 2, 
                         BOARD_SIZE + 4, BOARD_SIZE + 4), 2)
        
        # Draw squares
        for rank in range(8):
            for file in range(8):
                color = LIGHT_SQUARE if (rank + file) % 2 == 0 else DARK_SQUARE
                rect = pygame.Rect(
                    MARGIN + file * SQUARE_SIZE,
                    MARGIN + rank * SQUARE_SIZE,
                    SQUARE_SIZE,
                    SQUARE_SIZE
                )
                pygame.draw.rect(screen, color, rect)
        
        # Draw coordinates
        font = pygame.font.SysFont('Arial', 16)
        for i in range(8):
            # Files (a-h)
            text = font.render(chr(97 + i), True, TEXT_COLOR)
            screen.blit(text, (MARGIN + i * SQUARE_SIZE + SQUARE_SIZE//2 - 5, 
                             MARGIN + BOARD_SIZE + 5))
            # Ranks (1-8)
            text = font.render(str(8 - i), True, TEXT_COLOR)
            screen.blit(text, (MARGIN - 20, MARGIN + i * SQUARE_SIZE + SQUARE_SIZE//2 - 8))
        
        # Draw player color indicator
        color_text = "White" if self.player_color else "Black"
        color_indicator = font.render(f"Playing as: {color_text}", True, TEXT_COLOR)
        screen.blit(color_indicator, (MARGIN, MARGIN + BOARD_SIZE + 30))

    def square_to_pixel(self, square: chess.Square) -> Tuple[int, int]:
        rank = chess.square_rank(square)
        file = chess.square_file(square)
        if self.player_color:  # If playing as white, flip the board
            rank = 7 - rank
        x = MARGIN + file * SQUARE_SIZE
        y = MARGIN + rank * SQUARE_SIZE
        return (x, y)

    def pixel_to_square(self, pos: Tuple[int, int]) -> Optional[chess.Square]:
        x, y = pos
        if not (MARGIN <= x < MARGIN + BOARD_SIZE and MARGIN <= y < MARGIN + BOARD_SIZE):
            return None
        
        file = (x - MARGIN) // SQUARE_SIZE
        rank = (y - MARGIN) // SQUARE_SIZE
        
        if self.player_color:  # If playing as white, flip the coordinates
            rank = 7 - rank
            
        if 0 <= file < 8 and 0 <= rank < 8:
            return chess.square(file, rank)
        return None

    def draw_pieces(self):
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece and (square != self.selected_square or not self.selected_piece):
                piece_symbol = piece.symbol().lower()
                color = 'w' if piece.color == chess.WHITE else 'b'
                image = self.piece_images.get(f'{color}{piece_symbol}')
                if image:
                    x, y = self.square_to_pixel(square)
                    screen.blit(image, (x + 5, y + 5))

    def draw_highlights(self):
        if self.selected_square is not None:
            x, y = self.square_to_pixel(self.selected_square)
            highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            highlight_surface.fill(HIGHLIGHT)
            screen.blit(highlight_surface, (x, y))
            
            for move in self.valid_moves:
                if move.from_square == self.selected_square:
                    x, y = self.square_to_pixel(move.to_square)
                    highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                    highlight_surface.fill(MOVE_HIGHLIGHT)
                    screen.blit(highlight_surface, (x, y))
        
        if self.last_move:
            for square in [self.last_move.from_square, self.last_move.to_square]:
                x, y = self.square_to_pixel(square)
                highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                highlight_surface.fill(MOVE_HIGHLIGHT)
                screen.blit(highlight_surface, (x, y))

    def draw_selected_piece(self):
        if self.selected_piece and self.selected_piece_pos:
            mouse_x, mouse_y = self.selected_piece_pos
            piece_image = self.piece_images.get(self.selected_piece)
            if piece_image:
                screen.blit(piece_image, (mouse_x - PIECE_SIZE//2, mouse_y - PIECE_SIZE//2))

    def get_ai_move(self):
        if not self.engine:
            return None
        
        try:
            result = self.engine.play(self.board, chess.engine.Limit(time=1.0))
            return result.move
        except Exception as e:
            print(f"Error getting AI move: {str(e)}")
            return None

    def reset_game(self):
        self.board = chess.Board()
        self.selected_square = None
        self.valid_moves = []
        self.last_move = None
        self.game_over = False
        self.ai_thinking = False
        self.move_history = []
        self.captured_pieces = {'w': [], 'b': []}
        self.selected_piece = None
        self.selected_piece_pos = None
        self.player_color = None
        self.white_time = 600  # 10 minutes
        self.black_time = 600
        self.last_time = time.time()
        self.game_started = False
        self.checkmate_popup = False
        self.winner = None
        
        # Load piece images
        self.piece_images = self.load_piece_images()
        self.engine = self.init_stockfish()

    def run(self):
        clock = pygame.time.Clock()
        running = True
        color_selection = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif color_selection:
                    white_rect, black_rect = self.draw_color_selection()
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = event.pos
                        if white_rect.collidepoint(mouse_pos):
                            self.player_color = True
                            color_selection = False
                            self.game_started = True
                        elif black_rect.collidepoint(mouse_pos):
                            self.player_color = False
                            color_selection = False
                            self.game_started = True
                            # Add delay before AI makes first move
                            pygame.time.delay(1000)  # 1 second delay
                            # AI makes first move as White
                            ai_move = self.get_ai_move()
                            if ai_move and ai_move in self.board.legal_moves:
                                # Get SAN before pushing the move
                                move_san = self.board.san(ai_move)
                                self.board.push(ai_move)
                                self.move_history.append(move_san)
                                self.last_move = ai_move
                    pygame.display.flip()
                    continue
                
                elif event.type == pygame.MOUSEBUTTONDOWN and not self.game_over and not self.ai_thinking:
                    if event.button == 1:  # Left click
                        if self.checkmate_popup:
                            button_rect = self.draw_checkmate_popup()
                            if button_rect and button_rect.collidepoint(event.pos):
                                # Reset game
                                self.reset_game()
                                color_selection = True
                                continue
                        else:
                            pos = pygame.mouse.get_pos()
                            square = self.pixel_to_square(pos)
                            
                            if square is not None:
                                piece = self.board.piece_at(square)
                                if piece and piece.color == self.board.turn and \
                                   ((self.player_color and piece.color == chess.WHITE) or \
                                    (not self.player_color and piece.color == chess.BLACK)):
                                    self.selected_square = square
                                    self.valid_moves = [move for move in self.board.legal_moves 
                                                      if move.from_square == square]
                                    self.selected_piece = f"{'w' if piece.color == chess.WHITE else 'b'}{piece.symbol().lower()}"
                                    self.selected_piece_pos = pos
                
                elif event.type == pygame.MOUSEBUTTONUP and not self.game_over and not self.ai_thinking:
                    if event.button == 1 and self.selected_square is not None:
                        pos = pygame.mouse.get_pos()
                        target_square = self.pixel_to_square(pos)
                        
                        if target_square is not None:
                            move = chess.Move(self.selected_square, target_square)
                            if move in self.valid_moves:
                                # Get SAN before pushing the move
                                move_san = self.board.san(move)
                                
                                # Check if a piece was captured
                                captured_piece = self.board.piece_at(target_square)
                                if captured_piece:
                                    color = 'w' if captured_piece.color == chess.WHITE else 'b'
                                    self.captured_pieces[color].append(captured_piece.symbol().upper())
                                
                                self.board.push(move)
                                self.move_history.append(move_san)
                                self.last_move = move
                                
                                if self.board.is_game_over():
                                    self.game_over = True
                                    if self.board.is_checkmate():
                                        self.winner = "White" if not self.board.turn else "Black"
                                    self.checkmate_popup = True
                                else:
                                    self.ai_thinking = True
                        
                        self.selected_square = None
                        self.valid_moves = []
                        self.selected_piece = None
                        self.selected_piece_pos = None
                
                elif event.type == pygame.MOUSEMOTION and self.selected_piece:
                    self.selected_piece_pos = event.pos
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:  # Reset game
                        self.reset_game()
                        color_selection = True
                    elif event.key == pygame.K_u and len(self.move_history) >= 2:  # Undo move
                        self.board.pop()  # Undo AI move
                        self.board.pop()  # Undo player move
                        self.move_history.pop()
                        self.move_history.pop()
                        self.game_over = False
                        self.checkmate_popup = False
                        self.ai_thinking = False
                        self.selected_square = None
                        self.valid_moves = []
                        self.selected_piece = None
                        self.selected_piece_pos = None
            
            if not color_selection:
                # AI move
                if self.ai_thinking and not self.game_over:
                    ai_move = self.get_ai_move()
                    if ai_move and ai_move in self.board.legal_moves:
                        # Get SAN before pushing the move
                        move_san = self.board.san(ai_move)
                        
                        # Check if a piece was captured
                        captured_piece = self.board.piece_at(ai_move.to_square)
                        if captured_piece:
                            color = 'w' if captured_piece.color == chess.WHITE else 'b'
                            self.captured_pieces[color].append(captured_piece.symbol().upper())
                        
                        self.board.push(ai_move)
                        self.move_history.append(move_san)
                        self.last_move = ai_move
                        
                        if self.board.is_game_over():
                            self.game_over = True
                            if self.board.is_checkmate():
                                self.winner = "White" if not self.board.turn else "Black"
                            self.checkmate_popup = True
                    self.ai_thinking = False
                
                # Update timer
                self.update_timer()
                
                # Draw everything
                self.draw_board()
                self.draw_highlights()
                self.draw_pieces()
                self.draw_selected_piece()
                self.draw_timers()
                self.draw_move_history()
                
                if self.checkmate_popup:
                    self.draw_checkmate_popup()
            
            pygame.display.flip()
            clock.tick(60)
        
        if self.engine:
            self.engine.quit()
        pygame.quit()

if __name__ == "__main__":
    game = ChessGame()
    game.run() 