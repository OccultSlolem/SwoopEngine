from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

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
    max_players: int
    turn_actions: List[TurnActionLog]
    game_active: bool
    
class SystemMessageType(str, Enum):
    GAME_STATUS = 'GAME_STATUS'
    GAME_STARTING = 'GAME_STARTING'
    ROUND_COMPLETE = 'ROUND_COMPLETE'
    GAME_COMPLETE = 'GAME_COMPLETE'

class SystemMessage(BaseModel):
    message_type: SystemMessageType
    message: str
