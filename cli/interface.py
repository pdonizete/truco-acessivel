from __future__ import annotations

from pathlib import Path
import random
from typing import Callable, Optional

from ai.bot import Difficulty, TrucoBot
from cli.components import (
    format_hand,
    format_history,
    format_match_result,
    format_options,
    format_points_status,
    format_scoreboard,
    format_stats,
    format_table,
    separator,
)
from cli.tutorial import contextual_hint, explain_invalid_action, tutorial_intro
from core.persistence import ConfigStore
from core.rules import next_raise_value
from core.state import (
    BOT,
    PLAYER,
    GamePhase,
    InvalidMoveError,
    MatchSettings,
    TrucoGame,
)


class TerminalInterface:
    def __init__(
        self,
        store: ConfigStore,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ) -> None:
        self.store = store
        self.input_fn = input_fn
        self.output_fn = output_fn

    def run(self) -> None:
        while True:
            data = self.store.load()
            self._announce(separator("Menu Principal"))
            self._announce("Jogo de Truco Brasileiro em terminal.")
            options = [
                ("1", "Nova partida"),
                ("2", "Continuar partida salva"),
                ("3", "Nova partida com tutorial"),
                ("4", "Estatisticas e configuracoes"),
                ("5", "Sair"),
            ]
            self._announce(format_options(options))
            choice = self._prompt("Digite a opcao desejada").lower()
            if choice == "1":
                game = self._new_game(tutorial_mode=False)
                self.run_match(game)
            elif choice == "2":
                snapshot = data.get("partida_salva")
                if snapshot is None:
                    self._announce("Nao existe partida salva no momento.")
                else:
                    game = TrucoGame.from_dict(snapshot, rng=random.Random())
                    self.run_match(game)
            elif choice == "3":
                game = self._new_game(tutorial_mode=True)
                self.run_match(game)
            elif choice == "4":
                self._show_stats_and_settings()
            elif choice == "5":
                self._announce("Encerrando o jogo.")
                return
            else:
                self._announce("Opcao invalida. Escolha um numero do menu.")

    def run_match(self, game: TrucoGame) -> None:
        bot = TrucoBot(game.settings.difficulty, rng=game.rng)
        opening_hand_visible = False
        try:
            if game.phase == GamePhase.NEW_HAND:
                game.start_new_hand()
                self._save_snapshot(game)
                if game.settings.tutorial_mode:
                    self._announce(separator("Tutorial"))
                    self._announce(tutorial_intro())

            while not game.match_over:
                if game.phase == GamePhase.HAND_OVER:
                    self._render_state(game)
                    if game.hand_over_summary is not None:
                        self._announce(
                            f"Mao encerrada. {game.hand_over_summary.reason} "
                            f"Pontos recebidos: {game.hand_over_summary.points_awarded}.\n"
                            f"{format_points_status(game)}"
                        )
                    self._beep_if_enabled(game.settings.beep_enabled)
                    self._prompt("Pressione Enter para distribuir a proxima mao")
                    game.continue_after_hand()
                    opening_hand_visible = False
                    self._save_snapshot(game)
                    continue

                if game.phase == GamePhase.PLAYER_RESPONSE:
                    self._render_state(game)
                    opening_hand_visible = opening_hand_visible or self._is_opening_hand(game)
                    self._handle_player_raise_response(game)
                    self._save_snapshot(game)
                    continue

                if game.phase == GamePhase.PLAYER_TURN:
                    self._render_state(game)
                    opening_hand_visible = opening_hand_visible or self._is_opening_hand(game)
                    self._handle_player_turn(game)
                    self._save_snapshot(game)
                    continue

                if game.phase == GamePhase.BOT_TURN:
                    if self._is_opening_hand(game) and not opening_hand_visible:
                        self._announce("O computador abre a mao. Veja suas cartas antes da jogada dele.")
                        self._render_state(game)
                        opening_hand_visible = True
                    self._announce(separator("Turno do Computador"))
                    self._announce("O computador esta analisando a melhor jogada.")
                    self._handle_bot_turn(game, bot)
                    self._save_snapshot(game)
                    continue

            self.store.record_match_result(player_won=game.winner == PLAYER)
            self._announce(separator("Fim da Partida"))
            self._announce(format_match_result(game))
            self._beep_if_enabled(game.settings.beep_enabled)
            self._prompt("Pressione Enter para voltar ao menu principal")
        except KeyboardInterrupt:
            self._save_snapshot(game)
            self._announce("\nPartida interrompida pelo usuario. Progresso salvo.")
        except EOFError:
            self._save_snapshot(game)
            self._announce("\nEntrada encerrada. Progresso salvo.")

    def _render_state(self, game: TrucoGame) -> None:
        self._announce(separator("Estado Atual"))
        self._announce(format_scoreboard(game))
        self._announce(format_table(game))
        if game.phase == GamePhase.PLAYER_RESPONSE:
            self._announce(format_history(game.history))
            self._announce(format_hand(game.hands[PLAYER], game))
        else:
            self._announce(format_hand(game.hands[PLAYER], game))
            self._announce(format_history(game.history))
        if game.settings.tutorial_mode:
            self._announce(separator("Ajuda do Tutorial"))
            self._announce(contextual_hint(game))

    def _handle_player_turn(self, game: TrucoGame) -> None:
        options = [(str(index), f"Jogar {card.display_name}") for index, card in enumerate(game.hands[PLAYER], start=1)]
        if game.can_raise(PLAYER):
            next_value = next_raise_value(game.hand_value)
            options.append(("T", f"Pedir valor {next_value}"))
        options.append(("P", "Ver pontos atuais"))
        options.append(("F", "Correr da mao"))
        self._announce(format_options(options))
        choice = self._prompt("Escolha sua acao").upper()

        try:
            if choice == "T":
                game.request_raise(PLAYER)
                return
            if choice == "P":
                self._show_points_status(game)
                return
            if choice == "F":
                game.surrender_hand(PLAYER)
                return
            if choice.isdigit():
                game.play_card(PLAYER, int(choice) - 1)
                return
            raise InvalidMoveError("Opcao desconhecida para o turno atual.")
        except InvalidMoveError as error:
            self._announce(str(error))
            if game.settings.tutorial_mode:
                self._announce(explain_invalid_action(str(error)))

    def _handle_player_raise_response(self, game: TrucoGame) -> None:
        pending = game.pending_raise
        if pending is None:
            return
        next_value = next_raise_value(pending.requested_value)
        options = [("1", "Aceitar o pedido")]
        if next_value is not None:
            options.append(("2", f"Aumentar para {next_value}"))
            options.append(("3", "Correr"))
        else:
            options.append(("2", "Correr"))
        options.append(("P", "Ver pontos atuais"))
        self._announce(
            f"O computador pediu valor {pending.requested_value}. "
            "Voce precisa responder antes de jogar."
        )
        self._announce(format_options(options))
        choice = self._prompt("Escolha sua resposta")

        try:
            if choice == "1":
                game.accept_raise(PLAYER)
            elif choice.upper() == "P":
                self._show_points_status(game)
            elif choice == "2" and next_value is not None:
                game.escalate_raise(PLAYER)
            elif (choice == "2" and next_value is None) or (choice == "3" and next_value is not None):
                game.decline_raise(PLAYER)
            else:
                raise InvalidMoveError("Resposta invalida para o pedido.")
        except InvalidMoveError as error:
            self._announce(str(error))
            if game.settings.tutorial_mode:
                self._announce(explain_invalid_action(str(error)))

    def _handle_bot_turn(self, game: TrucoGame, bot: TrucoBot) -> None:
        if game.pending_raise is not None and game.pending_raise.responder == BOT:
            decision = bot.respond_to_raise(game)
            if decision == "raise":
                game.escalate_raise(BOT)
                return
            if decision == "decline":
                game.decline_raise(BOT)
                return
            game.accept_raise(BOT)
            return

        if game.can_raise(BOT) and bot.should_request_raise(game):
            game.request_raise(BOT)
            return

        card_index = bot.choose_card_index(game)
        if card_index < 0 or card_index >= len(game.hands[BOT]):
            card_index = 0
        game.play_card(BOT, card_index)

    def _is_opening_hand(self, game: TrucoGame) -> bool:
        return (
            game.vira is not None
            and len(game.hands[PLAYER]) == 3
            and len(game.hands[BOT]) == 3
            and not game.trick_history
            and not game.current_trick_cards
        )

    def _show_points_status(self, game: TrucoGame) -> None:
        self._announce(separator("Pontos Atuais"))
        self._announce(format_points_status(game))

    def _new_game(self, tutorial_mode: bool) -> TrucoGame:
        preferences = self.store.load()["preferencias"]
        difficulty = self._choose_difficulty(str(preferences["dificuldade_padrao"]))
        settings = MatchSettings(
            difficulty=difficulty,
            tutorial_mode=tutorial_mode,
            beep_enabled=bool(preferences["beep_habilitado"]),
        )
        game = TrucoGame(settings=settings, rng=random.Random())
        game.start_new_match()
        self.store.update_preferences(dificuldade_padrao=difficulty.value)
        return game

    def _choose_difficulty(self, default_value: str) -> Difficulty:
        self._announce(separator("Dificuldade"))
        self._announce(
            "Escolha a dificuldade da IA.\n"
            "[1] Iniciante\n"
            "[2] Intermediario\n"
            "[3] Expert\n"
            f"Dificuldade padrao atual: {default_value}"
        )
        mapping = {
            "1": Difficulty.INICIANTE,
            "2": Difficulty.INTERMEDIARIO,
            "3": Difficulty.EXPERT,
        }
        choice = self._prompt("Digite 1, 2 ou 3. Enter usa o padrao").strip()
        if not choice:
            return Difficulty(default_value)
        return mapping.get(choice, Difficulty(default_value))

    def _show_stats_and_settings(self) -> None:
        while True:
            data = self.store.load()
            self._announce(separator("Estatisticas e Configuracoes"))
            self._announce(format_stats(data))
            self._announce(
                "[1] Alternar beep\n"
                "[2] Alterar dificuldade padrao\n"
                "[3] Apagar partida salva\n"
                "[4] Voltar"
            )
            choice = self._prompt("Escolha uma opcao")
            if choice == "1":
                new_value = not bool(data["preferencias"]["beep_habilitado"])
                self.store.update_preferences(beep_habilitado=new_value)
            elif choice == "2":
                difficulty = self._choose_difficulty(
                    str(data["preferencias"]["dificuldade_padrao"])
                )
                self.store.update_preferences(dificuldade_padrao=difficulty.value)
            elif choice == "3":
                self.store.clear_match_snapshot()
                self._announce("Partida salva apagada.")
            elif choice == "4":
                return
            else:
                self._announce("Opcao invalida.")

    def _save_snapshot(self, game: TrucoGame) -> None:
        if game.match_over:
            self.store.clear_match_snapshot()
            return
        self.store.save_match_snapshot(game.to_dict())

    def _beep_if_enabled(self, enabled: bool) -> None:
        if enabled:
            self.output_fn("\a")

    def _prompt(self, message: str) -> str:
        return self.input_fn(f"{message}\n> ").strip()

    def _announce(self, message: str) -> None:
        self.output_fn(message)
