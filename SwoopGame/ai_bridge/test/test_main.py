import unittest
from unittest.mock import Mock, patch
from ai_bridge.main import (
    Game, PlayedFrom, TurnOutcome, initialize_card_deck, Card, CardSuit, 
    TurnActionRequest, IllegalMoveException, GameNotStartedException, 
    CardPlay, sort_message, BadArgumentException, GameManager
)
import asyncio
from uuid import uuid4

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
        # Make sure the first eighteen cards are not all exactly equal
        self.assertFalse(all(card == table_deck[0] for card in table_deck[1:18]))
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
            identical_pairs = 0
            for table_cards in table_cards_list:
                self.assertIsNotNone(table_cards.face_up_card)
                self.assertIsNotNone(table_cards.face_down_card)
                # self.assertNotEqual(table_cards.face_up_card, table_cards.face_down_card)

                if (table_cards.face_up_card == table_cards.face_down_card): identical_pairs += 1
                face_up_cards.append(table_cards.face_up_card)
                face_down_cards.append(table_cards.face_down_card)

        self.assertLess(identical_pairs, len(player_card_stacks) * 4, "All table card pairs were identical, which is highly improbable and likely indicates a bug.") # type: ignore
        self.assertFalse(all(card == face_up_cards[0] for card in face_up_cards[1:4]))
        self.assertFalse(all(card == face_down_cards[0] for card in face_down_cards[1:4]))

class TestGameTurnProcessing(unittest.TestCase):
    def setUp(self):
        """Set up a game instance before each test."""
        game_id = str(uuid4())
        self.game = Game(playing_to=100, max_players=2, game_id=game_id)
        # Mock websockets
        self.game.players = [None, None] # type: ignore # Two players
        asyncio.run(self.game.start_game())

    def test_process_turn_game_not_started(self):
        """Test that an exception is raised if a turn is processed before the game starts."""
        game_id = str(uuid4())
        game = Game(playing_to=100, max_players=6, game_id=game_id)
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
        card_not_in_hand = Card(suit=CardSuit.SPADES, rank=1)
        # Find a card that is not in the player's hand
        player_hand = self.game.game_state.player_card_stacks[0].cards_in_hand
        all_ranks = range(1, 14)
        all_suits = [CardSuit.HEARTS, CardSuit.DIAMONDS, CardSuit.CLUBS, CardSuit.SPADES]

        for rank in all_ranks:
            for suit in all_suits:
                potential_card = Card(suit=suit, rank=rank)
                if potential_card not in player_hand:
                    card_not_in_hand = potential_card
                    break
                if 'card_not_in_hand' in locals():
                    break

        action = TurnActionRequest(cards_played=[CardPlay(card=card_not_in_hand, played_from=PlayedFrom.CARDS_IN_HAND)])
        with self.assertRaises(IllegalMoveException):
            self.game.process_turn(0, action)

    def test_regular_turn(self):
        """Test a regular, legal turn."""
        # Give player 0 a specific card to play
        card_to_play = Card(suit=CardSuit.DIAMONDS, rank=3)
        card_not_to_play = Card(suit=CardSuit.CLUBS, rank=8)
        self.game.game_state.player_card_stacks[0].cards_in_hand = [card_to_play, card_not_to_play]
        
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

class MockMessage:
    def __init__(self, type, payload=None):
        self.type = type
        if payload:
            self.payload = Mock(**payload)


class TestSortMessage(unittest.TestCase):
    def setUp(self):
        self.game_manager = GameManager()
        self.mock_websocket = Mock()


    def test_sort_message_no_type(self):
        """Test that an exception is raised if the message has no type."""
        message = {} # A dict, which has no 'type' attribute
        with self.assertRaises(BadArgumentException):
            sort_message(message, self.mock_websocket, self.game_manager)

    def test_sort_message_unknown_type(self):
        """Test that an exception is raised for an unknown message type."""
        message = {"type": "UNKNOWN_TYPE"}
        with self.assertRaises(BadArgumentException):
            sort_message(message, self.mock_websocket, self.game_manager)

    @patch('ai_bridge.main.GameManager.create_game')
    def test_create_game_default(self, mock_create_game):
        """Test creating a game with default parameters."""
        message = {"type": "CREATE_GAME"}
        sort_message(message, self.mock_websocket, self.game_manager)
        mock_create_game.assert_called_once_with(300, 6, host=self.mock_websocket)

    @patch('ai_bridge.main.GameManager.create_game')
    def test_create_game_with_payload(self, mock_create_game):
        """Test creating a game with custom parameters."""
        message = {"type": "CREATE_GAME", "payload": {'playing_to': 200, 'max_players': 4}}
        sort_message(message, self.mock_websocket, self.game_manager)
        mock_create_game.assert_called_once_with(200, 4, host=self.mock_websocket)

    def test_join_game_by_id_no_id(self):
        """Test joining a game by ID when no ID is provided."""
        message = {"type": "JOIN_GAME_BY_ID", "payload": {}}
        with self.assertRaises(BadArgumentException):
            sort_message(message, self.mock_websocket, self.game_manager)

    @patch('ai_bridge.main.GameManager.join_game_by_id')
    def test_join_game_by_id(self, mock_join_game):
        """Test joining a game by a specific ID."""
        game_id = "test_game_id"
        message = {"type": "JOIN_GAME_BY_ID", "payload": {'game_id': game_id}}
        sort_message(message, self.mock_websocket, self.game_manager)
        mock_join_game.assert_called_once_with(self.mock_websocket, game_id)

    @patch('ai_bridge.main.GameManager.join_any_game')
    def test_join_any_game(self, mock_join_any_game):
        """Test joining any available game."""
        message = {"type": "JOIN_ANY_GAME"}
        sort_message(message, self.mock_websocket, self.game_manager)
        mock_join_any_game.assert_called_once_with(self.mock_websocket)
