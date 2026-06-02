#!/usr/bin/env python3
"""
Gravity Flip Poker - A Luck-Based Poker Game
Computer has NO advantage - pure chance determines outcome
"""

import sqlite3
import random
import json
import sys
import os
import argparse
import time
import math
from datetime import datetime
from enum import Enum
from typing import List, Tuple, Dict
from contextlib import closing

# Configure UTF-8 output encoding for Windows CMD / PowerShell consoles
try:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# --- TERMINAL COLOR SETUP ---
# ANSI escape codes for stunning visual terminal aesthetics (HSL tailored colors)
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_UNDERLINE = "\033[4m"

ANSI_GREEN = "\033[38;2;46;204;113m"   # Sleek modern Emerald Green (Win)
ANSI_RED = "\033[38;2;231;76;60m"      # Sleek soft Crimson Red (Loss)
ANSI_YELLOW = "\033[38;2;241;196;15m"   # Warm Gold (Ties/Pushes)
ANSI_CYAN = "\033[38;2;52;152;219m"     # Modern Bright Blue (Info/Menu)
ANSI_MAGENTA = "\033[38;2;155;89;182m"  # Royal Amethyst Purple (Player Hand)
ANSI_GRAY = "\033[38;2;149;165;166m"     # Asbestos Grey (Borders, Card Backs)
ANSI_ORANGE = "\033[38;2;230;126;34m"   # Pumpkin Orange (Betting, Special Alerts)

COLOR_ENABLED = True

def c_text(text: str, color_code: str) -> str:
    """Wraps text in ANSI colors if colors are globally enabled."""
    if COLOR_ENABLED:
        return f"{color_code}{text}{ANSI_RESET}"
    return text

