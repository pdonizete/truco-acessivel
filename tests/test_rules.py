from __future__ import annotations

import unittest

from core.deck import Card, Suit
from core.rules import (
    compare_cards,
    determine_hand_winner,
    determine_manilha_rank,
    determine_trick_winner,
    next_raise_value,
    next_rank,
    refusal_points,
)


class TrucoRulesTestCase(unittest.TestCase):
    def test_next_rank_wraps_after_three(self) -> None:
        self.assertEqual(next_rank("3"), "4")
        self.assertEqual(next_rank("7"), "Q")

    def test_determine_manilha_rank_from_vira(self) -> None:
        vira = Card("K", Suit.COPAS)
        self.assertEqual(determine_manilha_rank(vira), "A")

    def test_manilha_beats_any_non_manilha(self) -> None:
        vira = Card("3", Suit.OUROS)
        manilha = Card("4", Suit.ESPADAS)
        strongest_non_manilha = Card("3", Suit.PAUS)
        self.assertGreater(compare_cards(manilha, strongest_non_manilha, vira), 0)

    def test_manilha_suit_order_is_official(self) -> None:
        vira = Card("3", Suit.OUROS)
        zap = Card("4", Suit.PAUS)
        copas = Card("4", Suit.COPAS)
        espadas = Card("4", Suit.ESPADAS)
        ouros = Card("4", Suit.OUROS)
        self.assertGreater(compare_cards(zap, copas, vira), 0)
        self.assertGreater(compare_cards(copas, espadas, vira), 0)
        self.assertGreater(compare_cards(espadas, ouros, vira), 0)

    def test_non_manilha_order_keeps_three_as_strongest(self) -> None:
        vira = Card("5", Suit.COPAS)
        self.assertGreater(compare_cards(Card("3", Suit.COPAS), Card("2", Suit.COPAS), vira), 0)
        self.assertGreater(compare_cards(Card("A", Suit.COPAS), Card("K", Suit.COPAS), vira), 0)

    def test_trick_winner_returns_none_on_tie(self) -> None:
        vira = Card("5", Suit.COPAS)
        cards = {
            "jogador": Card("7", Suit.OUROS),
            "computador": Card("7", Suit.PAUS),
        }
        self.assertIsNone(determine_trick_winner(cards, vira))

    def test_hand_winner_uses_second_round_after_first_tie(self) -> None:
        winners = [None, "computador"]
        self.assertEqual(determine_hand_winner(winners, "jogador"), "computador")

    def test_hand_winner_uses_first_round_if_third_round_ties(self) -> None:
        winners = ["jogador", "computador", None]
        self.assertEqual(determine_hand_winner(winners, "computador"), "jogador")

    def test_all_tied_rounds_go_to_hand_starter(self) -> None:
        winners = [None, None, None]
        self.assertEqual(determine_hand_winner(winners, "computador"), "computador")

    def test_raise_progression_and_refusal_points(self) -> None:
        self.assertEqual(next_raise_value(1), 3)
        self.assertEqual(next_raise_value(3), 6)
        self.assertEqual(next_raise_value(9), 12)
        self.assertIsNone(next_raise_value(12))
        self.assertEqual(refusal_points(3), 1)
        self.assertEqual(refusal_points(6), 3)
        self.assertEqual(refusal_points(12), 9)


if __name__ == "__main__":
    unittest.main()
