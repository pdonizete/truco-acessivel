from __future__ import annotations

import unittest

from ai.bot import Difficulty, TrucoBot
from core.deck import Card, Suit
from core.state import BOT, PLAYER, GamePhase, MatchSettings, TrucoGame


class NoBluffRandom:
    def random(self) -> float:
        return 1.0


class TrucoBotTestCase(unittest.TestCase):
    def make_raise_game(self, hand_value: int) -> TrucoGame:
        game = TrucoGame(settings=MatchSettings(difficulty=Difficulty.INTERMEDIARIO))
        game.vira = Card("4", Suit.OUROS)
        game.hands = {
            BOT: [
                Card("5", Suit.OUROS),
                Card("6", Suit.OUROS),
                Card("5", Suit.COPAS),
            ],
            PLAYER: [
                Card("K", Suit.PAUS),
                Card("A", Suit.PAUS),
                Card("2", Suit.PAUS),
            ],
        }
        game.phase = GamePhase.BOT_TURN
        game.current_player = BOT
        game.hand_value = hand_value
        return game

    def test_raise_request_threshold_increases_with_hand_value(self) -> None:
        bot = TrucoBot(Difficulty.INTERMEDIARIO, rng=NoBluffRandom())

        self.assertTrue(bot.should_request_raise(self.make_raise_game(hand_value=1)))
        self.assertFalse(bot.should_request_raise(self.make_raise_game(hand_value=3)))


class TrucoRaiseStateTestCase(unittest.TestCase):
    def test_same_player_cannot_chain_raise_before_playing_card(self) -> None:
        game = TrucoGame(settings=MatchSettings(difficulty=Difficulty.INTERMEDIARIO))
        game.start_new_match()
        game.start_new_hand()
        game.current_player = BOT
        game.phase = GamePhase.BOT_TURN

        game.request_raise(BOT)
        game.accept_raise(PLAYER)

        self.assertEqual(game.hand_value, 3)
        self.assertFalse(game.can_raise(BOT))

    def test_accepting_escalated_raise_resumes_original_turn(self) -> None:
        game = TrucoGame(settings=MatchSettings(difficulty=Difficulty.INTERMEDIARIO))
        game.start_new_match()
        game.start_new_hand()
        game.current_player = BOT
        game.phase = GamePhase.BOT_TURN

        game.request_raise(BOT)
        game.escalate_raise(PLAYER)
        game.accept_raise(BOT)

        self.assertEqual(game.hand_value, 6)
        self.assertEqual(game.current_player, BOT)
        self.assertEqual(game.phase, GamePhase.BOT_TURN)
        self.assertFalse(game.can_raise(BOT))

    def test_loaded_turn_phase_follows_current_player_without_pending_raise(self) -> None:
        game = TrucoGame(settings=MatchSettings(difficulty=Difficulty.INTERMEDIARIO))
        game.start_new_match()
        game.start_new_hand()
        game.current_player = BOT
        game.phase = GamePhase.BOT_TURN
        snapshot = game.to_dict()
        snapshot["phase"] = GamePhase.PLAYER_TURN.value

        loaded = TrucoGame.from_dict(snapshot)

        self.assertEqual(loaded.current_player, BOT)
        self.assertEqual(loaded.phase, GamePhase.BOT_TURN)


if __name__ == "__main__":
    unittest.main()
