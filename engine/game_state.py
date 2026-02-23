"""Top-level game state for a Kuhhandel session."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from engine.models import AnimalCard, AnimalType, Deck, MoneyCard, MoneyValue, Player

MIN_PLAYERS: int = 3
MAX_PLAYERS: int = 5

# Every player starts with exactly these seven money cards.
STARTING_MONEY: list[MoneyValue] = (
    [MoneyValue.ZERO] * 2
    + [MoneyValue.TEN] * 4
    + [MoneyValue.FIFTY] * 1
)

# Bank bonus paid to all players when each successive Donkey card is drawn.
DONKEY_BONUS: dict[int, MoneyValue] = {
    1: MoneyValue.FIFTY,
    2: MoneyValue.HUNDRED,
    3: MoneyValue.TWO_HUNDRED,
    4: MoneyValue.FIVE_HUNDRED,
}


# ---------------------------------------------------------------------------
# State‑machine phases
# ---------------------------------------------------------------------------

class GamePhase(Enum):
    """Discrete phases the game can be in (state‑machine friendly)."""

    TURN_START = auto()
    AUCTION_BIDDING = auto()
    AUCTIONEER_DECISION = auto()
    AUCTION_PAYMENT = auto()


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
        payer_index: Index of the player who must pay (set after auctioneer_decision).
        payee_index: Index of the player who receives the payment (set after auctioneer_decision).
        buyer_index: Index of the player who receives the animal card (set after auctioneer_decision).
    """

    card: AnimalCard
    auctioneer_index: int
    highest_bid: int = 0
    highest_bidder_index: Optional[int] = None
    active_bidders: list[int] = field(default_factory=list)
    payer_index: Optional[int] = None
    payee_index: Optional[int] = None
    buyer_index: Optional[int] = None


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
        donkeys_drawn: Number of Donkey cards drawn so far this game.
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
        self.donkeys_drawn: int = 0

    # ── setup ──────────────────────────────────────────────────────────

    def deal_starting_money(self) -> None:
        """Give every player their seven starting money cards (2x0, 4x10, 1x50)."""
        for player in self.players:
            player.add_money([MoneyCard(v) for v in STARTING_MONEY])

    # ── auction flow ───────────────────────────────────────────────────

    def draw_for_auction(self) -> AnimalCard:
        """The turn player draws a card and opens an auction.

        If the drawn card is a Donkey, the bank immediately pays every player
        a bonus before bidding starts (1st Donkey=50, 2nd=100, 3rd=200, 4th=500).

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

        if card.animal_type is AnimalType.DONKEY:
            self.donkeys_drawn += 1
            bonus_value = DONKEY_BONUS[self.donkeys_drawn]
            for player in self.players:
                player.add_money([MoneyCard(bonus_value)])

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
            RuntimeError: If the phase is not AUCTION_BIDDING.
            ValueError: If the bid is invalid (player not eligible, amount not
                a multiple of 10, or not strictly higher than the current bid).
        """
        auction = self._require_bidding()

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

        Two outcomes after removing the passing player:

        - Zero-bid edge case: all bidders have now passed and the highest_bid
          is still 0.  The auctioneer takes the animal for free, the turn
          advances, and the phase resets to TURN_START.
        - Otherwise, if exactly one bidder remains, the phase transitions to
          AUCTIONEER_DECISION so the auctioneer can sell or exercise their
          right to buy.

        Raises:
            RuntimeError: If the phase is not AUCTION_BIDDING.
            ValueError: If the player is not an active bidder.
        """
        auction = self._require_bidding()

        if player_index not in auction.active_bidders:
            raise ValueError(
                f"Player {player_index} is not an active bidder"
            )

        auction.active_bidders.remove(player_index)

        if len(auction.active_bidders) == 0 and auction.highest_bid == 0:
            # All bidders passed with no bids: auctioneer takes the animal free.
            self.players[auction.auctioneer_index].add_animal(auction.card)
            self._end_turn()
        elif len(auction.active_bidders) == 1:
            # Last bidder standing: let the auctioneer decide.
            auction.highest_bidder_index = auction.active_bidders[0]
            self.phase = GamePhase.AUCTIONEER_DECISION

    def auctioneer_decision(self, sell: bool) -> None:
        """The auctioneer decides whether to sell or invoke their right to buy.

        Can only be called in the AUCTIONEER_DECISION phase.

        Args:
            sell: If True, the auctioneer sells — the highest bidder buys the
                  animal and owes the auctioneer the highest_bid amount.
                  If False, the auctioneer exercises their right to buy — the
                  auctioneer keeps the animal and owes the highest bidder the
                  highest_bid amount.

        Raises:
            RuntimeError: If the phase is not AUCTIONEER_DECISION.
        """
        if self.phase is not GamePhase.AUCTIONEER_DECISION:
            raise RuntimeError(
                f"Cannot decide: phase is {self.phase.name}, "
                f"expected AUCTIONEER_DECISION"
            )
        assert self.current_auction is not None
        auction = self.current_auction

        if sell:
            # Highest bidder pays auctioneer and receives the animal.
            auction.payer_index = auction.highest_bidder_index
            auction.payee_index = auction.auctioneer_index
            auction.buyer_index = auction.highest_bidder_index
        else:
            # Auctioneer pays highest bidder and keeps the animal.
            auction.payer_index = auction.auctioneer_index
            auction.payee_index = auction.highest_bidder_index
            auction.buyer_index = auction.auctioneer_index

        self.phase = GamePhase.AUCTION_PAYMENT

    def process_payment(self, cards_to_pay: list[MoneyCard]) -> None:
        """The payer settles the auction by tendering specific money cards.

        The tendered cards must all be in the payer's hand, and their total
        must be >= highest_bid.  The exact tendered cards transfer to the
        payee — no change is given.  The animal card then goes to the buyer,
        the turn advances, and the phase resets to TURN_START.

        Args:
            cards_to_pay: The exact MoneyCards the payer wishes to tender.

        Raises:
            RuntimeError: If the phase is not AUCTION_PAYMENT.
            ValueError: If the payer does not hold all tendered cards, or the
                total is less than the highest_bid.
        """
        if self.phase is not GamePhase.AUCTION_PAYMENT:
            raise RuntimeError(
                f"Cannot pay: phase is {self.phase.name}, "
                f"expected AUCTION_PAYMENT"
            )
        assert self.current_auction is not None
        auction = self.current_auction
        assert auction.payer_index is not None
        assert auction.payee_index is not None
        assert auction.buyer_index is not None

        payer = self.players[auction.payer_index]
        payee = self.players[auction.payee_index]
        buyer = self.players[auction.buyer_index]

        # Validate that the payer actually holds every tendered card.
        # Use a working copy to correctly handle duplicate denominations.
        hand_copy = list(payer.money)
        for card in cards_to_pay:
            try:
                hand_copy.remove(card)
            except ValueError:
                raise ValueError(
                    f"Player {auction.payer_index} does not hold {card}"
                )

        # Validate that the total is sufficient.
        total = sum(card.amount for card in cards_to_pay)
        if total < auction.highest_bid:
            raise ValueError(
                f"Payment total {total} is less than the required bid "
                f"{auction.highest_bid}"
            )

        # Transfer the exact tendered cards (no change given).
        payer.remove_money(cards_to_pay)
        payee.add_money(cards_to_pay)

        # Award the animal to the buyer.
        buyer.add_animal(auction.card)

        self._end_turn()

    # ── helpers ────────────────────────────────────────────────────────

    def _require_bidding(self) -> AuctionState:
        """Return the active auction or raise if not in AUCTION_BIDDING phase."""
        if self.phase is not GamePhase.AUCTION_BIDDING:
            raise RuntimeError(
                f"No active auction: phase is {self.phase.name}"
            )
        assert self.current_auction is not None
        return self.current_auction

    def _end_turn(self) -> None:
        """Advance to the next player's turn and clear all auction state."""
        self.current_turn = (self.current_turn + 1) % len(self.players)
        self.current_auction = None
        self.phase = GamePhase.TURN_START

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
