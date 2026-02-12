"""This guy is a "step 1" AI for SwoopEngine. All it does is find the first legal move and play it."""

from swooplib import Card, CardPlay, PlayerCardStack, PlayedFrom, TableCardPair
from typing import List

def is_play_legal(plays: List[CardPlay], player_stack: PlayerCardStack) -> bool:
    # 0 - If no cards are being played, the player is passing. Return True.
    # 1 - If player is playing a face down table card, return False if
      # 1a - There is a face up card above it
      # 1b - They are playing more than one card
    # 2 - Check if all card ranks are equal (if not, return False)
    # 3 - Check if all cards are in the player card stack (if not, return False)
    # 4 - Check if card is a trump card (if so, return True)
    # 5 - Check if the rank is lower than the rank currently on the table (if not, return False)
    # 6 - Return True

    if len(plays) == 0: return True

    first_rank = plays[0].card.rank

    for play in plays:
        card = play.card
        if card.rank != first_rank: return False
        match play.played_from:
            case PlayedFrom.CARDS_IN_HAND:
                if card not in player_stack.cards_in_hand: return False
            case PlayedFrom.UPSIDE_DOWN_TABLE_CARD:
                if not any(card == pair.face_down_card for pair in player_stack.table_cards): return False
            case PlayedFrom.RIGHTSIDE_UP_TABLE_CARD:
                if not any(card == pair.face_up_card for pair in player_stack.table_cards): return False

    # TODO
    return True