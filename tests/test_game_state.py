"""Verify Game initialization, starting money, auction state machine, and repr."""

from engine.models import Player
from engine.game_state import Game, GamePhase


def test_game_rejects_invalid_player_count() -> None:
    for n in (1, 2, 6, 10):
        players = [Player(name=f"P{i}") for i in range(n)]
        try:
            Game(players)
            assert False, f"Expected ValueError for {n} players"
        except ValueError:
            pass
    print("  Game rejects invalid player counts OK")


def test_game_accepts_valid_player_counts() -> None:
    for n in (3, 4, 5):
        players = [Player(name=f"P{i}") for i in range(n)]
        game = Game(players)
        assert len(game.players) == n
        assert game.deck.remaining == 40
        assert game.current_turn == 0
    print("  Game accepts 3-5 players OK")


def test_deal_starting_money() -> None:
    players = [Player(name=name) for name in ("Alice", "Bob", "Carol")]
    game = Game(players)
    game.deal_starting_money()

    for player in game.players:
        assert len(player.money) == 7, (
            f"{player.name} has {len(player.money)} cards, expected 7"
        )
        assert player.total_money == 90, (
            f"{player.name} has {player.total_money}, expected 90"
        )

        # Verify exact denomination breakdown
        amounts = [card.amount for card in player.money]
        assert amounts.count(0) == 2
        assert amounts.count(10) == 4
        assert amounts.count(50) == 1
    print("  deal_starting_money OK: 7 cards each, 90 per player")


def test_game_repr() -> None:
    players = [Player(name=name) for name in ("Alice", "Bob", "Carol")]
    game = Game(players)
    text = repr(game)
    assert "Kuhhandel Game" in text
    assert "Phase: TURN_START" in text
    assert "Turn: Player 0 (Alice)" in text
    assert "40 cards remaining" in text
    assert "Alice" in text and "Bob" in text and "Carol" in text
    print("  Game __repr__ OK")


# ── Auction state‑machine ─────────────────────────────────────────────────

def _make_game() -> Game:
    """Helper: 3-player game with starting money dealt."""
    players = [Player(name=n) for n in ("Alice", "Bob", "Carol")]
    game = Game(players)
    game.deal_starting_money()
    return game


def test_draw_for_auction() -> None:
    game = _make_game()
    assert game.phase is GamePhase.TURN_START

    card = game.draw_for_auction()
    assert card is not None
    assert game.phase is GamePhase.AUCTION_BIDDING
    assert game.deck.remaining == 39

    auction = game.current_auction
    assert auction is not None
    assert auction.card is card
    assert auction.auctioneer_index == 0  # Alice's turn
    assert auction.highest_bid == 0
    assert auction.highest_bidder_index is None
    assert auction.active_bidders == [1, 2]  # Bob, Carol
    print("  draw_for_auction OK")


def test_draw_for_auction_wrong_phase() -> None:
    game = _make_game()
    game.draw_for_auction()
    try:
        game.draw_for_auction()  # already in AUCTION_BIDDING
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass
    print("  draw_for_auction rejects wrong phase OK")


def test_process_bid_valid() -> None:
    game = _make_game()
    game.draw_for_auction()

    game.process_bid(player_index=1, amount=10)
    assert game.current_auction.highest_bid == 10
    assert game.current_auction.highest_bidder_index == 1

    game.process_bid(player_index=2, amount=30)
    assert game.current_auction.highest_bid == 30
    assert game.current_auction.highest_bidder_index == 2
    print("  process_bid valid bids OK")


def test_process_bid_rejects_auctioneer() -> None:
    game = _make_game()
    game.draw_for_auction()
    try:
        game.process_bid(player_index=0, amount=10)  # auctioneer
        assert False, "Expected ValueError"
    except ValueError:
        pass
    print("  process_bid rejects auctioneer OK")


def test_process_bid_rejects_low_bid() -> None:
    game = _make_game()
    game.draw_for_auction()
    game.process_bid(player_index=1, amount=20)
    try:
        game.process_bid(player_index=2, amount=20)  # equal, not higher
        assert False, "Expected ValueError"
    except ValueError:
        pass
    try:
        game.process_bid(player_index=2, amount=10)  # lower
        assert False, "Expected ValueError"
    except ValueError:
        pass
    print("  process_bid rejects low/equal bids OK")


def test_process_bid_rejects_non_multiple_of_10() -> None:
    game = _make_game()
    game.draw_for_auction()
    try:
        game.process_bid(player_index=1, amount=15)
        assert False, "Expected ValueError"
    except ValueError:
        pass
    print("  process_bid rejects non-multiple-of-10 OK")


def test_pass_auction_removes_bidder() -> None:
    game = _make_game()
    game.draw_for_auction()
    game.pass_auction(player_index=1)

    assert 1 not in game.current_auction.active_bidders
    # Only one bidder left → auction won
    assert game.phase is GamePhase.AUCTION_WON
    assert game.current_auction.highest_bidder_index == 2
    print("  pass_auction (immediate win) OK")


def test_pass_auction_rejects_non_bidder() -> None:
    game = _make_game()
    game.draw_for_auction()
    try:
        game.pass_auction(player_index=0)  # auctioneer
        assert False, "Expected ValueError"
    except ValueError:
        pass
    print("  pass_auction rejects non-bidder OK")


def test_full_auction_scenario() -> None:
    """Simulate a full bidding sequence: bids, passes, winner."""
    game = _make_game()
    game.current_turn = 2  # Carol is auctioneer
    card = game.draw_for_auction()
    auction = game.current_auction

    assert auction.auctioneer_index == 2
    assert auction.active_bidders == [0, 1]  # Alice, Bob

    # Alice bids 10
    game.process_bid(player_index=0, amount=10)
    assert auction.highest_bid == 10
    assert game.phase is GamePhase.AUCTION_BIDDING

    # Bob bids 20
    game.process_bid(player_index=1, amount=20)
    assert auction.highest_bid == 20

    # Alice raises to 50
    game.process_bid(player_index=0, amount=50)
    assert auction.highest_bid == 50

    # Bob passes → Alice wins
    game.pass_auction(player_index=1)
    assert game.phase is GamePhase.AUCTION_WON
    assert auction.highest_bidder_index == 0  # Alice
    assert auction.highest_bid == 50
    assert auction.card is card
    print("  full auction scenario OK")


if __name__ == "__main__":
    print("Running game_state tests...\n")

    # Phase 2 tests
    test_game_rejects_invalid_player_count()
    test_game_accepts_valid_player_counts()
    test_deal_starting_money()
    test_game_repr()

    # Phase 3 – auction state machine
    test_draw_for_auction()
    test_draw_for_auction_wrong_phase()
    test_process_bid_valid()
    test_process_bid_rejects_auctioneer()
    test_process_bid_rejects_low_bid()
    test_process_bid_rejects_non_multiple_of_10()
    test_pass_auction_removes_bidder()
    test_pass_auction_rejects_non_bidder()
    test_full_auction_scenario()

    print("\nAll tests passed.")
