import unittest
from ai_bridge.main import Game, PlayedFrom, TurnOutcome, initialize_card_deck, Card, CardSuit, TurnActionRequest, IllegalMoveException, GameNotStartedException, CardPlay, TableCardPair
import asyncio

"""
IMPORTANT NOTE:

Some tests might fail due to pure chance. For instance, test_illegal_move_card_not_in_hand
uses an ace of spades as a test card, but the player may have it by pure chance. If the tests
fail, try running them up to five times.
"""

def add(a: int, b: int):
    return a+b

class TestThatTestsWork(unittest.TestCase):
    def test_add_numbers(self):
        self.assertEqual(add(2,2), 4)

class TestCardsFunctionality(unittest.TestCase):
    def test_shuffle_works(self):
        """Test that the initialize_card_deck function works as expected"""
        table = initialize_card_deck(4)
        table_deck = table["table_deck"]
        player_card_stacks = table["player_card_stacks"]
        # Make sure the first four cards are not all exactly equal
        # Technically this could happen by pure chance as we use four card decks,
        # but the possibility is astronomically small. If this fails, try running it again.
        self.assertFalse(all(card == table_deck[0] for card in table_deck[1:4]))
        self.assertEqual(len(player_card_stacks), 4)
        face_up_cards = []
        face_down_cards = []
        for stack in player_card_stacks:
            # Make sure that the relevant card stacks exist with the correct cards and
            # that they are not all the same - another technically possible but extremely
            # unlikely thing to occur.
            self.assertTrue(hasattr(stack, "table_cards"))
            table_cards_list = stack.table_cards
            self.assertEqual(len(table_cards_list), 4)
            for table_cards in table_cards_list:
                self.assertIsNotNone(table_cards.face_up_card)
                self.assertIsNotNone(table_cards.face_down_card)
                self.assertNotEqual(table_cards.face_up_card, table_cards.face_down_card)
                face_up_cards.append(table_cards.face_up_card)
                face_down_cards.append(table_cards.face_down_card)
        
        self.assertFalse(all(card == face_up_cards[0] for card in face_up_cards[1:4]))
        self.assertFalse(all(card == face_down_cards[0] for card in face_down_cards[1:4]))

class TestGameTurnProcessing(unittest.TestCase):
    def setUp(self):
        """Set up a game instance before each test."""
        self.game = Game(playing_to=100)
        # Mock websockets
        self.game.players = [None, None] # Two players
        asyncio.run(self.game.start_game())

    def test_process_turn_game_not_started(self):
        """Test that an exception is raised if a turn is processed before the game starts."""
        game = Game(playing_to=100)
        action = TurnActionRequest(cards_played=[])
        with self.assertRaises(GameNotStartedException):
            game.process_turn(0, action)

    def test_process_turn_wrong_player(self):
        """Test that an exception is raised if the wrong player tries to play."""
        self.game.game_state.player_turn = 0
        action = TurnActionRequest(cards_played=[])
        with self.assertRaises(IllegalMoveException):
            self.game.process_turn(1, action)

    def test_player_passes_and_picks_up_cards(self):
        """Test that a player picks up the live cards if they pass their turn."""
        self.game.game_state.live_cards = [Card(suit=CardSuit.HEARTS, rank=5)]
        player_hand_before = len(self.game.game_state.player_card_stacks[0].cards_in_hand)
        action = TurnActionRequest(cards_played=[])
        outcome = self.game.process_turn(0, action)
        self.assertEqual(outcome, TurnOutcome.PICKED_UP_CARDS_ON_TABLE)
        self.assertEqual(len(self.game.game_state.live_cards), 0)
        player_hand_after = len(self.game.game_state.player_card_stacks[0].cards_in_hand)
        self.assertEqual(player_hand_after, player_hand_before + 1)

    def test_illegal_move_card_not_in_hand(self):
        """Test that an exception is raised if a player tries to play a card they don't have.
        Note that this test assumes the player doesn't have an ace of spades - it may fail
        due to pure chance. Try running it a few times."""
        card_not_in_hand = Card(suit=CardSuit.SPADES, rank=1) # Assume this card is not in hand
        action = TurnActionRequest(cards_played=[CardPlay(card=card_not_in_hand, played_from=PlayedFrom.CARDS_IN_HAND)])
        with self.assertRaises(IllegalMoveException):
            self.game.process_turn(0, action)

    def test_regular_turn(self):
        """Test a regular, legal turn."""
        # Give player 0 a specific card to play
        card_to_play = Card(suit=CardSuit.DIAMONDS, rank=3)
        self.game.game_state.player_card_stacks[0].cards_in_hand.append(card_to_play)
        
        # Set up the game state for a legal move
        self.game.game_state.live_cards = [Card(suit=CardSuit.HEARTS, rank=5)]
        
        action = TurnActionRequest(cards_played=[CardPlay(card=card_to_play, played_from=PlayedFrom.CARDS_IN_HAND)])
        outcome = self.game.process_turn(0, action)
        
        self.assertEqual(outcome, TurnOutcome.REGULAR_TURN)
        self.assertIn(card_to_play, self.game.game_state.live_cards)
        self.assertNotIn(card_to_play, self.game.game_state.player_card_stacks[0].cards_in_hand)

    def test_swoop_turn(self):
        """Test that a swoop correctly clears the live cards."""
        card_to_play = Card(suit=CardSuit.CLUBS, rank=10) # A 10 is a swoop card
        self.game.game_state.player_card_stacks[0].cards_in_hand.append(card_to_play)
        
        self.game.game_state.live_cards = [Card(suit=CardSuit.HEARTS, rank=5)]
        
        action = TurnActionRequest(cards_played=[CardPlay(card=card_to_play, played_from=PlayedFrom.CARDS_IN_HAND)])
        outcome = self.game.process_turn(0, action)
        
        self.assertEqual(outcome, TurnOutcome.SWOOP)
        self.assertEqual(len(self.game.game_state.live_cards), 0)

    def test_victory_turn(self):
        """Test that a player wins when they play their last card."""
        player_stack = self.game.game_state.player_card_stacks[0]
        
        # Clear player's hand and table cards, leaving one card to play
        last_card = Card(suit=CardSuit.DIAMONDS, rank=4)
        player_stack.cards_in_hand = [last_card]
        player_stack.table_cards = []

        self.game.game_state.live_cards = [Card(suit=CardSuit.HEARTS, rank=5)]
        
        action = TurnActionRequest(cards_played=[CardPlay(card=last_card, played_from=PlayedFrom.CARDS_IN_HAND)])
        outcome = self.game.process_turn(0, action)
        
        self.assertEqual(outcome, TurnOutcome.VICTORY)
