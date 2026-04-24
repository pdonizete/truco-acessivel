from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random
from typing import Optional


class Suit(str, Enum):
    OUROS = "ouros"
    ESPADAS = "espadas"
    COPAS = "copas"
    PAUS = "paus"


RANKS: tuple[str, ...] = ("4", "5", "6", "7", "Q", "J", "K", "A", "2", "3")
SUITS: tuple[Suit, ...] = (
    Suit.OUROS,
    Suit.ESPADAS,
    Suit.COPAS,
    Suit.PAUS,
)

RANK_NAMES: dict[str, str] = {
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "Q": "Dama",
    "J": "Valete",
    "K": "Rei",
    "A": "As",
    "2": "2",
    "3": "3",
}


@dataclass(frozen=True, slots=True)
class Card:
    rank: str
    suit: Suit

    def __post_init__(self) -> None:
        if self.rank not in RANKS:
            raise ValueError(f"Valor de carta invalido: {self.rank}")

    @property
    def display_name(self) -> str:
        return f"{RANK_NAMES[self.rank]} de {self.suit.value}"

    def to_dict(self) -> dict[str, str]:
        return {"rank": self.rank, "suit": self.suit.value}

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Card":
        return cls(rank=data["rank"], suit=Suit(data["suit"]))

    def __str__(self) -> str:
        return self.display_name


def full_deck() -> list[Card]:
    return [Card(rank=rank, suit=suit) for suit in SUITS for rank in RANKS]


class Deck:
    def __init__(
        self,
        cards: Optional[list[Card]] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._rng = rng or random.Random()
        self.cards: list[Card] = list(cards) if cards is not None else full_deck()

    @classmethod
    def fresh_shuffled(cls, rng: Optional[random.Random] = None) -> "Deck":
        deck = cls(rng=rng)
        deck.shuffle()
        return deck

    def shuffle(self) -> None:
        self._rng.shuffle(self.cards)

    def draw(self, count: int = 1) -> list[Card]:
        if count < 1:
            raise ValueError("A quantidade de cartas compradas deve ser positiva.")
        if count > len(self.cards):
            raise ValueError("Nao ha cartas suficientes no baralho.")
        drawn = self.cards[:count]
        self.cards = self.cards[count:]
        return drawn
