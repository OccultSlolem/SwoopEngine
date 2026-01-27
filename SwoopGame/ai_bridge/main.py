from typing import Optional, List, Dict
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel, Field
from uuid import uuid4
from enum import Enum
from random import shuffle

# --- Swoop logic

class CardSuit(str, Enum):
    DIAMONDS = 'diamonds'
    CLUBS = 'clubs'
    SPADES = 'spades'
    HEARTS = 'hearts'

class Card(BaseModel):
    suit: CardSuit
    rank: int = Field(..., ge=1, le=13)

class PlayerCardStack(BaseModel):
    table_cards: List[Dict[Optional[Card], Optional[Card]]]
    cards_in_hand: List[Card]

class TurnAction(BaseModel):
    class PlayedFrom(str, Enum):
        CARDS_IN_HAND = "cards_in_hand"
        UPSIDE_DOWN_TABLE_CARD = "upside_down_table_card"
        RIGHTSIDE_UP_TABLE_CARD = "rightside_up_table_card"

    played_from: PlayedFrom
    player: int
    rank_played: int
    number_of_cards_played: int
    was_swoop: bool
    was_winning_move: bool
class GameState(BaseModel):
    table_deck: List[Card]
    live_cards: List[Card]
    player_card_stacks: List[PlayerCardStack] # Assume position 0 is the player if player is not AI
    player_points: List[int] # The number of points each player has. Like golf, fewer is better.
    playing_to: int # Once any one player reaches this many points, the game ends.
    player_turn: int
    turn_actions: TurnAction
    game_active: bool


def initialize_card_deck(num_players: int):
    # 1. Generate 4 52-card decks (no jokers)
    # 2. Shuffle the deck
    # 3. Distribute the deck to the number of players specified
    # 4. Return the remaining cards in the deck and each player's decks

    # 1
    SUITS: List[CardSuit] = list(CardSuit)
    four_card_decks: List[Card] = []

    for _ in range(4):
        for suit in SUITS:
            for rank in range(1, 14):
                four_card_decks.append(Card(suit=suit, rank=rank))
    
    # 2

    shuffle(four_card_decks)
    shuffled_deck = four_card_decks # Use a more descriptive name
    
    # 3
    player_stacks: List[PlayerCardStack] = []
    for _ in range(num_players):
        stack = PlayerCardStack(
            table_cards=[],
            cards_in_hand=[]
        )

        # Distribute 14 cards to cards_in_hand
        for _ in range(14):
            card = shuffled_deck.pop()
            stack.cards_in_hand.append(card)
        
        # Distribute 4 pairs of cards to table_cards
        for _ in range(4):
            card_down = shuffled_deck.pop()
            card_up = shuffled_deck.pop()
            stack.table_cards.append({ "face_down_card": card_down, "face_up_card": card_up })
        
        player_stacks.append(stack)
    
    # 4
    return {
        "table_deck": shuffled_deck,
        "player_card_stacks": player_stacks
    }

class IncorrectPlayerAmountException(Exception):
    pass

class Game:
    """Represents a single game instance"""
    def __init__(self, playing_to: int):
        self.game_state = GameState(
            table_deck=[],
            live_cards=[],
            player_card_stacks=[],
            player_turn=0,
            playing_to=playing_to,
            game_active=False
        )
        self.players: List[WebSocket] = []
    
    def add_player(self, websocket: WebSocket):
        self.players.append(websocket)
    
    def remove_player(self, websocket: WebSocket):
        self.players.remove(websocket)
    
    def start_game(self):
        num_players = len(self.players)

        if num_players < 2 or num_players > 6:
            raise IncorrectPlayerAmountException("Games must have between 2 and 6 players.")

        deck = initialize_card_deck(num_players)
        self.game_state.player_card_stacks = deck["player_card_stacks"]
        self.game_state.table_deck = deck["table_deck"]
        self.game_state.game_active = True
        self.broadcast_all(self.game_state)
    
    def process_turn():
        # 1. Parse what the player did
        # 2. Ensure that the action was legal
        # 3. Check if the move resulted in a win (last card played)
        # 3a - Calculate points. If a player won, log the results and moves of the game
        # for ML training
        # 4. If no win, check if a swoop occured and clear live_cards if so.
        #   - A swoop occurs if a 10 or jack is played, or if the move results in the
        #   last four or more cards having equal rank.
        # 5. If the player passed, they pick up all live_cards.
        # 6. Log the turn action and results.
        # 7. Broadcast the new game state.

        pass
    
    async def broadcast_all(self, message: str):
        for player in self.players:
            await player.send_text(message)

class GameManager:
    """Singleton class that manages all active game sessions"""
    def __init__(self):
        # The str represents a unique game ID
        self.active_games: Dict["game_id": str, "game_state": Game] = {}
    
    def create_game(self):
        game_id = uuid4()
        game_state = Game()
        self.active_games["game_id": game_id, "game_state": game_state]
        return game_id

# --- FastAPI Application

app = FastAPI()

@app.get("/")
def read_root():
    return { "Hello": "World" }

@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(data)
