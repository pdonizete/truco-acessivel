from __future__ import annotations

from enum import Enum
import random
from typing import TYPE_CHECKING

from core.deck import Card
from core.rules import (
    card_strength,
    compare_cards,
    is_manilha,
    next_raise_value,
    probability_card_beats_random_hand,
    remaining_cards,
)

if TYPE_CHECKING:
    from core.state import TrucoGame


class Difficulty(str, Enum):
    INICIANTE = "iniciante"
    INTERMEDIARIO = "intermediario"
    EXPERT = "expert"


class TrucoBot:
    def __init__(
        self,
        difficulty: Difficulty = Difficulty.INTERMEDIARIO,
        rng: random.Random | None = None,
    ) -> None:
        self.difficulty = difficulty
        self.rng = rng or random.Random()

    def choose_card_index(self, game: "TrucoGame") -> int:
        hand = game.hands["computador"]
        if not hand:
            return 0

        if self.difficulty == Difficulty.INICIANTE:
            return self._choose_beginner_card(game)
        if self.difficulty == Difficulty.INTERMEDIARIO:
            return self._choose_intermediate_card(game)
        return self._choose_expert_card(game)

    def should_request_raise(self, game: "TrucoGame") -> bool:
        if not game.can_raise("computador"):
            return False
        next_value = next_raise_value(game.hand_value)
        if next_value is None:
            return False
        confidence = self._hand_confidence(game)
        thresholds = {
            Difficulty.INICIANTE: {3: 0.83, 6: 0.94, 9: 0.99, 12: 1.01},
            Difficulty.INTERMEDIARIO: {3: 0.70, 6: 0.82, 9: 0.91, 12: 0.98},
            Difficulty.EXPERT: {3: 0.60, 6: 0.74, 9: 0.84, 12: 0.93},
        }[self.difficulty]
        threshold = thresholds[next_value]
        behind_bonus = 0.06 if game.player_score > game.bot_score else 0.0
        match_point_bonus = 0.05 if game.bot_score + next_value >= 12 else 0.0
        bluff_chance = {
            Difficulty.INICIANTE: 0.03,
            Difficulty.INTERMEDIARIO: 0.07,
            Difficulty.EXPERT: 0.10,
        }[self.difficulty]
        if game.hand_value > 1:
            bluff_chance *= 0.25 if next_value == 6 else 0.0
        pressure_bonus = behind_bonus + match_point_bonus
        if confidence >= threshold - pressure_bonus:
            return True
        return confidence >= 0.35 and self.rng.random() < bluff_chance + pressure_bonus / 2

    def respond_to_raise(self, game: "TrucoGame") -> str:
        if game.pending_raise is None:
            return "accept"
        confidence = self._hand_confidence(game)
        requested_value = game.pending_raise.requested_value
        accept_thresholds = {
            Difficulty.INICIANTE: {3: 0.53, 6: 0.69, 9: 0.80, 12: 0.90},
            Difficulty.INTERMEDIARIO: {3: 0.44, 6: 0.58, 9: 0.74, 12: 0.86},
            Difficulty.EXPERT: {3: 0.35, 6: 0.48, 9: 0.64, 12: 0.77},
        }
        raise_thresholds = {
            Difficulty.INICIANTE: {3: 0.93, 6: 0.99, 9: 9.99, 12: 9.99},
            Difficulty.INTERMEDIARIO: {3: 0.85, 6: 0.93, 9: 9.99, 12: 9.99},
            Difficulty.EXPERT: {3: 0.76, 6: 0.84, 9: 0.92, 12: 9.99},
        }
        next_value = next_raise_value(requested_value)
        pressure_bonus = 0.06 if game.player_score >= 9 else 0.0
        if (
            next_value is not None
            and confidence >= raise_thresholds[self.difficulty][requested_value] - pressure_bonus
        ):
            return "raise"
        if confidence >= accept_thresholds[self.difficulty][requested_value] - pressure_bonus:
            return "accept"
        desperation = 0.10 if game.bot_score + requested_value >= 12 else 0.0
        if confidence >= accept_thresholds[self.difficulty][requested_value] - (pressure_bonus + desperation):
            return "accept"
        return "decline"

    def _choose_beginner_card(self, game: "TrucoGame") -> int:
        hand = game.hands["computador"]
        if "jogador" in game.current_trick_cards:
            beating_indices = [
                index
                for index, card in enumerate(hand)
                if compare_cards(card, game.current_trick_cards["jogador"], game.vira) > 0
            ]
            if beating_indices and self.rng.random() < 0.45:
                return min(
                    beating_indices,
                    key=lambda idx: card_strength(hand[idx], game.vira),
                )
        return self.rng.randrange(len(hand))

    def _choose_intermediate_card(self, game: "TrucoGame") -> int:
        hand = game.hands["computador"]
        if "jogador" in game.current_trick_cards:
            target = game.current_trick_cards["jogador"]
            beating_indices = [
                index
                for index, card in enumerate(hand)
                if compare_cards(card, target, game.vira) > 0
            ]
            if beating_indices:
                return min(
                    beating_indices,
                    key=lambda idx: card_strength(hand[idx], game.vira),
                )
            return min(range(len(hand)), key=lambda idx: card_strength(hand[idx], game.vira))

        bot_wins = sum(1 for trick in game.trick_history if trick.winner == "computador")
        player_wins = sum(1 for trick in game.trick_history if trick.winner == "jogador")
        ordered_indices = sorted(range(len(hand)), key=lambda idx: card_strength(hand[idx], game.vira))
        if bot_wins > player_wins:
            return ordered_indices[0]
        if player_wins > bot_wins:
            return ordered_indices[-1]
        middle = len(ordered_indices) // 2
        return ordered_indices[middle]

    def _choose_expert_card(self, game: "TrucoGame") -> int:
        hand = game.hands["computador"]
        unseen_cards = self._unseen_cards(game)
        opponent_cards = len(game.hands["jogador"])
        bot_wins = sum(1 for trick in game.trick_history if trick.winner == "computador")
        player_wins = sum(1 for trick in game.trick_history if trick.winner == "jogador")

        best_score = float("-inf")
        best_index = 0
        for index, card in enumerate(hand):
            immediate = self._immediate_play_value(game, card, unseen_cards, opponent_cards)
            remaining_hand = [candidate for pos, candidate in enumerate(hand) if pos != index]
            preserved = self._remaining_hand_quality(game, remaining_hand, unseen_cards)
            normalized_strength = self._normalized_strength(card, game)

            score = (immediate * 0.65) + (preserved * 0.35)
            if bot_wins > player_wins:
                score -= normalized_strength * 0.15
            elif player_wins > bot_wins:
                score += normalized_strength * 0.12
            if is_manilha(card, game.vira) and bot_wins == player_wins:
                score -= 0.05

            if score > best_score:
                best_score = score
                best_index = index
        return best_index

    def _hand_confidence(self, game: "TrucoGame") -> float:
        hand = game.hands["computador"]
        if not hand or game.vira is None:
            return 0.0
        unseen_cards = self._unseen_cards(game)
        opponent_cards = len(game.hands["jogador"])
        survival_scores = [
            probability_card_beats_random_hand(card, game.vira, unseen_cards, opponent_cards)
            for card in hand
        ]
        strength_scores = [self._normalized_strength(card, game) for card in hand]
        combined = [
            (survival * 0.65) + (strength * 0.35)
            for survival, strength in zip(survival_scores, strength_scores)
        ]
        combined.sort(reverse=True)
        base = 0.0
        weights = (0.5, 0.3, 0.2)
        for weight, score in zip(weights, combined):
            base += weight * score

        bot_wins = sum(1 for trick in game.trick_history if trick.winner == "computador")
        player_wins = sum(1 for trick in game.trick_history if trick.winner == "jogador")
        state_bonus = 0.0
        if bot_wins > player_wins:
            state_bonus += 0.10
        elif player_wins > bot_wins:
            state_bonus -= 0.08
        score_context = (game.bot_score - game.player_score) / 12
        return max(0.0, min(1.0, base + state_bonus + (score_context * 0.05)))

    def _immediate_play_value(
        self,
        game: "TrucoGame",
        card: Card,
        unseen_cards: list[Card],
        opponent_cards: int,
    ) -> float:
        if "jogador" in game.current_trick_cards:
            comparison = compare_cards(card, game.current_trick_cards["jogador"], game.vira)
            if comparison > 0:
                return 1.0
            if comparison == 0:
                return 0.55
            return 0.05
        return probability_card_beats_random_hand(card, game.vira, unseen_cards, opponent_cards)

    def _remaining_hand_quality(
        self,
        game: "TrucoGame",
        remaining_hand: list[Card],
        unseen_cards: list[Card],
    ) -> float:
        if not remaining_hand:
            return 0.0
        opponent_cards = max(0, len(game.hands["jogador"]) - 1)
        values = [
            probability_card_beats_random_hand(card, game.vira, unseen_cards, opponent_cards)
            for card in remaining_hand
        ]
        return sum(values) / len(values)

    def _unseen_cards(self, game: "TrucoGame") -> list[Card]:
        known_cards: list[Card] = []
        if game.vira is not None:
            known_cards.append(game.vira)
        known_cards.extend(game.hands["computador"])
        known_cards.extend(game.current_trick_cards.values())
        for trick in game.trick_history:
            known_cards.extend(trick.cards.values())
        return remaining_cards(known_cards)

    def _normalized_strength(self, card: Card, game: "TrucoGame") -> float:
        primary, secondary = card_strength(card, game.vira)
        if primary >= 100:
            return 0.82 + (secondary * 0.06)
        return (primary + 1) / 12
