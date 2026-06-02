import unittest
from gravity_poker import Card, Deck, HandEvaluator, AIPlayer, HandRank

class TestGravityPoker(unittest.TestCase):
    def test_card_creation(self):
        card = Card(14, 'H')
        self.assertEqual(card.suit, 'H')
        self.assertEqual(card.rank, 14)
        self.assertEqual(repr(card), "A♥")

    def test_deck_shuffle_and_draw(self):
        deck = Deck()
        self.assertEqual(len(deck.cards), 52)
        deck.shuffle(seed=42)
        drawn = deck.draw(5)
        self.assertEqual(len(drawn), 5)
        self.assertEqual(len(deck.cards), 47)

    def test_hand_evaluator_royal_flush(self):
        # Create a Royal Flush (10, J, Q, K, A of Spades)
        hand = [
            Card(10, 'S'), Card(11, 'S'), Card(12, 'S'), 
            Card(13, 'S'), Card(14, 'S')
        ]
        community = [Card(2, 'H'), Card(3, 'D')]
        
        rank, score, desc = HandEvaluator.evaluate_7_cards(hand, community)
        self.assertEqual(rank, HandRank.ROYAL_FLUSH)
        self.assertTrue("Royal Flush" in desc)

    def test_ai_player_decision(self):
        ai = AIPlayer()
        hand = [
            Card(2, 'S'), Card(7, 'H'), Card(10, 'D'), 
            Card(12, 'C'), Card(14, 'S')
        ]
        discards, seed = ai.decide_discards(hand)
        self.assertTrue(isinstance(discards, list))
        self.assertTrue(0 <= len(discards) <= 3)
        for d in discards:
            self.assertTrue(0 <= d <= 4)

if __name__ == '__main__':
    unittest.main()

