import unittest
from ai_bridge.main import initialize_card_deck

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
        self.assertFalse(all(card == table_deck[0] for card in table_deck[1:4]))
        self.assertEqual(len(player_card_stacks), 4)
        face_up_cards = []
        face_down_cards = []
        for stack in player_card_stacks:
            self.assertTrue(hasattr(stack, "table_cards"))
            table_cards_list = stack.table_cards
            self.assertEqual(len(table_cards_list), 4)
            for table_cards in table_cards_list:
                self.assertIn("face_up_card", table_cards)
                self.assertIn("face_down_card", table_cards)
                self.assertNotEqual(table_cards["face_up_card"], table_cards["face_down_card"])
                face_up_cards.append(table_cards["face_up_card"])
                face_down_cards.append(table_cards["face_down_card"])
        
        self.assertFalse(all(card == face_up_cards[0] for card in face_up_cards[1:4]))
        self.assertFalse(all(card == face_down_cards[0] for card in face_down_cards[1:4]))
