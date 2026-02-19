"""Top-level game state for a Kuhhandel session."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from engine.models import AnimalCard, Deck, MoneyCard, MoneyValue, Player

MIN_PLAYERS: int = 3
MAX_PLAYERS: int = 5

# Every player starts with exactly these seven money cards.
STARTING_MONEY: list[MoneyValue] = (
    [MoneyValue.ZERO] * 2
    + [MoneyValue.TEN] * 4
    + [MoneyValue.FIFTY] * 1
)


# ---------------------------------------------------------------------------
# State‑machine phases
# ---------------------------------------------------------------------------

class GamePhase(Enum):
    """Discrete phases the game can be in (state‑machine friendly)."""

    TURN_START = auto()
    AUCTION_BIDDING = auto()
    AUCTION_WON = auto()


# ---------------------------------------------------------------------------
# Auction tracking
# ---------------------------------------------------------------------------

@dataclass
class AuctionState:
    """Snapshot of an in‑progress auction.

    Attributes:
        card: The animal card being auctioned.
        auctioneer_index: Player who drew the card and opened the auction.
        highest_bid: Current top bid (0 means no bids yet).
        highest_bidder_index: Player who placed the top bid, or None.
        active_bidders: Indices of players still eligible to bid/pass.
    """

    card: AnimalCard
    auctioneer_index: int
    highest_bid: int = 0
    highest_bidder_index: Optional[int] = None
    active_bidders: list[int] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------

class Game:
    """Manages the shared state of a Kuhhandel game.

    Attributes:
        deck: The animal draw pile.
        players: Participating players (3-5).
        current_turn: Index of the player whose turn it is.
        phase: Current state‑machine phase.
        current_auction: Active auction data, or None.
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
        self.phase: GamePhase = GamePhase.TURN_START
        self.current_auction: Optional[AuctionState] = None

    # ── setup ──────────────────────────────────────────────────────────

    def deal_starting_money(self) -> None:
        """Give every player their seven starting money cards (2x0, 4x10, 1x50)."""
        for player in self.players:
            player.add_money([MoneyCard(v) for v in STARTING_MONEY])

    # ── auction flow ───────────────────────────────────────────────────

    def draw_for_auction(self) -> AnimalCard:
        """The turn player draws a card and opens an auction.

        Returns:
            The drawn AnimalCard.

        Raises:
            RuntimeError: If the phase is not TURN_START or the deck is empty.
        """
        if self.phase is not GamePhase.TURN_START:
            raise RuntimeError(
                f"Cannot draw: phase is {self.phase.name}, expected TURN_START"
            )
        card = self.deck.draw()
        if card is None:
            raise RuntimeError("Cannot draw: deck is empty")

        bidders = [
            i for i in range(len(self.players))
            if i != self.current_turn
        ]
        self.current_auction = AuctionState(
            card=card,
            auctioneer_index=self.current_turn,
            active_bidders=bidders,
        )
        self.phase = GamePhase.AUCTION_BIDDING
        return card

    def process_bid(self, player_index: int, amount: int) -> None:
        """Register a bid from a player.

        Raises:
            RuntimeError: If no auction is active.
            ValueError: If the bid is invalid (wrong phase, player not
                eligible, amount not a multiple of 10, or not strictly
                higher than the current bid).
        """
        auction = self._require_auction()

        if player_index not in auction.active_bidders:
            raise ValueError(
                f"Player {player_index} is not an active bidder"
            )
        if amount % 10 != 0:
            raise ValueError(
                f"Bid {amount} is not a multiple of 10"
            )
        if amount <= auction.highest_bid:
            raise ValueError(
                f"Bid {amount} must be strictly higher than "
                f"current bid {auction.highest_bid}"
            )

        auction.highest_bid = amount
        auction.highest_bidder_index = player_index

    def pass_auction(self, player_index: int) -> None:
        """A player passes (drops out of the auction).

        If only one bidder remains after the pass, the auction is won.

        Raises:
            RuntimeError: If no auction is active.
            ValueError: If the player is not an active bidder.
        """
        auction = self._require_auction()

        if player_index not in auction.active_bidders:
            raise ValueError(
                f"Player {player_index} is not an active bidder"
            )

        auction.active_bidders.remove(player_index)

        if len(auction.active_bidders) == 1:
            # Last bidder standing wins
            auction.highest_bidder_index = auction.active_bidders[0]
            self.phase = GamePhase.AUCTION_WON

    # ── helpers ────────────────────────────────────────────────────────

    def _require_auction(self) -> AuctionState:
        """Return the active auction or raise if there isn't one."""
        if self.phase is not GamePhase.AUCTION_BIDDING:
            raise RuntimeError(
                f"No active auction: phase is {self.phase.name}"
            )
        assert self.current_auction is not None
        return self.current_auction

    # ── display ────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        lines: list[str] = [
            f"=== Kuhhandel Game ===",
            f"Phase: {self.phase.name}",
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
