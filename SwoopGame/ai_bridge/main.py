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

class GameState(BaseModel):
    table_deck: List[Card]
    live_cards: List[Card]
    card_stacks: List[PlayerCardStack] # Assume position 0 is the player if player is not AI
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

        

class Game:
    """Represents a single game instance"""
    def __init__(self, num_players: int):
        game_state = GameState(
            table_deck=[],
            live_cards=[],
            card_stacks=[],
            game_active=False
        )
        self.players: List[WebSocket] = []
    
    def add_player(self, websocket: WebSocket):
        self.players.append(websocket)
    
    def remove_player(self, websocket: WebSocket):
        self.players.remove(websocket)
    
    async def broadcast_all(self, message: str):
        for player in self.players:
            await player.send_text(message)

class GameManager:
    """Singleton class that manages all active game sessions"""
    def __init__(self):
        # The str represents a unique game ID
        self.active_games: Dict[str, Game] = {}
    
    def create_game(self, num_players):
        game_id = uuid4()
        self.active_games[game_id: game_id, ]

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
