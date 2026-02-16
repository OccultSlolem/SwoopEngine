"""This guy is a "step 1" AI for SwoopEngine. All it does is find the first legal move and play it."""

from swooplib import is_swoop, is_card_playable, Card, CardPlay, PlayerCardStack, PlayedFrom, TableCardPair
from itertools import chain, combinations
from typing import List, Optional
from random import randint
import numpy as np


def is_play_legal(plays: List[CardPlay], player_stack: PlayerCardStack, live_cards: List[Card], pair: Optional[TableCardPair]) -> bool:
    """
    Evaluates whether or not a play is legal
    
    :param plays: The list of cards being played
    :type plays: List[CardPlay]
    :param player_stack: The current state of the player's stack
    :type player_stack: PlayerCardStack
    :param pair: **ONLY SUPPLY IF PLAYING A FACE DOWN CARD** - The table card pair associated with the face down table card 
    :type pair: Optional[TableCardPair]
    :return: Description
    :rtype: Whether or not the play is allowed under the rules
    """
    # 0 - If no cards are being played, the player is passing. Return True.
    # 1 - If player is playing a face down table card, return False if
      # 1a - There is a face up card above it
      # 1b - They are playing more than one card
    # 2 - Check if all card ranks are equal (if not, return False)
    # 3 - Check if all cards are in the player card stack (if not, return False)
    # 4 - Check if card is a trump card (if so, return True)
    # 5 - Check if the rank is lower than the rank currently on the table (if not, return False)
    # 6 - Return True

    if len(plays) == 0: return True # 0

    # 1    
    is_face_down = any(play.played_from == PlayedFrom.UPSIDE_DOWN_TABLE_CARD for play in plays)

    if is_face_down:
        if len(plays) != 1: return False
        if not pair or pair.face_down_card != plays[0].card: return False
        if pair.face_up_card is not None: return False
        
        return True # Note that this means the play is *legal*, but it may result in the player having to pick up the stack

    # 2
    play_rank = plays[0].card.rank

    for play in plays:
        card = play.card
        if card.rank != play_rank: return False
        # 3
        match play.played_from:
            case PlayedFrom.CARDS_IN_HAND:
                if card not in player_stack.cards_in_hand: return False
            case PlayedFrom.RIGHTSIDE_UP_TABLE_CARD:
                if not any(card == this_pair.face_up_card for this_pair in player_stack.table_cards): return False
            case PlayedFrom.UPSIDE_DOWN_TABLE_CARD:
                print("WARN: Unexpectedly found upside down table card during step 3 assessment")
                return False # This case should already be handled above, but here as a safeguard
    
    # 4
    if is_swoop(play_rank, len(plays), live_cards): return True

    # 5
    if len(live_cards) == 0 or play_rank < live_cards[0].rank: return False

    # 6
    return True

def calculate_legal_plays(player_stack: PlayerCardStack, live_cards: List[Card])-> List[List[CardPlay]]:
    """
    Returns a matrix consisting of all possible plays given the player's stack and the table state.

    The player can play:
    - Any swoop card
    - Any face down card that does not have a face up card above it
      - Note that playing a face down card may be risky as the player will have to pick up all live
        cards if it happens to be above the rank of the live cards. It is a legal play nonetheless.
    - Any hand card and/or face up table card that is below the rank of the last live cards AND are
      all of the same rank.
      - A combination of hand and face up cards can be played as long as the above constraints are
        satisfied.
    """

    legal_plays: List[List[CardPlay]] = []
    # Use a very very big number for table_rank if there are no live cards
    table_rank = 10*100 if not live_cards else live_cards[0].rank
    playable_cards: List[CardPlay] = []

    for table_pair in player_stack.table_cards:
        face_up_card = table_pair.face_up_card
        face_down_card = table_pair.face_down_card

        if face_up_card and is_card_playable(face_up_card, table_rank):
            playable_cards.append(CardPlay(card=face_up_card, played_from=PlayedFrom.RIGHTSIDE_UP_TABLE_CARD))
        if face_down_card and not face_up_card:
            # face down cards can only be played by themselves and cannot be joined with other cards
            # add each uncovered one as a legal play
            legal_plays.append([CardPlay(card=face_down_card, played_from=PlayedFrom.UPSIDE_DOWN_TABLE_CARD)])
    
    for card in player_stack.cards_in_hand:
        if is_card_playable(card, table_rank): playable_cards.append(CardPlay(card=card, played_from=PlayedFrom.CARDS_IN_HAND))

    # Group playable cards by rank
    cards_by_rank: dict[int, list[CardPlay]] = {}
    for pc in playable_cards:
        cards_by_rank.setdefault(pc.card.rank, []).append(pc)
    
    for rank_group in cards_by_rank.values():
        s = list(rank_group)
        # Generate the power set for cards of the same rank
        power_set = [list(combo) for combo in chain.from_iterable(combinations(s, r) for r in range(1, len(s) + 1))]
        legal_plays.extend(power_set)
    
    # Add the option to pass (playing no cards)
    legal_plays.append([])

    return legal_plays

# Select any random play!
def simple_turn_processor(current_stack: PlayerCardStack, live_cards: List[Card]) -> List[CardPlay]:
    plays = calculate_legal_plays(current_stack, live_cards)
    random_play = randint(0, len(plays))
    return plays[random_play]
