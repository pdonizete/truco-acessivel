from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Optional

from core.deck import Card, RANKS, Suit, full_deck


MANILHA_SUIT_STRENGTH: dict[Suit, int] = {
    Suit.OUROS: 0,
    Suit.ESPADAS: 1,
    Suit.COPAS: 2,
    Suit.PAUS: 3,
}
HAND_VALUE_SEQUENCE: tuple[int, ...] = (1, 3, 6, 9, 12)


@dataclass(frozen=True, slots=True)
class TrickResolution:
    winner: Optional[str]
    cards: dict[str, Card]
    description: str


def next_rank(rank: str) -> str:
    if rank not in RANKS:
        raise ValueError(f"Valor de carta invalido: {rank}")
    index = RANKS.index(rank)
    return RANKS[(index + 1) % len(RANKS)]


def determine_manilha_rank(vira: Card) -> str:
    return next_rank(vira.rank)


def is_manilha(card: Card, vira: Card) -> bool:
    return card.rank == determine_manilha_rank(vira)


def non_manilha_strength(card: Card) -> int:
    return RANKS.index(card.rank)


def card_strength(card: Card, vira: Card) -> tuple[int, int]:
    if is_manilha(card, vira):
        return (100, MANILHA_SUIT_STRENGTH[card.suit])
    return (non_manilha_strength(card), -1)


def compare_cards(first: Card, second: Card, vira: Card) -> int:
    first_strength = card_strength(first, vira)
    second_strength = card_strength(second, vira)
    if first_strength > second_strength:
        return 1
    if first_strength < second_strength:
        return -1
    return 0


def determine_trick_winner(cards: dict[str, Card], vira: Card) -> Optional[str]:
    if len(cards) != 2:
        raise ValueError("A rodada precisa conter exatamente duas cartas.")
    players = list(cards.keys())
    result = compare_cards(cards[players[0]], cards[players[1]], vira)
    if result == 0:
        return None
    return players[0] if result > 0 else players[1]


def describe_card(card: Card, vira: Card) -> str:
    if is_manilha(card, vira):
        return (
            f"{card.display_name} e manilha. "
            f"Forca relativa do naipe: {MANILHA_SUIT_STRENGTH[card.suit] + 1}."
        )
    return f"{card.display_name} tem forca base {non_manilha_strength(card) + 1}."


def next_raise_value(current_hand_value: int) -> Optional[int]:
    try:
        index = HAND_VALUE_SEQUENCE.index(current_hand_value)
    except ValueError as exc:
        raise ValueError("Valor atual da mao invalido.") from exc
    if index == len(HAND_VALUE_SEQUENCE) - 1:
        return None
    return HAND_VALUE_SEQUENCE[index + 1]


def refusal_points(requested_hand_value: int) -> int:
    try:
        index = HAND_VALUE_SEQUENCE.index(requested_hand_value)
    except ValueError as exc:
        raise ValueError("Valor pedido invalido.") from exc
    if index == 0:
        return HAND_VALUE_SEQUENCE[0]
    return HAND_VALUE_SEQUENCE[index - 1]


def determine_hand_winner(
    trick_winners: list[Optional[str]],
    hand_starter: str,
) -> Optional[str]:
    if not trick_winners:
        return None

    first = trick_winners[0]
    if len(trick_winners) == 1:
        return None

    second = trick_winners[1]
    if first == second and first is not None:
        return first
    if first is not None and second is None:
        return first
    if first is None and second is not None:
        return second
    if first is None and second is None:
        if len(trick_winners) < 3:
            return None
        return trick_winners[2] or hand_starter

    if len(trick_winners) < 3:
        return None

    third = trick_winners[2]
    if third is None:
        return first
    return third


def next_trick_leader(
    trick_winners: list[Optional[str]],
    hand_starter: str,
) -> str:
    if not trick_winners:
        return hand_starter
    last_winner = trick_winners[-1]
    if last_winner is not None:
        return last_winner
    if len(trick_winners) == 1:
        return hand_starter
    if len(trick_winners) == 2 and trick_winners[0] is not None:
        return trick_winners[0]
    return hand_starter


def remaining_cards(known_cards: Iterable[Card]) -> list[Card]:
    known_set = set(known_cards)
    return [card for card in full_deck() if card not in known_set]


def probability_card_beats_random_hand(
    card: Card,
    vira: Card,
    unseen_cards: list[Card],
    opponent_cards: int,
) -> float:
    if opponent_cards <= 0:
        return 1.0
    total_cards = len(unseen_cards)
    if total_cards == 0:
        return 1.0
    beating_cards = sum(
        1 for unseen_card in unseen_cards if compare_cards(unseen_card, card, vira) > 0
    )
    safe_cards = total_cards - beating_cards
    if opponent_cards > total_cards:
        opponent_cards = total_cards
    total_combinations = math.comb(total_cards, opponent_cards)
    safe_combinations = math.comb(safe_cards, opponent_cards) if safe_cards >= opponent_cards else 0
    if total_combinations == 0:
        return 1.0
    return safe_combinations / total_combinations
