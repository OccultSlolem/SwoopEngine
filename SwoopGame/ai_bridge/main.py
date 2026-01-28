from typing import Optional, List, Dict
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel, Field
from uuid import uuid4
from enum import Enum
from random import shuffle
from math import inf

# --- Swoop logic

class CardSuit(str, Enum):
    DIAMONDS = 'diamonds'
    CLUBS = 'clubs'
    SPADES = 'spades'
    HEARTS = 'hearts'

class Card(BaseModel):
    suit: CardSuit
    rank: int = Field(..., ge=1, le=13)

class TableCardPair(BaseModel):
    face_down_card: Optional[Card]
    face_up_card: Optional[Card]

class PlayerCardStack(BaseModel):
    table_cards: List[TableCardPair]
    cards_in_hand: List[Card]

class PlayedFrom(str, Enum):
    CARDS_IN_HAND = "cards_in_hand"
    UPSIDE_DOWN_TABLE_CARD = "upside_down_table_card"
    RIGHTSIDE_UP_TABLE_CARD = "rightside_up_table_card"

class TurnOutcome(str, Enum):
    REGULAR_TURN = "regular_turn"
    SWOOP = "swoop"
    PICKED_UP_CARDS_ON_TABLE = "picked_up_cards_on_table"
    VICTORY = "victory"

class TurnActionLog(BaseModel):
    played_from: PlayedFrom
    outcome: TurnOutcome
    player: int
    rank_played: int
    number_of_cards_played: int

class CardPlay(BaseModel):
    card: Card
    played_from: PlayedFrom

class TurnActionRequest(BaseModel):
    cards_played: List[CardPlay]

class GameState(BaseModel):
    table_deck: List[Card]
    live_cards: List[Card]
    player_card_stacks: List[PlayerCardStack] # Assume position 0 is the player if player is not AI
    player_points: List[int] # The number of points each player has. Like golf, fewer is better.
    playing_to: int # Once any one player reaches this many points, the game ends.
    player_turn: int
    turn_actions: List[TurnActionLog]
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
            stack.table_cards.append(TableCardPair(face_down_card=card_down, face_up_card=card_up))
        
        player_stacks.append(stack)
    
    # 4
    return {
        "table_deck": shuffled_deck,
        "player_card_stacks": player_stacks
    }

def is_swoop(rank_played: int, num_cards_played: int, live_cards: List[Card]) -> bool:
    """
    Returns true if the play resulted in a swoop. A swoop occured if any of the following
    are true:

    - The player put down a ten or jack (ranks 10 and 11)
    - The player put down four or more cards of the same rank
    - The top four or more live cards, including what the player just put down,
    have the same rank
    """
    if rank_played == 10 or rank_played == 11: return True
    if num_cards_played >= 4: return True
    
    if len(live_cards) == 0: return False
    latest_live_card_rank = live_cards[-1].rank
    if latest_live_card_rank != rank_played: return False

    count = 0
    for card in reversed(live_cards):
        if card.rank == rank_played:
            count += 1
        else:
            break
    
    if count + num_cards_played >= 4:
        return True

    return False

class IncorrectPlayerAmountException(Exception):
    pass

class GameNotStartedException(Exception):
    pass

class IllegalMoveException(Exception):
    pass

class BadArgumentException(Exception):
    pass

