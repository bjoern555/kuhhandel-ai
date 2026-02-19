"""Top-level game state for a Kuhhandel session."""

from __future__ import annotations

from engine.models import Deck, MoneyCard, MoneyValue, Player

MIN_PLAYERS: int = 3
MAX_PLAYERS: int = 5

# Every player starts with exactly these seven money cards.
STARTING_MONEY: list[MoneyValue] = (
    [MoneyValue.ZERO] * 2
    + [MoneyValue.TEN] * 4
    + [MoneyValue.FIFTY] * 1
)


class Game:
    """Manages the shared state of a Kuhhandel game.

    Attributes:
        deck: The animal draw pile.
        players: Participating players (3-5).
        current_turn: Index of the player whose turn it is.
    """

    def __init__(self, players: list[Player]) -> None:
        if not MIN_PLAYERS <= len(players) <= MAX_PLAYERS:
            raise ValueError(
                f"Kuhhandel requires {MIN_PLAYERS}-{MAX_PLAYERS} players, "
                f"got {len(players)}"
            )
        self.deck: Deck = Deck()
        self.deck.shuffle()
        self.players: list[Player] = players
        self.current_turn: int = 0

    def deal_starting_money(self) -> None:
        """Give every player their seven starting money cards (2x0, 4x10, 1x50)."""
        for player in self.players:
            player.add_money([MoneyCard(v) for v in STARTING_MONEY])

    def __repr__(self) -> str:
        lines: list[str] = [
            f"=== Kuhhandel Game ===",
            f"Turn: Player {self.current_turn} ({self.players[self.current_turn].name})",
            f"Deck: {self.deck.remaining} cards remaining",
            f"",
            f"--- Player Inventories ---",
        ]
        for i, player in enumerate(self.players):
            animal_names = [card.name for card in player.animals]
            lines.append(
                f"  [{i}] {player.name}: {animal_names if animal_names else '(none)'}"
            )
        return "\n".join(lines)
