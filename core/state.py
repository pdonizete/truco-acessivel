from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import random
from typing import Optional

from ai.bot import Difficulty
from core.deck import Card, Deck
from core.rules import (
    TrickResolution,
    determine_hand_winner,
    determine_manilha_rank,
    determine_trick_winner,
    next_raise_value,
    next_trick_leader,
    refusal_points,
)


PLAYER = "jogador"
BOT = "computador"
MAX_POINTS = 12
HISTORY_LIMIT = 12


class GamePhase(str, Enum):
    NEW_HAND = "nova_mao"
    PLAYER_TURN = "turno_jogador"
    BOT_TURN = "turno_computador"
    PLAYER_RESPONSE = "resposta_jogador"
    HAND_OVER = "fim_da_mao"
    MATCH_OVER = "fim_da_partida"


class InvalidMoveError(ValueError):
    """Erro usado para manter a interface resiliente sem encerrar o jogo."""


@dataclass(slots=True)
class MatchSettings:
    difficulty: Difficulty = Difficulty.INTERMEDIARIO
    tutorial_mode: bool = False
    beep_enabled: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "difficulty": self.difficulty.value,
            "tutorial_mode": self.tutorial_mode,
            "beep_enabled": self.beep_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "MatchSettings":
        return cls(
            difficulty=Difficulty(str(data.get("difficulty", Difficulty.INTERMEDIARIO.value))),
            tutorial_mode=bool(data.get("tutorial_mode", False)),
            beep_enabled=bool(data.get("beep_enabled", False)),
        )