class Game:
    """Represents a single game instance"""
    def __init__(self, playing_to: int):
        self.game_state = GameState(
            table_deck=[],
            live_cards=[],
            player_card_stacks=[],
            player_points=[],
            player_turn=0,
            playing_to=playing_to,
            turn_actions=[],
            game_active=False
        )
        self.players: List[WebSocket] = []
    
    def add_player(self, websocket: WebSocket):
        self.players.append(websocket)
    
    def remove_player(self, websocket: WebSocket):
        self.players.remove(websocket)
    
    async def start_game(self):
        num_players = len(self.players)

        if num_players < 2 or num_players > 6:
            raise IncorrectPlayerAmountException("Games must have between 2 and 6 players.")

        deck = initialize_card_deck(num_players)
        self.game_state.player_card_stacks = deck["player_card_stacks"]
        self.game_state.table_deck = deck["table_deck"]
        self.game_state.game_active = True
        await self.broadcast_all(self.game_state.model_dump_json())
    
    def process_turn(self, player: int, action_request: TurnActionRequest) -> TurnOutcome:
        # 1. Parse what the player did
        # 2. If the player passed, they must pick up all cards on table
        # 3. Ensure that the action was legal
        # 4. Check if the move resulted in a win (last card played)
        # 5. If no win, check if a swoop occured and clear live_cards if so.
        # 6. Return the turn outcome.

        if not self.game_state.game_active:
            raise GameNotStartedException("The game has not started.")
        
        if player != self.game_state.player_turn:
            raise IllegalMoveException("It's not your turn!")
        
        if player < 0:
            raise BadArgumentException("Attempted to play on a negative player.")
        
        if player >= len(self.game_state.player_card_stacks):
            raise IncorrectPlayerAmountException("Attempted to act on a nonexistent player.")
        
        player_stack = self.game_state.player_card_stacks[player]
        if len(action_request.cards_played) == 0:
            # The player passed, they must pick up all cards on table
            player_stack.cards_in_hand.extend(self.game_state.live_cards)
            self.game_state.live_cards = []
            return TurnOutcome.PICKED_UP_CARDS_ON_TABLE
        
        top_live_rank = self.game_state.live_cards[-1].rank if len(self.game_state.live_cards) > 0 else inf

        # Validate that the cards played exist in the player's stack
        for play in action_request.cards_played:
            card_played = play.card
            played_from = play.played_from

            if played_from == PlayedFrom.CARDS_IN_HAND:
                if card_played not in player_stack.cards_in_hand:
                    raise IllegalMoveException(f"Card {card_played} not in player's hand.")
            elif played_from == PlayedFrom.RIGHTSIDE_UP_TABLE_CARD:
                if not any(d.face_up_card == card_played for d in player_stack.table_cards):
                    raise IllegalMoveException(f"Card {card_played} not on player's face-up table cards.")
            elif played_from == PlayedFrom.UPSIDE_DOWN_TABLE_CARD:
                if not any(d.face_down_card == card_played for d in player_stack.table_cards):
                    raise IllegalMoveException(f"Card {card_played} not on player's face-down table cards.")

        # Check if the player put down an upside down table card
        if any(
            play.played_from == PlayedFrom.UPSIDE_DOWN_TABLE_CARD
            for play in action_request.cards_played
        ):
            # This is a blind play. The player doesn't know what card they are playing.
            # They can only play one card.
            if len(action_request.cards_played) > 1:
                raise IllegalMoveException("When playing a face-down card, you can only play that one card.")
            
            card_played = action_request.cards_played[0].card
            if card_played.rank > top_live_rank: 
                player_stack.cards_in_hand.extend(self.game_state.live_cards)
                self.game_state.live_cards = []
                return TurnOutcome.PICKED_UP_CARDS_ON_TABLE
        
        # Validate that all cards played have the same rank
        first_card_rank = action_request.cards_played[0].card.rank
        if not all(play.card.rank == first_card_rank for play in action_request.cards_played):
            raise IllegalMoveException("All cards played in a single turn must have the same rank.")

        # Validate that the rank played is legal
        # Swoop cards (10 and jack) are always legal to play
        if first_card_rank > top_live_rank and (first_card_rank != 10 and first_card_rank != 11):
            raise IllegalMoveException("Card played has higher rank than top of live cards.")

        # The move is legal, so remove the cards from the player's stack
        for play in action_request.cards_played:
            card_played = play.card
            played_from = play.played_from

            if played_from == PlayedFrom.CARDS_IN_HAND:
                player_stack.cards_in_hand.remove(card_played)
            elif played_from == PlayedFrom.RIGHTSIDE_UP_TABLE_CARD:
                for i, table_card_pair in enumerate(player_stack.table_cards):
                    if table_card_pair.face_up_card == card_played:
                        player_stack.table_cards[i].face_up_card = None
                        break
            elif played_from == PlayedFrom.UPSIDE_DOWN_TABLE_CARD:
             for i, table_card_pair in enumerate(player_stack.table_cards):
                if table_card_pair.face_down_card == card_played:
                    player_stack.table_cards[i].face_down_card = None
                    break
        
        swoop_check = is_swoop(first_card_rank, len(action_request.cards_played), self.game_state.live_cards)
        
        # Add played cards to the live_cards pile
        played_cards = [play.card for play in action_request.cards_played]
        self.game_state.live_cards.extend(played_cards)

        # Check for victory condition
        if (
            len(player_stack.cards_in_hand) == 0 and
            all(card_pair.face_up_card is None for card_pair in player_stack.table_cards) and
            all(card_pair.face_down_card is None for card_pair in player_stack.table_cards)
        ):
            return TurnOutcome.VICTORY
        elif swoop_check:
            self.game_state.live_cards = []
            return TurnOutcome.SWOOP

        return TurnOutcome.REGULAR_TURN
    
    async def broadcast_all(self, message: str):
        # These next two lines exist primarily to facilitate unit testing in mockless setups
        if len(self.players) == 0: return
        if (all(player is None for player in self.players)): return
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
