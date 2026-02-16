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

def is_card_playable(card: Card, table_rank: int) -> bool:
    if card.rank == 10 or card.rank == 11:
        return True
    
    if card.rank <= table_rank:
        return True
    
    return False

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
