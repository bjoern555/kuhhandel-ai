"""Data structures for the physical pieces of Kuhhandel (You're Bluffing!)."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Animal cards
# ---------------------------------------------------------------------------

class AnimalType(Enum):
    """Every animal type in the game, paired with its quartet point value."""

    ROOSTER = ("Rooster", 10)
    GOOSE = ("Goose", 40)
    CAT = ("Cat", 90)
    DOG = ("Dog", 160)
    SHEEP = ("Sheep", 250)
    GOAT = ("Goat", 350)
    DONKEY = ("Donkey", 500)
    PIG = ("Pig", 650)
    COW = ("Cow", 800)
    HORSE = ("Horse", 1000)

    def __init__(self, animal_name: str, quartet_value: int) -> None:
        self.animal_name = animal_name
        self.quartet_value = quartet_value


@dataclass(frozen=True)
class AnimalCard:
    """A single animal card.

    Attributes:
        animal_type: The type of animal on this card.
    """

    animal_type: AnimalType

    @property
    def name(self) -> str:
        return self.animal_type.animal_name

    @property
    def quartet_value(self) -> int:
        return self.animal_type.quartet_value

    def __repr__(self) -> str:
        return f"AnimalCard({self.name}, {self.quartet_value}pts)"


# ---------------------------------------------------------------------------
# Money cards
# ---------------------------------------------------------------------------

class MoneyValue(Enum):
    """Valid denominations for money cards."""

    ZERO = 0
    TEN = 10
    FIFTY = 50
    HUNDRED = 100
    TWO_HUNDRED = 200
    FIVE_HUNDRED = 500


@dataclass(frozen=True)
class MoneyCard:
    """A single money card.

    Attributes:
        value: The face value of this card (one of the valid denominations).
    """

    value: MoneyValue

    @property
    def amount(self) -> int:
        return self.value.value

    def __repr__(self) -> str:
        return f"MoneyCard({self.amount})"


# ---------------------------------------------------------------------------
# Deck (animal draw pile)
# ---------------------------------------------------------------------------

class Deck:
    """The 40-card animal draw pile.

    Initializes one card per animal type x 4 copies, supports shuffling
    and drawing from the top.
    """

    CARDS_PER_ANIMAL: int = 4

    def __init__(self) -> None:
        self._cards: list[AnimalCard] = [
            AnimalCard(animal_type=animal)
            for animal in AnimalType
            for _ in range(self.CARDS_PER_ANIMAL)
        ]

    def shuffle(self) -> None:
        """Randomly shuffle the draw pile in place."""
        random.shuffle(self._cards)

    def draw(self) -> Optional[AnimalCard]:
        """Remove and return the top card, or None if the deck is empty."""
        if not self._cards:
            return None
        return self._cards.pop()

    @property
    def remaining(self) -> int:
        return len(self._cards)

    def __len__(self) -> int:
        return self.remaining

    def __repr__(self) -> str:
        return f"Deck({self.remaining} cards remaining)"


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

@dataclass
class Player:
    """A player in the game.

    Attributes:
        name: Display name for this player.
        animals: Publicly visible collection of won animal cards.
        money: Hidden hand of money cards (private information).
    """

    name: str
    animals: list[AnimalCard] = field(default_factory=list)
    money: list[MoneyCard] = field(default_factory=list)

    @property
    def total_money(self) -> int:
        """Sum of all money card values in hand."""
        return sum(card.amount for card in self.money)

    def add_money(self, cards: list[MoneyCard]) -> None:
        """Add one or more money cards to the player's hidden hand."""
        self.money.extend(cards)

    def remove_money(self, cards: list[MoneyCard]) -> None:
        """Remove specific money cards from the player's hand.

        Raises:
            ValueError: If a card to remove is not in the player's hand.
        """
        for card in cards:
            self.money.remove(card)

    def add_animal(self, card: AnimalCard) -> None:
        """Add an animal card to the player's public inventory."""
        self.animals.append(card)

    def has_animal(self, animal_type: AnimalType) -> bool:
        """Check whether the player owns at least one card of the given type."""
        return any(c.animal_type is animal_type for c in self.animals)

    def __repr__(self) -> str:
        return (
            f"Player({self.name}, "
            f"{len(self.animals)} animals, "
            f"{len(self.money)} money cards)"
        )