@dataclass(slots=True)
class RaiseRequest:
    requester: str
    responder: str
    requested_value: int

    def to_dict(self) -> dict[str, object]:
        return {
            "requester": self.requester,
            "responder": self.responder,
            "requested_value": self.requested_value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "RaiseRequest":
        return cls(
            requester=str(data["requester"]),
            responder=str(data["responder"]),
            requested_value=int(data["requested_value"]),
        )


@dataclass(slots=True)
class HandSummary:
    winner: str
    points_awarded: int
    reason: str


@dataclass(slots=True)
class TrucoGame:
    settings: MatchSettings
    rng: random.Random = field(default_factory=random.Random)
    player_score: int = 0
    bot_score: int = 0
    hand_starter: str = PLAYER
    current_player: str = PLAYER
    phase: GamePhase = GamePhase.NEW_HAND
    hand_value: int = 1
    hands: dict[str, list[Card]] = field(default_factory=lambda: {PLAYER: [], BOT: []})
    vira: Optional[Card] = None
    current_trick_cards: dict[str, Card] = field(default_factory=dict)
    trick_history: list[TrickResolution] = field(default_factory=list)
    history: list[str] = field(default_factory=list)
    pending_raise: Optional[RaiseRequest] = None
    last_raise_requester: Optional[str] = None
    last_raise_card_count: int = 0
    hand_over_summary: Optional[HandSummary] = None
    winner: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.history:
            self.add_history("Partida preparada. Escolha iniciar ou continuar.")

    @property
    def manilha_rank(self) -> str:
        if self.vira is None:
            raise InvalidMoveError("A mao ainda nao foi distribuida.")
        return determine_manilha_rank(self.vira)

    @property
    def match_over(self) -> bool:
        return self.phase == GamePhase.MATCH_OVER

    def other_player(self, player: str) -> str:
        return BOT if player == PLAYER else PLAYER

    def add_history(self, message: str) -> None:
        self.history.append(message)
        if len(self.history) > HISTORY_LIMIT:
            self.history = self.history[-HISTORY_LIMIT:]

    def start_new_match(self) -> None:
        self.player_score = 0
        self.bot_score = 0
        self.hand_starter = self.rng.choice([PLAYER, BOT])
        self.current_player = self.hand_starter
        self.phase = GamePhase.NEW_HAND
        self.hand_value = 1
        self.hands = {PLAYER: [], BOT: []}
        self.vira = None
        self.current_trick_cards = {}
        self.trick_history = []
        self.pending_raise = None
        self.last_raise_requester = None
        self.last_raise_card_count = 0
        self.hand_over_summary = None
        self.winner = None
        self.history = []
        self.add_history("Nova partida iniciada.")

    def start_new_hand(self) -> None:
        deck = Deck.fresh_shuffled(self.rng)
        self.hands = {
            PLAYER: deck.draw(3),
            BOT: deck.draw(3),
        }
        self.vira = deck.draw(1)[0]
        self.current_trick_cards = {}
        self.trick_history = []
        self.pending_raise = None
        self.last_raise_requester = None
        self.last_raise_card_count = 0
        self.hand_value = 1
        self.current_player = self.hand_starter
        self.hand_over_summary = None
        self.phase = self._phase_for_current_player()
        self.add_history(
            "Nova mao distribuida. "
            f"Vira: {self.vira.display_name}. Manilha: {self.manilha_rank}."
        )

    def can_raise(self, player: str) -> bool:
        if self.pending_raise is not None:
            return False
        if self.current_player != player:
            return False
        if next_raise_value(self.hand_value) is None:
            return False
        return not self._waiting_for_play_after_raise()

    def request_raise(self, player: str) -> int:
        if not self.can_raise(player):
            raise InvalidMoveError("Nao e possivel pedir truco neste momento.")
        requested_value = next_raise_value(self.hand_value)
        if requested_value is None:
            raise InvalidMoveError("A aposta da mao ja chegou ao maximo.")
        responder = self.other_player(player)
        self.pending_raise = RaiseRequest(
            requester=player,
            responder=responder,
            requested_value=requested_value,
        )
        self.last_raise_requester = player
        self.last_raise_card_count = self._played_card_count()
        self.phase = (
            GamePhase.PLAYER_RESPONSE if responder == PLAYER else GamePhase.BOT_TURN
        )
        pedido = self._raise_name(requested_value)
        self.add_history(f"{self._player_label(player)} pediu {pedido}.")
        return requested_value

    def accept_raise(self, player: str) -> None:
        if self.pending_raise is None or self.pending_raise.responder != player:
            raise InvalidMoveError("Nao ha pedido pendente para responder.")
        self.hand_value = self.pending_raise.requested_value
        pedido = self._raise_name(self.hand_value)
        self.add_history(f"{self._player_label(player)} aceitou {pedido}.")
        self.pending_raise = None
        self.phase = self._phase_for_current_player()

    def escalate_raise(self, player: str) -> int:
        if self.pending_raise is None or self.pending_raise.responder != player:
            raise InvalidMoveError("Nao ha pedido pendente para aumentar.")
        next_value = next_raise_value(self.pending_raise.requested_value)
        if next_value is None:
            raise InvalidMoveError("Nao ha aumento disponivel alem de 12.")
        requester = self.pending_raise.requester
        self.pending_raise = RaiseRequest(
            requester=player,
            responder=requester,
            requested_value=next_value,
        )
        self.last_raise_requester = player
        self.last_raise_card_count = self._played_card_count()
        self.phase = (
            GamePhase.PLAYER_RESPONSE if requester == PLAYER else GamePhase.BOT_TURN
        )
        pedido = self._raise_name(next_value)
        self.add_history(f"{self._player_label(player)} aumentou para {pedido}.")
        return next_value

    def decline_raise(self, player: str) -> HandSummary:
        if self.pending_raise is None or self.pending_raise.responder != player:
            raise InvalidMoveError("Nao ha pedido pendente para correr.")
        winner = self.pending_raise.requester
        points = refusal_points(self.pending_raise.requested_value)
        self.pending_raise = None
        return self._finish_hand(
            winner=winner,
            points=points,
            reason=f"{self._player_label(player)} correu do pedido.",
        )

    def surrender_hand(self, player: str) -> HandSummary:
        if self.match_over:
            raise InvalidMoveError("A partida ja terminou.")
        winner = self.other_player(player)
        return self._finish_hand(
            winner=winner,
            points=self.hand_value,
            reason=f"{self._player_label(player)} correu da mao.",
        )

    def play_card(self, player: str, hand_index: int) -> Optional[HandSummary]:
        if self.match_over:
            raise InvalidMoveError("A partida ja terminou.")
        if self.pending_raise is not None:
            raise InvalidMoveError("Responda ao pedido pendente antes de jogar.")
        if self.current_player != player:
            raise InvalidMoveError("Ainda nao e a vez desse jogador.")
        hand = self.hands[player]
        if hand_index < 0 or hand_index >= len(hand):
            raise InvalidMoveError("Indice de carta invalido.")
        card = hand.pop(hand_index)
        self.current_trick_cards[player] = card
        self.add_history(f"{self._player_label(player)} jogou {card.display_name}.")

        if len(self.current_trick_cards) == 1:
            self.current_player = self.other_player(player)
            self.phase = self._phase_for_current_player()
            return None

        if self.vira is None:
            raise InvalidMoveError("A vira nao foi definida.")
        winner = determine_trick_winner(self.current_trick_cards, self.vira)
        trick_number = len(self.trick_history) + 1
        if winner is None:
            description = f"Rodada {trick_number} empatou."
        else:
            description = f"Rodada {trick_number} vencida por {self._player_label(winner)}."
        resolution = TrickResolution(
            winner=winner,
            cards=dict(self.current_trick_cards),
            description=description,
        )
        self.trick_history.append(resolution)
        self.add_history(description)
        self.current_trick_cards = {}

        hand_winner = determine_hand_winner(
            [trick.winner for trick in self.trick_history],
            self.hand_starter,
        )
        if hand_winner is not None:
            return self._finish_hand(
                winner=hand_winner,
                points=self.hand_value,
                reason=f"{self._player_label(hand_winner)} venceu a mao.",
            )

        if len(self.trick_history) == 3:
            winner = determine_hand_winner(
                [trick.winner for trick in self.trick_history],
                self.hand_starter,
            )
            if winner is None:
                winner = self.hand_starter
            return self._finish_hand(
                winner=winner,
                points=self.hand_value,
                reason="Tres rodadas encerradas.",
            )

        self.current_player = next_trick_leader(
            [trick.winner for trick in self.trick_history],
            self.hand_starter,
        )
        self.phase = self._phase_for_current_player()
        return None

    def continue_after_hand(self) -> None:
        if self.phase == GamePhase.MATCH_OVER:
            return
        if self.phase != GamePhase.HAND_OVER:
            raise InvalidMoveError("A mao atual ainda nao terminou.")
        self.hand_starter = self.other_player(self.hand_starter)
        self.start_new_hand()

    def _finish_hand(self, winner: str, points: int, reason: str) -> HandSummary:
        self.pending_raise = None
        self.current_trick_cards = {}
        self.last_raise_requester = None
        self.last_raise_card_count = 0
        if winner == PLAYER:
            self.player_score += points
        else:
            self.bot_score += points
        summary = HandSummary(winner=winner, points_awarded=points, reason=reason)
        self.hand_over_summary = summary
        self.add_history(f"{reason} {self._player_label(winner)} recebeu {points} ponto(s).")
        if self.player_score >= MAX_POINTS or self.bot_score >= MAX_POINTS:
            self.phase = GamePhase.MATCH_OVER
            self.winner = winner
            self.add_history(f"Partida encerrada com vitoria de {self._player_label(winner)}.")
        else:
            self.phase = GamePhase.HAND_OVER
        return summary

    def _player_label(self, player: str) -> str:
        return "voce" if player == PLAYER else "o computador"

    def _played_card_count(self) -> int:
        return sum(3 - len(hand) for hand in self.hands.values())

    def _waiting_for_play_after_raise(self) -> bool:
        return (
            self.last_raise_requester is not None
            and self.last_raise_card_count == self._played_card_count()
        )

    def _phase_for_current_player(self) -> GamePhase:
        return GamePhase.PLAYER_TURN if self.current_player == PLAYER else GamePhase.BOT_TURN

    def _normalize_active_phase(self) -> None:
        if self.phase in (GamePhase.NEW_HAND, GamePhase.HAND_OVER, GamePhase.MATCH_OVER):
            return
        if self.pending_raise is not None:
            self.phase = (
                GamePhase.PLAYER_RESPONSE
                if self.pending_raise.responder == PLAYER
                else GamePhase.BOT_TURN
            )
            return
        self.phase = self._phase_for_current_player()

    def _raise_name(self, hand_value: int) -> str:
        mapping = {
            3: "truco",
            6: "seis",
            9: "nove",
            12: "doze",
        }
        return mapping.get(hand_value, str(hand_value))

    def to_dict(self) -> dict[str, object]:
        return {
            "settings": self.settings.to_dict(),
            "player_score": self.player_score,
            "bot_score": self.bot_score,
            "hand_starter": self.hand_starter,
            "current_player": self.current_player,
            "phase": self.phase.value,
            "hand_value": self.hand_value,
            "hands": {
                player: [card.to_dict() for card in cards]
                for player, cards in self.hands.items()
            },
            "vira": self.vira.to_dict() if self.vira is not None else None,
            "current_trick_cards": {
                player: card.to_dict() for player, card in self.current_trick_cards.items()
            },
            "trick_history": [
                {
                    "winner": trick.winner,
                    "cards": {
                        player: card.to_dict() for player, card in trick.cards.items()
                    },
                    "description": trick.description,
                }
                for trick in self.trick_history
            ],
            "history": list(self.history),
            "pending_raise": self.pending_raise.to_dict() if self.pending_raise else None,
            "last_raise_requester": self.last_raise_requester,
            "last_raise_card_count": self.last_raise_card_count,
            "hand_over_summary": (
                {
                    "winner": self.hand_over_summary.winner,
                    "points_awarded": self.hand_over_summary.points_awarded,
                    "reason": self.hand_over_summary.reason,
                }
                if self.hand_over_summary
                else None
            ),
            "winner": self.winner,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
        rng: Optional[random.Random] = None,
    ) -> "TrucoGame":
        game = cls(
            settings=MatchSettings.from_dict(dict(data["settings"])),
            rng=rng or random.Random(),
        )
        game.player_score = int(data["player_score"])
        game.bot_score = int(data["bot_score"])
        game.hand_starter = str(data["hand_starter"])
        game.current_player = str(data["current_player"])
        game.phase = GamePhase(str(data["phase"]))
        game.hand_value = int(data["hand_value"])
        hands_data = dict(data["hands"])
        game.hands = {
            player: [Card.from_dict(card) for card in cards]
            for player, cards in hands_data.items()
        }
        vira_data = data.get("vira")
        game.vira = Card.from_dict(vira_data) if vira_data else None
        current_trick_data = dict(data.get("current_trick_cards", {}))
        game.current_trick_cards = {
            player: Card.from_dict(card) for player, card in current_trick_data.items()
        }
        game.trick_history = [
            TrickResolution(
                winner=trick["winner"],
                cards={
                    player: Card.from_dict(card)
                    for player, card in dict(trick["cards"]).items()
                },
                description=str(trick["description"]),
            )
            for trick in list(data.get("trick_history", []))
        ]
        game.history = list(data.get("history", []))
        pending_raise_data = data.get("pending_raise")
        game.pending_raise = (
            RaiseRequest.from_dict(dict(pending_raise_data))
            if pending_raise_data
            else None
        )
        game.last_raise_requester = (
            str(data["last_raise_requester"])
            if data.get("last_raise_requester") is not None
            else None
        )
        game.last_raise_card_count = int(data.get("last_raise_card_count", 0))
        hand_over_summary = data.get("hand_over_summary")
        game.hand_over_summary = (
            HandSummary(
                winner=str(hand_over_summary["winner"]),
                points_awarded=int(hand_over_summary["points_awarded"]),
                reason=str(hand_over_summary["reason"]),
            )
            if hand_over_summary
            else None
        )
        game.winner = data.get("winner")
        game._normalize_active_phase()
        return game