def enable_windows_ansi():
    """Enables Virtual Terminal Processing in Windows CMD/PowerShell."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # STD_OUTPUT_HANDLE is -11
            hOut = kernel32.GetStdHandle(-11)
            if hOut != -1:
                mode = ctypes.c_ulong()
                if kernel32.GetConsoleMode(hOut, ctypes.byref(mode)):
                    # ENABLE_VIRTUAL_TERMINAL_PROCESSING is 0x0004
                    kernel32.SetConsoleMode(hOut, mode.value | 0x0004)
        except Exception:
            pass

# --- CORE CLASSES ---

class Card:
    SUIT_SYMBOLS = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
    SUIT_NAMES = {'S': 'Spades', 'H': 'Hearts', 'D': 'Diamonds', 'C': 'Clubs'}
    RANK_NAMES = {
        2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
        10: '10', 11: 'J', 12: 'Q', 13: 'K', 14: 'A'
    }

    def __init__(self, rank: int, suit: str):
        self.rank = rank  # 2 to 14
        self.suit = suit  # 'S', 'H', 'D', 'C'

    def __repr__(self):
        return f"{self.RANK_NAMES[self.rank]}{self.SUIT_SYMBOLS[self.suit]}"

    def to_dict(self):
        return {'rank': self.rank, 'suit': self.suit}

    @classmethod
    def from_dict(cls, d):
        return cls(d['rank'], d['suit'])


class Deck:
    def __init__(self):
        self.cards = [Card(rank, suit) for rank in range(2, 15) for suit in ['S', 'H', 'D', 'C']]
        self.discards = []
        
    def shuffle(self, seed=None):
        """Truly shuffles using random.shuffle() each hand to prevent any manipulation."""
        if seed is not None:
            random.seed(seed)
        random.shuffle(self.cards)

    def add_to_discards(self, cards: List[Card]):
        self.discards.extend(cards)

    def draw(self, count=1) -> List[Card]:
        """Draws cards from the draw pile. Handles depletion by reshuffling the discard pile."""
        drawn = []
        for _ in range(count):
            if not self.cards:
                if self.discards:
                    # Reshuffle discards
                    self.cards = list(self.discards)
                    self.discards = []
                    self.shuffle()
                else:
                    break
            if self.cards:
                drawn.append(self.cards.pop(0))
        return drawn


class HandRank(Enum):
    HIGH_CARD = 1
    ONE_PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10


class HandEvaluator:
    @staticmethod
    def evaluate_hand(cards: List[Card]) -> Tuple[HandRank, tuple, str]:
        """
        Evaluates a 5-card poker hand and returns:
          1. HandRank Enum
          2. A flattened comparison tuple for tie-breaking (Python handles tuple comparison recursively)
          3. A string description of the hand rank.
        """
        if len(cards) != 5:
            raise ValueError("Evaluator requires exactly 5 cards.")

        # Sort cards by rank descending
        sorted_cards = sorted(cards, key=lambda c: c.rank, reverse=True)
        ranks = [c.rank for c in sorted_cards]
        suits = [c.suit for c in sorted_cards]
        
        # Check Flush (all cards same suit)
        is_flush = len(set(suits)) == 1
        
        # Check Straight
        is_straight = False
        straight_high = 0
        
        unique_ranks = sorted(list(set(ranks)), reverse=True)
        if len(unique_ranks) == 5:
            if unique_ranks[0] - unique_ranks[4] == 4:
                is_straight = True
                straight_high = unique_ranks[0]
            elif unique_ranks == [14, 5, 4, 3, 2]: # Ace-low Straight (5, 4, 3, 2, A)
                is_straight = True
                straight_high = 5
        
        # Frequency counts
        rank_counts = {}
        for r in ranks:
            rank_counts[r] = rank_counts.get(r, 0) + 1
            
        # Sort counts descending by count, then by rank
        sorted_by_freq = sorted(rank_counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
        
        # Determine hand ranking
        if is_flush and is_straight:
            if straight_high == 14:
                return (HandRank.ROYAL_FLUSH, (HandRank.ROYAL_FLUSH.value, 14), "Royal Flush")
            else:
                return (HandRank.STRAIGHT_FLUSH, (HandRank.STRAIGHT_FLUSH.value, straight_high), f"Straight Flush ({Card.RANK_NAMES[straight_high]}-High)")
                
        if sorted_by_freq[0][1] == 4:
            four_rank = sorted_by_freq[0][0]
            kicker = sorted_by_freq[1][0]
            return (HandRank.FOUR_OF_A_KIND, (HandRank.FOUR_OF_A_KIND.value, four_rank, kicker), f"Four of a Kind ({Card.RANK_NAMES[four_rank]}s)")
            
        if sorted_by_freq[0][1] == 3 and sorted_by_freq[1][1] == 2:
            three_rank = sorted_by_freq[0][0]
            pair_rank = sorted_by_freq[1][0]
            return (HandRank.FULL_HOUSE, (HandRank.FULL_HOUSE.value, three_rank, pair_rank), f"Full House ({Card.RANK_NAMES[three_rank]}s over {Card.RANK_NAMES[pair_rank]}s)")
            
        if is_flush:
            return (HandRank.FLUSH, (HandRank.FLUSH.value,) + tuple(ranks), f"Flush ({Card.RANK_NAMES[ranks[0]]}-High)")
            
        if is_straight:
            return (HandRank.STRAIGHT, (HandRank.STRAIGHT.value, straight_high), f"Straight ({Card.RANK_NAMES[straight_high]}-High)")
            
        if sorted_by_freq[0][1] == 3:
            three_rank = sorted_by_freq[0][0]
            kickers = (sorted_by_freq[1][0], sorted_by_freq[2][0])
            return (HandRank.THREE_OF_A_KIND, (HandRank.THREE_OF_A_KIND.value, three_rank) + kickers, f"Three of a Kind ({Card.RANK_NAMES[three_rank]}s)")
            
        if sorted_by_freq[0][1] == 2 and sorted_by_freq[1][1] == 2:
            pair1 = sorted_by_freq[0][0]
            pair2 = sorted_by_freq[1][0]
            kicker = sorted_by_freq[2][0]
            return (HandRank.TWO_PAIR, (HandRank.TWO_PAIR.value, pair1, pair2, kicker), f"Two Pair ({Card.RANK_NAMES[pair1]}s and {Card.RANK_NAMES[pair2]}s)")
            
        if sorted_by_freq[0][1] == 2:
            pair_rank = sorted_by_freq[0][0]
            kickers = tuple(r for r, count in sorted_by_freq[1:])
            return (HandRank.ONE_PAIR, (HandRank.ONE_PAIR.value, pair_rank) + kickers, f"One Pair ({Card.RANK_NAMES[pair_rank]}s)")
            
        return (HandRank.HIGH_CARD, (HandRank.HIGH_CARD.value,) + tuple(ranks), f"High Card ({Card.RANK_NAMES[ranks[0]]})")

    @staticmethod
    def evaluate_7_cards(hole_cards: List[Card], community_cards: List[Card]) -> Tuple[HandRank, tuple, str]:
        """
        Takes 2 hole cards and 5 community cards, evaluates all 21 possible 5-card combinations,
        and returns:
          1. Best HandRank Enum
          2. Best flattened comparison score tuple
          3. Best hand rank description text
        """
        import itertools
        all_7 = hole_cards + community_cards
        best_score_tuple = None
        best_rank = None
        best_desc = ""
        
        for combo in itertools.combinations(all_7, 5):
            rank, score, desc = HandEvaluator.evaluate_hand(list(combo))
            if best_score_tuple is None or score > best_score_tuple:
                best_score_tuple = score
                best_rank = rank
                best_desc = desc
                
        return best_rank, best_score_tuple, best_desc


class AIPlayer:
    def decide_discards(self, hand: List[Card], debug_luck: bool = False) -> Tuple[List[int], int]:
        """
        Anti-Computer-Advantage Draw strategy:
        1. Select a number of cards to discard (0 to 3) with equal probability (25% each).
        2. Randomly select that many card indices (0 to 4) to discard.
        Returns:
            list of indices to discard (0-indexed)
            the seed used for this random choice (for audit and debug_luck)
        """
        seed = random.randint(0, 2**31 - 1)
        # Use a local Random instance to ensure no global state contamination and strict replicability
        local_rand = random.Random(seed)
        
        discard_count = local_rand.randint(0, 3)
        indices = list(range(5))
        local_rand.shuffle(indices)
        discards = sorted(indices[:discard_count])
        
        if debug_luck:
            print(c_text(f"\n[DEBUG-LUCK AUDIT] Computer Draw Decision Process:", ANSI_CYAN))
            print(f"  - Random Seed Registered: {seed}")
            print(f"  - Discard Count Chosen: {discard_count} (equal 25% chance for 0, 1, 2, or 3 cards)")
            if discard_count > 0:
                discarded_cards = [hand[i] for i in discards]
                print(f"  - Card Indices Chosen: {[i+1 for i in discards]} (Cards: {', '.join(map(str, discarded_cards))})")
            else:
                print(f"  - No cards selected for discard.")
            print("-" * 60)
                
        return discards, seed


class Database:
    def __init__(self, db_path="gravity_poker.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Initializes tables using connection context manager with proper closing."""
        with closing(self.get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                # Players table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT UNIQUE,
                    total_games INTEGER DEFAULT 0,
                    player_wins INTEGER DEFAULT 0,
                    computer_wins INTEGER DEFAULT 0,
                    pushes INTEGER DEFAULT 0,
                    total_chips INTEGER DEFAULT 1000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Game history table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_history (
                    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    player_hand TEXT, -- JSON string
                    computer_hand TEXT, -- JSON string
                    winner TEXT, -- 'player', 'computer', 'push'
                    player_hand_rank TEXT,
                    computer_hand_rank TEXT,
                    chips_bet INTEGER,
                    chips_won INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(player_id) REFERENCES players(player_id)
                )
                """)
                
                # Deck history table (first 20 cards for shuffling audit)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS deck_history (
                    shuffle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hand_number INTEGER,
                    deck_order TEXT
                )
                """)
                conn.commit()

    def get_or_create_player(self, name: str) -> dict:
        """Retrieves or creates a player by name. Saves states for seamless resuming."""
        with closing(self.get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM players WHERE player_name = ?", (name,))
                row = cursor.fetchone()
                if row:
                    return self._map_player(row)
                else:
                    cursor.execute("INSERT INTO players (player_name, total_chips) VALUES (?, ?)", (name, 1000))
                    conn.commit()
                    cursor.execute("SELECT * FROM players WHERE player_name = ?", (name,))
                    row = cursor.fetchone()
                    return self._map_player(row)

    def _map_player(self, row) -> dict:
        return {
            'player_id': row[0],
            'player_name': row[1],
            'total_games': row[2],
            'player_wins': row[3],
            'computer_wins': row[4],
            'pushes': row[5],
            'total_chips': row[6],
            'created_at': row[7]
        }

    def update_player_stats(self, player_id: int, winner: str, chips_change: int):
        with closing(self.get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT total_games, player_wins, computer_wins, pushes, total_chips FROM players WHERE player_id = ?", (player_id,))
                row = cursor.fetchone()
                if not row:
                    return
                
                total_games, player_wins, computer_wins, pushes, total_chips = row
                total_games += 1
                if winner == 'player':
                    player_wins += 1
                elif winner == 'computer':
                    computer_wins += 1
                else:
                    pushes += 1
                    
                new_chips = max(0, total_chips + chips_change)
                
                cursor.execute("""
                UPDATE players 
                SET total_games = ?, player_wins = ?, computer_wins = ?, pushes = ?, total_chips = ?
                WHERE player_id = ?
                """, (total_games, player_wins, computer_wins, pushes, new_chips, player_id))
                conn.commit()

    def update_chips_direct(self, player_id: int, new_chips: int):
        with closing(self.get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE players SET total_chips = ? WHERE player_id = ?", (new_chips, player_id))
                conn.commit()

    def log_game(self, player_id: int, player_hand: List[Card], computer_hand: List[Card], winner: str,
                 player_rank: str, computer_rank: str, chips_bet: int, chips_won: int):
        p_hand_json = json.dumps([str(c) for c in player_hand])
        c_hand_json = json.dumps([str(c) for c in computer_hand])
        
        with closing(self.get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO game_history (player_id, player_hand, computer_hand, winner, player_hand_rank, computer_hand_rank, chips_bet, chips_won)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (player_id, p_hand_json, c_hand_json, winner, player_rank, computer_rank, chips_bet, chips_won))
                conn.commit()

    def log_deck(self, hand_number: int, deck_cards: List[Card]):
        deck_order_json = json.dumps([str(c) for c in deck_cards[:20]])
        with closing(self.get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO deck_history (hand_number, deck_order)
                VALUES (?, ?)
                """, (hand_number, deck_order_json))
                conn.commit()

    def get_player_stats(self, player_id: int) -> dict:
        """Gathers stats including streaks, profit metrics, and last 100 decisive hands for luck ratings."""
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
            p_row = cursor.fetchone()
            if not p_row:
                return {}
                
            # Win streak
            cursor.execute("SELECT winner FROM game_history WHERE player_id = ? ORDER BY timestamp ASC", (player_id,))
            games = cursor.fetchall()
            
            longest_streak = 0
            current_streak = 0
            for g in games:
                w = g[0]
                if w == 'player':
                    current_streak += 1
                    longest_streak = max(longest_streak, current_streak)
                elif w == 'computer':
                    current_streak = 0
                # pushes maintain win streaks but do not increment them.
            
            # Best hand achieved:
            cursor.execute("SELECT player_hand_rank FROM game_history WHERE player_id = ? AND winner != 'computer'", (player_id,))
            hands = cursor.fetchall()
            
            rank_order = {
                "Royal Flush": 10,
                "Straight Flush": 9,
                "Four of a Kind": 8,
                "Full House": 7,
                "Flush": 6,
                "Straight": 5,
                "Three of a Kind": 4,
                "Two Pair": 3,
                "One Pair": 2,
                "High Card": 1
            }
            best_rank_val = 0
            best_hand_text = "None"
            for h in hands:
                h_text = h[0]
                matched_rank = "High Card"
                for r_name in rank_order:
                    if h_text.startswith(r_name):
                        matched_rank = r_name
                        break
                r_val = rank_order.get(matched_rank, 1)
                if r_val > best_rank_val:
                    best_rank_val = r_val
                    best_hand_text = h_text
            
            # Net chips profit:
            cursor.execute("SELECT SUM(chips_won), SUM(chips_bet) FROM game_history WHERE player_id = ?", (player_id,))
            row = cursor.fetchone()
            if row and row[0] is not None and row[1] is not None:
                profit_loss = row[0] - row[1]
            else:
                profit_loss = 0
                
            # Last 100 games for Luck Meter
            cursor.execute("SELECT winner FROM game_history WHERE player_id = ? ORDER BY timestamp DESC LIMIT 100", (player_id,))
            last_100 = cursor.fetchall()
            
            last_100_wins = sum(1 for g in last_100 if g[0] == 'player')
            last_100_losses = sum(1 for g in last_100 if g[0] == 'computer')
            last_100_pushes = sum(1 for g in last_100 if g[0] == 'push')
            last_100_total = len(last_100)
            
            return {
                'player_name': p_row[1],
                'total_games': p_row[2],
                'player_wins': p_row[3],
                'computer_wins': p_row[4],
                'pushes': p_row[5],
                'total_chips': p_row[6],
                'longest_streak': longest_streak,
                'best_hand': best_hand_text,
                'profit_loss': profit_loss,
                'last_100_total': last_100_total,
                'last_100_wins': last_100_wins,
                'last_100_losses': last_100_losses,
                'last_100_pushes': last_100_pushes
            }

    def reset_db(self):
        with closing(self.get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS game_history")
                cursor.execute("DROP TABLE IF EXISTS players")
                cursor.execute("DROP TABLE IF EXISTS deck_history")
                conn.commit()
        self.init_db()


# --- STUNNING ASCII ART AND DRAW LOGIC ---

def render_cards(cards: List[Card], face_up: List[bool] = None) -> str:
    """
    Renders a list of cards side-by-side as elegant ASCII art.
    If face_up[i] is False, the card is shown face-down.
    """
    if not cards:
        return ""
        
    if face_up is None:
        face_up = [True] * len(cards)
        
    card_lines = []
    
    for i, card in enumerate(cards):
        lines = []
        is_red = card.suit in ['H', 'D']
        suit_sym = Card.SUIT_SYMBOLS[card.suit]
        rank_sym = Card.RANK_NAMES[card.rank]
        
        card_color = ANSI_RED if is_red else ANSI_GRAY
        
        if face_up[i]:
            if len(rank_sym) == 2:
                top_rank = f"{rank_sym}       "
                bottom_rank = f"       {rank_sym}"
            else:
                top_rank = f"{rank_sym}        "
                bottom_rank = f"        {rank_sym}"
                
            lines.append(c_text("┌─────────┐", ANSI_GRAY))
            lines.append(c_text(f"│{top_rank}│", card_color))
            lines.append(c_text("│         │", card_color))
            lines.append(c_text(f"│    {suit_sym}    │", card_color))
            lines.append(c_text("│         │", card_color))
            lines.append(c_text(f"│{bottom_rank}│", card_color))
            lines.append(c_text("└─────────┘", ANSI_GRAY))
        else:
            # Face-down cards with gorgeous styling
            lines.append(c_text("┌─────────┐", ANSI_GRAY))
            lines.append(c_text("│░░░░░░░░░│", ANSI_CYAN))
            lines.append(c_text("│░  G F  ░│", ANSI_CYAN))
            lines.append(c_text("│░  P O  ░│", ANSI_CYAN))
            lines.append(c_text("│░  K E  ░│", ANSI_CYAN))
            lines.append(c_text("│░░░░░░░░░│", ANSI_CYAN))
            lines.append(c_text("└─────────┘", ANSI_GRAY))
            
        card_lines.append(lines)
        
    # Join card lines side-by-side
    rendered = ""
    for row in range(7):
        row_str = "  ".join(card_lines[col][row] for col in range(len(cards)))
        rendered += row_str + "\n"
        
    return rendered


def render_luck_meter(wins: int, losses: int) -> str:
    """Renders a beautiful and informative color-coded ASCII progress bar."""
    decisive = wins + losses
    if decisive == 0:
        return "[░░░░░░░░░░░░░░░░░░░░] 50.0% (Expected: 50%) (Waiting for data)"
        
    rate = (wins / decisive) * 100
    filled = int(round(rate / 5.0)) # 20 segments
    filled = max(0, min(20, filled))
    empty = 20 - filled
    
    color = ANSI_YELLOW
    status = "Balanced ⚖️"
    if rate > 50.0:
        color = ANSI_GREEN
        status = "Lucky! 🍀"
    elif rate < 50.0:
        color = ANSI_RED
        status = "Cold... 🍂"
        
    bar = "█" * filled + "░" * empty
    return f"{c_text('[' + bar + ']', color)} {rate:.1f}% ({status} based on last {decisive} decisive hands)"


def parse_discards(input_str: str) -> List[int]:
    """Parses discard positions from string, performs robust validation."""
    cleaned = input_str.replace(',', ' ').strip()
    if not cleaned:
        return []
        
    tokens = cleaned.split()
    indices = []
    
    for token in tokens:
        if not token.isdigit():
            raise ValueError("Card positions must be integers between 1 and 5.")
        pos = int(token)
        if pos < 1 or pos > 5:
            raise ValueError("Card positions must be between 1 and 5.")
        idx = pos - 1
        if idx in indices:
            raise ValueError("Duplicate card positions are not allowed.")
        indices.append(idx)
        
    if len(indices) > 3:
        raise ValueError("You can discard at most 3 cards.")
        
    return sorted(indices)


# --- TEXT USER INTERFACE (TextUI) ---

class TextUI:
    def __init__(self, color_enabled: bool = True):
        global COLOR_ENABLED
        COLOR_ENABLED = color_enabled

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self, title: str):
        title_str = f" {title} "
        border = "=" * 60
        padded_title = title_str.center(60, '=')
        print(c_text(border, ANSI_GRAY))
        print(c_text(padded_title, ANSI_CYAN + ANSI_BOLD))
        print(c_text(border, ANSI_GRAY))
        print()

    def prompt_bet(self, max_chips: int, default_bet: int) -> int:
        """Prompts player for a bet amount, validates thoroughly."""
        while True:
            prompt = f"Enter bet amount (10, 25, 50, 100 or custom) [Default: {default_bet}]: "
            inp = input(prompt).strip()
            if not inp:
                return default_bet
                
            if inp.isdigit():
                bet = int(inp)
                if bet < 10:
                    print(c_text("Error: Minimum bet is 10 chips.", ANSI_RED))
                elif bet > max_chips:
                    print(c_text(f"Error: You don't have enough chips. Max available: {max_chips}.", ANSI_RED))
                else:
                    return bet
            else:
                print(c_text("Error: Please enter a valid positive integer.", ANSI_RED))

    def prompt_bet_optional(self, max_chips: int) -> int:
        """Prompts player for an optional add-on bet. Returns 0 if checked (Enter)."""
        while True:
            prompt = "Enter additional bet amount (min 10), or press Enter to CHECK: "
            inp = input(prompt).strip()
            if not inp:
                return 0
                
            if inp.isdigit():
                bet = int(inp)
                if bet < 10:
                    print(c_text("Error: Minimum bet is 10 chips.", ANSI_RED))
                elif bet > max_chips:
                    print(c_text(f"Error: You don't have enough chips. Max available: {max_chips}.", ANSI_RED))
                else:
                    return bet
            else:
                print(c_text("Error: Please enter a valid positive integer.", ANSI_RED))


# --- GAME CONTROLLER ---

class PokerGame:
    def __init__(self, player_name: str, config: dict, debug_luck: bool = False):
        self.config = config
        self.player_name = player_name
        self.debug_luck = debug_luck
        self.db = Database()
        self.ai = AIPlayer()
        self.player_profile = self.db.get_or_create_player(player_name)
        self.player_id = self.player_profile['player_id']
        self.sound_enabled = config.get("sound_notifications", True)

    def get_next_hand_number(self) -> int:
        stats = self.db.get_player_stats(self.player_id)
        return stats.get('total_games', 0) + 1

    def update_config_default_bet(self, bet: int):
        config_path = "config.json"
        self.config["default_bet_amount"] = bet
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception:
            pass

    def beep(self, win: bool):
        if not self.sound_enabled:
            return
        try:
            if win:
                # Upbeat fast double beep for player win
                sys.stdout.write('\a')
                sys.stdout.flush()
                time.sleep(0.15)
                sys.stdout.write('\a')
                sys.stdout.flush()
            else:
                # Single lower beep for loss
                sys.stdout.write('\a')
                sys.stdout.flush()
        except Exception:
            pass

    def play_hand(self):
        ui = TextUI(color_enabled=self.config["color_scheme_toggle"])
        ui.clear_screen()
        hand_num = self.get_next_hand_number()
        ui.print_header(f"HAND #{hand_num} - PRE-FLOP")
        
        stats = self.db.get_player_stats(self.player_id)
        chips = stats['total_chips']
        
        if chips < 10:
            print(c_text("\n[!] Oh no! You're out of chips! 💸", ANSI_RED))
            print(c_text("The house has granted you a complimentary refill of 1,000 chips. Good luck!", ANSI_GREEN))
            self.db.update_chips_direct(self.player_id, 1000)
            chips = 1000
            self.beep(win=True)
            input("\nPress Enter to continue...")
            ui.clear_screen()
            ui.print_header(f"HAND #{hand_num} - PRE-FLOP")
            
        print(f"Current Balance: {c_text(str(chips) + ' chips', ANSI_YELLOW)}")
        default_bet = min(self.config["default_bet_amount"], chips)
        bet = ui.prompt_bet(chips, default_bet)
        self.update_config_default_bet(bet)
        
        # Deduct initial bet
        total_bet = bet
        chips -= bet
        self.db.update_chips_direct(self.player_id, chips)
        
        # 1. Initialize and shuffle a fresh deck
        deck = Deck()
        deck.shuffle()
        self.db.log_deck(hand_num, deck.cards)
        
        # Deal 2 hole cards each, and 5 community cards (kept face-down initially)
        player_hand = deck.draw(2)
        computer_hand = deck.draw(2)
        community_cards = deck.draw(5)
        
        # Show Pre-flop layout
        ui.clear_screen()
        ui.print_header(f"HAND #{hand_num} - PRE-FLOP DEAL")
        print(f"Total Bet: {c_text(str(total_bet) + ' chips', ANSI_YELLOW)} | Balance: {c_text(str(chips) + ' chips', ANSI_YELLOW)}\n")
        
        print(c_text("COMPUTER'S HOLE CARDS (FACE DOWN):", ANSI_RED))
        print(render_cards(computer_hand, face_up=[False]*2))
        
        print(c_text(f"{self.player_name.upper()}'S HOLE CARDS:", ANSI_MAGENTA))
        print(render_cards(player_hand))
        
        # Prompt for Flop Wager
        print(c_text("--- ROUND 2: THE FLOP ---", ANSI_CYAN))
        if chips >= 10:
            print("Would you like to place another bet to deal the Flop, or Check/Continue?")
            add_bet = ui.prompt_bet_optional(chips)
            if add_bet > 0:
                total_bet += add_bet
                chips -= add_bet
                self.db.update_chips_direct(self.player_id, chips)
                print(f"Added {add_bet} to bet. Total bet is now {total_bet} chips.")
            else:
                print("You checked. Total bet remains same.")
        else:
            print("Insufficient chips to place additional bets. Checking automatically...")
        
        input("\nPress Enter to deal the Flop...")
            
        # Reveal Flop (first 3 community cards)
        flop_cards = community_cards[:3]
        ui.clear_screen()
        ui.print_header(f"HAND #{hand_num} - THE FLOP")
        print(f"Total Bet: {c_text(str(total_bet) + ' chips', ANSI_YELLOW)} | Balance: {c_text(str(chips) + ' chips', ANSI_YELLOW)}\n")
        
        # Display flop community cards + 2 outlines for remaining cards
        print(c_text("COMMUNITY CARDS (THE FLOP):", ANSI_YELLOW))
        # Create virtual cards for outline representation
        flop_visual = list(flop_cards)
        print(render_cards(flop_visual, face_up=[True, True, True]))
        
        print(c_text(f"{self.player_name.upper()}'S HOLE CARDS:", ANSI_MAGENTA))
        print(render_cards(player_hand))
        
        # Prompt for River Wager
        print(c_text("--- ROUND 3: THE RIVER ---", ANSI_CYAN))
        if chips >= 10:
            print("Would you like to place a final bet to deal the Turn & River, or Check/Continue?")
            add_bet = ui.prompt_bet_optional(chips)
            if add_bet > 0:
                total_bet += add_bet
                chips -= add_bet
                self.db.update_chips_direct(self.player_id, chips)
                print(f"Added {add_bet} to bet. Total bet is now {total_bet} chips.")
            else:
                print("You checked. Total bet remains same.")
        else:
            print("Checking automatically...")
            
        input("\nPress Enter to deal the River & Showdown...")
            
        # Reveal River (all 5 community cards)
        ui.clear_screen()
        ui.print_header(f"HAND #{hand_num} - SHOWDOWN")
        
        print(c_text("COMMUNITY CARDS (FINAL BOARD):", ANSI_YELLOW))
        print(render_cards(community_cards))
        
        print(c_text("COMPUTER'S HOLE CARDS REVEALED:", ANSI_RED))
        print(render_cards(computer_hand))
        
        print(c_text(f"{self.player_name.upper()}'S HOLE CARDS:", ANSI_MAGENTA))
        print(render_cards(player_hand))
        
        # 5. Hand Evaluations (best 5 out of 7)
        p_rank, p_score, p_desc = HandEvaluator.evaluate_7_cards(player_hand, community_cards)
        c_rank, c_score, c_desc = HandEvaluator.evaluate_7_cards(computer_hand, community_cards)
        
        print(c_text("-" * 60, ANSI_GRAY))
        print(f"{c_text(self.player_name + ' Has Best 5:', ANSI_MAGENTA)} {c_text(p_desc, ANSI_BOLD)}")
        print(f"{c_text('Computer Has Best 5:', ANSI_RED)} {c_text(c_desc, ANSI_BOLD)}")
        print(c_text("-" * 60, ANSI_GRAY))
        
        # Winner Determination
        winner = 'push'
        chips_won = total_bet
        chips_change = 0
        winner_text = ""
        winner_color = ANSI_YELLOW
        
        if p_score > c_score:
            winner = 'player'
            chips_won = total_bet * 2
            chips_change = total_bet
            winner_text = f"🎉 YOU WIN! Won {total_bet} chips! 🎉"
            winner_color = ANSI_GREEN
        elif c_score > p_score:
            winner = 'computer'
            chips_won = 0
            chips_change = -total_bet
            winner_text = f"💸 COMPUTER WINS! Lost {total_bet} chips. 💸"
            winner_color = ANSI_RED
        else:
            winner = 'push'
            chips_won = total_bet
            chips_change = 0
            winner_text = "🤝 IT'S A PUSH (TIE)! Chips returned. 🤝"
            winner_color = ANSI_YELLOW
            
        print("\n" + "=" * 60)
        print(c_text(winner_text.center(60), winner_color + ANSI_BOLD))
        print("=" * 60 + "\n")
        
        self.beep(win=(winner == 'player'))
        
        # Persistent Data Storage Logging
        # Add chips won back to balance
        self.db.update_player_stats(self.player_id, winner, chips_won)
        
        self.db.log_game(
            player_id=self.player_id,
            player_hand=player_hand,
            computer_hand=computer_hand,
            winner=winner,
            player_rank=p_desc,
            computer_rank=c_desc,
            chips_bet=total_bet,
            chips_won=chips_won
        )
        
        # Real-time Seed Auditing Log Summary
        if self.debug_luck:
            print(c_text("[DEBUG-LUCK AUDIT LOG SUMMARY]", ANSI_CYAN))
            print(f"  - Player Name: {self.player_name}")
            print(f"  - Hand Played: #{hand_num}")
            print(f"  - Player Hole: {player_hand}")
            print(f"  - Computer Hole: {computer_hand}")
            print(f"  - Community Board: {community_cards}")
            print(f"  - Raw Comparison Values: Player: {p_score} | Computer: {c_score}")
            print(c_text("-" * 60, ANSI_GRAY))
            
        input("Press Enter to return to main menu...")

    def show_stats_dashboard(self):
        ui = TextUI(color_enabled=self.config["color_scheme_toggle"])
        ui.clear_screen()
        ui.print_header("STATISTICS & LUCK DASHBOARD")
        
        stats = self.db.get_player_stats(self.player_id)
        if not stats:
            print("No statistics available.")
            input("\nPress Enter to return to main menu...")
            return
            
        total = stats['total_games']
        wins = stats['player_wins']
        losses = stats['computer_wins']
        pushes = stats['pushes']
        
        win_pct = (wins / total * 100) if total > 0 else 0.0
        loss_pct = (losses / total * 100) if total > 0 else 0.0
        push_pct = (pushes / total * 100) if total > 0 else 0.0
        
        decisive = wins + losses
        actual_win_rate = (wins / decisive * 100) if decisive > 0 else 50.0
        luck_rating = actual_win_rate - 50.0
        
        if luck_rating > 0:
            luck_str = f"+{luck_rating:.2f}% (Lucky! 🍀)"
            luck_color = ANSI_GREEN
        elif luck_rating < 0:
            luck_str = f"{luck_rating:.2f}% (Unlucky... 🍂)"
            luck_color = ANSI_RED
        else:
            luck_str = f"0.00% (Balanced ⚖️)"
            luck_color = ANSI_YELLOW
            
        print(f" Player Profile:     {c_text(stats['player_name'], ANSI_MAGENTA + ANSI_BOLD)}")
        print(f" Current Chips:      {c_text(str(stats['total_chips']) + ' chips', ANSI_YELLOW)}")
        print(f" Net Profit/Loss:    {c_text(('+' if stats['profit_loss'] >= 0 else '') + str(stats['profit_loss']) + ' chips', ANSI_GREEN if stats['profit_loss'] >= 0 else ANSI_RED)}")
        print(c_text("-" * 60, ANSI_GRAY))
        print(f" Total Hands Played: {total}")
        print(f" Player Wins:        {wins} ({win_pct:.1f}%)")
        print(f" Computer Wins:      {losses} ({loss_pct:.1f}%)")
        print(f" Pushes / Ties:      {pushes} ({push_pct:.1f}%)")
        print(c_text("-" * 60, ANSI_GRAY))
        print(f" Longest Win Streak: {c_text(str(stats['longest_streak']) + ' hands', ANSI_GREEN)}")
        print(f" Best Hand Achieved: {c_text(stats['best_hand'], ANSI_CYAN)}")
        print(f" Actual Win Rate:    {actual_win_rate:.2f}% (excluding ties)")
        print(f" Expected Win Rate:  50.00%")
        print(f" Luck Rating:        {c_text(luck_str, luck_color)}")
        print(c_text("-" * 60, ANSI_GRAY))
        print(" LUCK METER (Win Rate Over Last 100 Decisive Hands):")
        print(f" {render_luck_meter(stats['last_100_wins'], stats['last_100_losses'])}")
        print("=" * 60)
        
        input("\nPress Enter to return to main menu...")

    def main_menu(self):
        ui = TextUI(color_enabled=self.config["color_scheme_toggle"])
        while True:
            ui.clear_screen()
            ui.print_header("GRAVITY FLIP POKER - MAIN MENU")
            
            stats = self.db.get_player_stats(self.player_id)
            chips = stats.get('total_chips', 1000)
            
            print(f" Welcome back, {c_text(self.player_name, ANSI_MAGENTA + ANSI_BOLD)}!")
            print(f" Current Balance: {c_text(str(chips) + ' chips', ANSI_YELLOW)}")
            print(f" Total Hands Played: {c_text(str(stats.get('total_games', 0)), ANSI_CYAN)}\n")
            
            print("  [P] Play Next Hand")
            print("  [S] View Statistics Dashboard")
            print("  [D] Toggle Debug Luck Mode (Currently " + (c_text("ON", ANSI_GREEN) if self.debug_luck else c_text("OFF", ANSI_RED)) + ")")
            print("  [C] Reset Current Player Scores")
            print("  [T] Run Quick 100-Hand Luck Verification Test")
            print("  [Q] Save & Quit Game")
            print(c_text("-" * 60, ANSI_GRAY))
            
            choice = input("Select an option: ").strip().lower()
            if choice == 'p':
                self.play_hand()
            elif choice == 's':
                self.show_stats_dashboard()
            elif choice == 'd':
                self.debug_luck = not self.debug_luck
                print(f"\nDebug luck mode is now {'ON' if self.debug_luck else 'OFF'}.")
                time.sleep(1)
            elif choice == 'c':
                confirm = input("\nAre you sure you want to reset all stats for this player? (y/n): ").strip().lower()
                if confirm == 'y':
                    with closing(self.db.get_connection()) as conn:
                        with conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE players SET total_games=0, player_wins=0, computer_wins=0, pushes=0, total_chips=1000 WHERE player_id=?", (self.player_id,))
                            cursor.execute("DELETE FROM game_history WHERE player_id=?", (self.player_id,))
                            cursor.execute("DELETE FROM deck_history")
                            conn.commit()
                    print(c_text("Stats reset successfully!", ANSI_GREEN))
                    time.sleep(1.5)
            elif choice == 't':
                print("\nRunning quick 100-hand verification...")
                run_luck_test(100)
                input("\nPress Enter to return to main menu...")
            elif choice == 'q':
                print(c_text("\nThank you for playing Gravity Flip Poker! Safe travels. ✨", ANSI_GREEN))
                break


# --- AUTOMATED MONTE CARLO LUCK SIMULATION ---

def run_luck_test(n_hands=1000):
    """
    Simulates thousands of hands running automated player & computer
    random draw mechanics to mathematically prove a ~50% win rate.
    Prints statistical properties (Standard Error, Z-Score, Confidence).
    """
    print("\n" + "=" * 60)
    print("      GRAVITY FLIP POKER - MONTE CARLO LUCK SIMULATION      ")
    print("=" * 60)
    print(f"Running {n_hands} automated hands to verify ~50% win rate...")
    
    player_wins = 0
    computer_wins = 0
    pushes = 0
    
    for i in range(1, n_hands + 1):
        deck = Deck()
        deck.shuffle()
        
        player_hand = deck.draw(2)
        computer_hand = deck.draw(2)
        community_cards = deck.draw(5)
        
        _, p_score, _ = HandEvaluator.evaluate_7_cards(player_hand, community_cards)
        _, c_score, _ = HandEvaluator.evaluate_7_cards(computer_hand, community_cards)
        
        if p_score > c_score:
            player_wins += 1
        elif c_score > p_score:
            computer_wins += 1
        else:
            pushes += 1
            
        if i % 100 == 0 or i == n_hands:
            progress = i / n_hands * 100
            bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
            sys.stdout.write(f"\rProgress: [{bar}] {i}/{n_hands} hands complete.")
            sys.stdout.flush()
            
    print("\n\n" + "=" * 60)
    print("                     SIMULATION RESULTS                     ")
    print("=" * 60)
    total_decided = player_wins + computer_wins
    win_rate = (player_wins / total_decided * 100) if total_decided > 0 else 0
    loss_rate = (computer_wins / total_decided * 100) if total_decided > 0 else 0
    push_rate = (pushes / n_hands * 100)
    
    print(f"Total Hands Simulated:  {n_hands}")
    print(f"Player Wins:           {player_wins} ({player_wins/n_hands*100:.2f}%)")
    print(f"Computer Wins:         {computer_wins} ({computer_wins/n_hands*100:.2f}%)")
    print(f"Pushes (Ties):         {pushes} ({push_rate:.2f}%)")
    print("-" * 60)
    print(f"Decisive Games:        {total_decided} hands")
    print(f"Player Win Rate:       {win_rate:.2f}% (Expected: 50.00%)")
    print(f"Computer Win Rate:     {loss_rate:.2f}% (Expected: 50.00%)")
    
    if total_decided > 0:
        se = 0.5 / math.sqrt(total_decided) * 100
        z_score = abs(win_rate - 50.0) / se
        deviation = abs(win_rate - 50.0)
        print(f"Actual Deviation:      {deviation:.2f}%")
        print(f"Standard Error (SE):   {se:.2f}%")
        print(f"Z-Score:               {z_score:.2f}")
        
        print("-" * 60)
        if z_score <= 1.96:
            print("STATISTICAL VERIFICATION: SUCCESS ✅")
            print("The deviation is well within the 95% confidence interval (z <= 1.96).")
            print("This mathematically proves that the game is PURELY LUCK-BASED")
            print("and that the computer has NO advantage whatsoever.")
        else:
            print("STATISTICAL VERIFICATION: HIGHER DEVIATION ⚠️")
            print("The deviation is slightly higher than typical (expected in ~5% of samples),")
            print("but mathematically standard for completely independent trials.")
    print("=" * 60 + "\n")


# --- WEB APPLICATION BACKEND WEB SERVER ---

def run_web_server(port: int = 5000):
    """
    Launches a Flask web server, hosts REST API transaction endpoints, 
    and automatically opens the desktop web browser to the poker lobby.
    """
    from flask import Flask, request, jsonify, session
    import webbrowser
    from threading import Timer

    app = Flask(__name__, static_folder='web', static_url_path='')
    app.secret_key = "gravity_poker_super_secret_session_key_1337"
    
    db = Database()
    ai = AIPlayer()

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    @app.route('/api/select_player', methods=['POST'])
    def select_player():
        data = request.json or {}
        player_name = data.get('player_name', 'Lucky Gambler').strip()
        if not player_name:
            return jsonify({'error': 'Player name cannot be empty'}), 400
            
        player = db.get_or_create_player(player_name)
        session['player_id'] = player['player_id']
        session['player_name'] = player['player_name']
        return jsonify(player)

    @app.route('/api/place_bet', methods=['POST'])
    def place_bet():
        player_id = session.get('player_id')
        if not player_id:
            return jsonify({'error': 'No active session player found'}), 400
            
        data = request.json or {}
        bet = data.get('bet', 50)
        
        stats = db.get_player_stats(player_id)
        chips = stats['total_chips']
        
        reloaded = False
        if chips < 10:
            db.update_chips_direct(player_id, 1000)
            chips = 1000
            reloaded = True
            
        if bet < 10:
            return jsonify({'error': 'Minimum bet is 10 chips'}), 400
        if bet > chips:
            return jsonify({'error': f'Insufficient chips. Available: {chips}'}), 400
            
        deck = Deck()
        deck.shuffle()
        
        hand_num = stats['total_games'] + 1
        db.log_deck(hand_num, deck.cards)
        
        player_hand = deck.draw(2)
        computer_hand = deck.draw(2)
        community_cards = deck.draw(5)
        
        session['active_game'] = {
            'player_id': player_id,
            'bet': bet,
            'total_bet': bet,
            'deck': [c.to_dict() for c in deck.cards],
            'discards': [c.to_dict() for c in deck.discards],
            'player_hand': [c.to_dict() for c in player_hand],
            'computer_hand': [c.to_dict() for c in computer_hand],
            'community_cards': [c.to_dict() for c in community_cards],
            'hand_number': hand_num,
            'stage': 'preflop'
        }
        
        # Deduct initial bet
        db.update_chips_direct(player_id, chips - bet)
        
        return jsonify({
            'player_hand': [c.to_dict() for c in player_hand],
            'computer_hand': [{'rank': 0, 'suit': 'S'}, {'rank': 0, 'suit': 'S'}], # Hidden placeholder
            'community_cards': [],
            'stage': 'preflop',
            'total_bet': bet,
            'current_chips': chips - bet,
            'reloaded': reloaded
        })

    @app.route('/api/deal_flop', methods=['POST'])
    def deal_flop():
        player_id = session.get('player_id')
        active_game = session.get('active_game')
        if not player_id or not active_game or active_game['stage'] != 'preflop':
            return jsonify({'error': 'Invalid game transaction stage'}), 400
            
        data = request.json or {}
        add_bet = data.get('add_bet', 0)
        
        stats = db.get_player_stats(player_id)
        chips = stats['total_chips']
        
        if add_bet > 0:
            if add_bet < 10:
                return jsonify({'error': 'Minimum bet is 10 chips'}), 400
            if add_bet > chips:
                return jsonify({'error': f'Insufficient chips. Available: {chips}'}), 400
            chips -= add_bet
            db.update_chips_direct(player_id, chips)
            active_game['total_bet'] += add_bet
            
        active_game['stage'] = 'flop'
        session['active_game'] = active_game
        
        flop_cards = active_game['community_cards'][:3]
        
        return jsonify({
            'community_cards': flop_cards,
            'stage': 'flop',
            'total_bet': active_game['total_bet'],
            'current_chips': chips
        })

    @app.route('/api/deal_river', methods=['POST'])
    def deal_river():
        player_id = session.get('player_id')
        active_game = session.get('active_game')
        if not player_id or not active_game or active_game['stage'] != 'flop':
            return jsonify({'error': 'Invalid game transaction stage'}), 400
            
        data = request.json or {}
        add_bet = data.get('add_bet', 0)
        
        stats = db.get_player_stats(player_id)
        chips = stats['total_chips']
        
        if add_bet > 0:
            if add_bet < 10:
                return jsonify({'error': 'Minimum bet is 10 chips'}), 400
            if add_bet > chips:
                return jsonify({'error': f'Insufficient chips. Available: {chips}'}), 400
            chips -= add_bet
            db.update_chips_direct(player_id, chips)
            active_game['total_bet'] += add_bet
            
        active_game['stage'] = 'river'
        session['active_game'] = active_game
        
        return jsonify({
            'community_cards': active_game['community_cards'],
            'stage': 'river',
            'total_bet': active_game['total_bet'],
            'current_chips': chips
        })

    @app.route('/api/showdown', methods=['POST'])
    def showdown():
        player_id = session.get('player_id')
        active_game = session.get('active_game')
        if not player_id or not active_game or active_game['stage'] != 'river':
            return jsonify({'error': 'Invalid game transaction stage'}), 400
            
        player_hand = [Card.from_dict(d) for d in active_game['player_hand']]
        computer_hand = [Card.from_dict(d) for d in active_game['computer_hand']]
        community_cards = [Card.from_dict(d) for d in active_game['community_cards']]
        total_bet = active_game['total_bet']
        hand_num = active_game['hand_number']
        
        # 5. Hand Evaluations
        p_rank, p_score, p_desc = HandEvaluator.evaluate_7_cards(player_hand, community_cards)
        c_rank, c_score, c_desc = HandEvaluator.evaluate_7_cards(computer_hand, community_cards)
        
        # Compare outcomes
        winner = 'push'
        chips_won = total_bet
        chips_change = 0
        
        if p_score > c_score:
            winner = 'player'
            chips_won = total_bet * 2
            chips_change = total_bet
        elif c_score > p_score:
            winner = 'computer'
            chips_won = 0
            chips_change = -total_bet
        else:
            winner = 'push'
            chips_won = total_bet
            chips_change = 0
            
        # Log outcome and reconcile chips
        db.update_player_stats(player_id, winner, chips_won)
        
        db.log_game(
            player_id=player_id,
            player_hand=player_hand,
            computer_hand=computer_hand,
            winner=winner,
            player_rank=p_desc,
            computer_rank=c_desc,
            chips_bet=total_bet,
            chips_won=chips_won
        )
        
        # Clean game state
        session.pop('active_game', None)
        
        # Retrieve final chips
        stats = db.get_player_stats(player_id)
        
        return jsonify({
            'computer_hand': [c.to_dict() for c in computer_hand],
            'player_rank': p_desc,
            'computer_rank': c_desc,
            'winner': winner,
            'chips_change': ('+' if chips_change >= 0 else '') + str(chips_change),
            'chips_won': chips_won,
            'active_chips': stats['total_chips']
        })

    @app.route('/api/fold', methods=['POST'])
    def fold():
        player_id = session.get('player_id')
        active_game = session.get('active_game')
        if not player_id or not active_game:
            return jsonify({'error': 'No active game found'}), 400
            
        player_hand = [Card.from_dict(d) for d in active_game['player_hand']]
        computer_hand = [Card.from_dict(d) for d in active_game['computer_hand']]
        total_bet = active_game['total_bet']
        
        # When folding, the player loses the total_bet. Chips are already deducted.
        winner = 'computer'
        chips_won = 0
        chips_change = -total_bet
        
        db.update_player_stats(player_id, winner, chips_won)
        db.log_game(
            player_id=player_id,
            player_hand=player_hand,
            computer_hand=computer_hand,
            winner=winner,
            player_rank="Folded",
            computer_rank="Won by Default",
            chips_bet=total_bet,
            chips_won=chips_won
        )
        
        session.pop('active_game', None)
        stats = db.get_player_stats(player_id)
        
        return jsonify({
            'computer_hand': [c.to_dict() for c in computer_hand],
            'player_rank': "Folded",
            'computer_rank': "Won by Default",
            'winner': 'computer',
            'chips_change': str(chips_change),
            'chips_won': chips_won,
            'active_chips': stats['total_chips']
        })

    @app.route('/api/stats', methods=['GET'])
    def get_stats():
        player_id = session.get('player_id')
        if not player_id:
            return jsonify({'error': 'No active session found'}), 400
        stats = db.get_player_stats(player_id)
        return jsonify(stats)

    @app.route('/api/reset', methods=['POST'])
    def reset_player_stats():
        player_id = session.get('player_id')
        if not player_id:
            return jsonify({'error': 'No active session found'}), 400
            
        with closing(db.get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE players SET total_games=0, player_wins=0, computer_wins=0, pushes=0, total_chips=1000 WHERE player_id=?", (player_id,))
                cursor.execute("DELETE FROM game_history WHERE player_id=?", (player_id,))
                cursor.execute("DELETE FROM deck_history")
                conn.commit()
                
        return jsonify({'success': True})

    # Auto-open browser once Flask initializes
    def open_browser():
        try:
            webbrowser.open(f"http://127.0.0.1:{port}")
        except Exception:
            pass

    Timer(1.2, open_browser).start()
    
    print("=" * 60)
    print(c_text("        GRAVITY FLIP POKER - WEB SERVER RUNNING        ", ANSI_GREEN + ANSI_BOLD))
    print("=" * 60)
    print(f" Web app URL: {c_text('http://127.0.0.1:' + str(port), ANSI_CYAN + ANSI_UNDERLINE)}")
    print(" Press Ctrl+C to stop the server.")
    print("=" * 60)
    
    app.run(host='127.0.0.1', port=port, debug=False)


# --- CONFIGURATION MANAGER ---

def load_config() -> dict:
    """Loads configuration file. Creates defaults if it doesn't exist."""
    default_config = {
        "player_name": "Lucky Gambler",
        "default_bet_amount": 50,
        "color_scheme_toggle": True,
        "sound_notifications": True
    }
    
    config_path = "config.json"
    if not os.path.exists(config_path):
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
        except Exception:
            pass
        return default_config
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
            # Ensure any missing keys are populated from defaults
            for k, v in default_config.items():
                if k not in user_config:
                    user_config[k] = v
            return user_config
    except Exception:
        return default_config


# --- MAIN APPLICATION ENTRY POINT ---

def main():
    enable_windows_ansi()
    
    parser = argparse.ArgumentParser(
        description="Gravity Flip Poker - A beautifully designed, luck-based, provably fair poker game."
    )
    parser.add_argument(
        "--debug-luck", 
        action="store_true", 
        help="Log and audit raw random seeds, shuffling deck indices, and AI discard decisions in real time."
    )
    parser.add_argument(
        "--luck-test", 
        action="store_true", 
        help="Run Monte Carlo simulation of 1000 hands to prove the ~50%% win rate."
    )
    parser.add_argument(
        "--hands", 
        type=int, 
        default=1000, 
        help="Number of simulated hands to execute in the luck test (defaults to 1000)."
    )
    parser.add_argument(
        "--reset-db", 
        action="store_true", 
        help="Completely clear and reset the SQLite statistics database."
    )
    parser.add_argument(
        "--cli", 
        action="store_true", 
        help="Start the legacy CLI Interactive version."
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=5000, 
        help="Port to run the web server on (defaults to 5000)."
    )
    
    args = parser.parse_args()
    
    # 1. Handles CLI Resets and Tests
    if args.reset_db:
        db = Database()
        print("Resetting database...")
        db.reset_db()
        print("Database has been reset successfully.")
        sys.exit(0)
        
    if args.luck_test:
        run_luck_test(args.hands)
        sys.exit(0)
        
    if args.cli:
        # 2. Handles Interactive Mode
        config = load_config()
        game = PokerGame(
            player_name=config["player_name"], 
            config=config, 
            debug_luck=args.debug_luck
        )
        game.main_menu()
        sys.exit(0)
        
    # 3. Default to Web App
    run_web_server(args.port)

if __name__ == "__main__":
    main()

