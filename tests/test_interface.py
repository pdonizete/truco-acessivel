from __future__ import annotations

import unittest
from unittest.mock import patch

from ai.bot import Difficulty
from cli.interface import TerminalInterface
from core.state import BOT, PLAYER, MatchSettings, TrucoGame


class DummyStore:
    def save_match_snapshot(self, snapshot: dict[str, object]) -> None:
        self.snapshot = snapshot

    def clear_match_snapshot(self) -> None:
        self.snapshot = None

    def record_match_result(self, player_won: bool) -> None:
        self.player_won = player_won


class AlwaysRaiseBot:
    def __init__(self, difficulty: Difficulty, rng=None) -> None:
        self.difficulty = difficulty
        self.rng = rng

    def should_request_raise(self, game: TrucoGame) -> bool:
        return True

    def respond_to_raise(self, game: TrucoGame) -> str:
        return "accept"

    def choose_card_index(self, game: TrucoGame) -> int:
        return 0


class TerminalInterfaceTestCase(unittest.TestCase):
    def test_opening_bot_turn_shows_player_hand_before_bot_acts(self) -> None:
        store = DummyStore()
        events: list[str] = []

        def output_fn(message: str) -> None:
            events.append(message)

        def input_fn(prompt: str) -> str:
            events.append(prompt)
            raise EOFError

        interface = TerminalInterface(store=store, input_fn=input_fn, output_fn=output_fn)
        game = TrucoGame(settings=MatchSettings(difficulty=Difficulty.INTERMEDIARIO))
        game.start_new_match()
        game.hand_starter = BOT
        game.current_player = BOT

        with patch("cli.interface.TrucoBot", AlwaysRaiseBot):
            interface.run_match(game)

        transcript = "\n".join(events)
        hand_index = transcript.index("Suas cartas atuais:")
        bot_turn_index = transcript.index("O computador esta analisando a melhor jogada.")

        self.assertLess(hand_index, bot_turn_index)
        self.assertIn("O computador pediu valor 3.", transcript)

    def test_raise_response_keeps_player_hand_next_to_decision_prompt(self) -> None:
        store = DummyStore()
        events: list[str] = []

        def output_fn(message: str) -> None:
            events.append(message)

        def input_fn(prompt: str) -> str:
            events.append(prompt)
            raise EOFError

        interface = TerminalInterface(store=store, input_fn=input_fn, output_fn=output_fn)
        game = TrucoGame(settings=MatchSettings(difficulty=Difficulty.INTERMEDIARIO))
        game.start_new_match()
        game.hand_starter = BOT
        game.current_player = BOT

        with patch("cli.interface.TrucoBot", AlwaysRaiseBot):
            interface.run_match(game)

        transcript = "\n".join(events)
        raise_history_index = transcript.rindex("- o computador pediu truco.")
        hand_index = transcript.rindex("Suas cartas atuais:")
        decision_prompt_index = transcript.rindex("O computador pediu valor 3.")

        self.assertLess(raise_history_index, hand_index)
        self.assertLess(hand_index, decision_prompt_index)

    def test_bot_turn_plays_after_accepted_raise_instead_of_chaining(self) -> None:
        store = DummyStore()
        interface = TerminalInterface(
            store=store,
            input_fn=lambda prompt: "",
            output_fn=lambda message: None,
        )
        game = TrucoGame(settings=MatchSettings(difficulty=Difficulty.INTERMEDIARIO))
        game.start_new_match()
        game.start_new_hand()
        game.current_player = BOT

        game.request_raise(BOT)
        game.accept_raise(PLAYER)
        interface._handle_bot_turn(game, AlwaysRaiseBot(Difficulty.INTERMEDIARIO))

        self.assertEqual(game.hand_value, 3)
        self.assertIsNone(game.pending_raise)
        self.assertEqual(len(game.hands[BOT]), 2)

    def test_player_can_check_current_points_without_playing(self) -> None:
        store = DummyStore()
        events: list[str] = []
        interface = TerminalInterface(
            store=store,
            input_fn=lambda prompt: "P",
            output_fn=events.append,
        )
        game = TrucoGame(settings=MatchSettings(difficulty=Difficulty.INTERMEDIARIO))
        game.start_new_match()
        game.start_new_hand()
        game.player_score = 4
        game.bot_score = 2
        game.hand_value = 3
        game.current_player = PLAYER

        interface._handle_player_turn(game)

        transcript = "\n".join(events)
        self.assertIn("=== Pontos Atuais ===", transcript)
        self.assertIn("Placar atual: voce 4 x 2 computador.", transcript)
        self.assertEqual(game.current_player, PLAYER)
        self.assertEqual(len(game.hands[PLAYER]), 3)

    def test_player_can_check_points_while_answering_raise(self) -> None:
        store = DummyStore()
        events: list[str] = []
        interface = TerminalInterface(
            store=store,
            input_fn=lambda prompt: "p",
            output_fn=events.append,
        )
        game = TrucoGame(settings=MatchSettings(difficulty=Difficulty.INTERMEDIARIO))
        game.start_new_match()
        game.start_new_hand()
        game.player_score = 6
        game.bot_score = 5
        game.current_player = BOT
        game.request_raise(BOT)

        interface._handle_player_raise_response(game)

        transcript = "\n".join(events)
        self.assertIn("[P] Ver pontos atuais", transcript)
        self.assertIn("Placar atual: voce 6 x 5 computador.", transcript)
        self.assertIsNotNone(game.pending_raise)
        self.assertEqual(game.hand_value, 1)

    def test_hand_over_message_includes_current_points(self) -> None:
        store = DummyStore()
        events: list[str] = []

        def input_fn(prompt: str) -> str:
            events.append(prompt)
            raise EOFError

        interface = TerminalInterface(store=store, input_fn=input_fn, output_fn=events.append)
        game = TrucoGame(settings=MatchSettings(difficulty=Difficulty.INTERMEDIARIO))
        game.start_new_match()
        game.start_new_hand()
        game.player_score = 4
        game.bot_score = 2
        game.surrender_hand(BOT)

        interface.run_match(game)

        transcript = "\n".join(events)
        self.assertIn("Mao encerrada.", transcript)
        self.assertIn("Placar atual: voce 5 x 2 computador.", transcript)


if __name__ == "__main__":
    unittest.main()
