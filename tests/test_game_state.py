"""Verify Game initialization, starting money, auction state machine, and repr."""

from engine.models import AnimalCard, AnimalType, MoneyCard, MoneyValue, Player
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


def _force_draw(game: Game, animal_type: AnimalType) -> None:
    """Replace the top-of-deck card with a specific animal type."""
    game.deck._cards[-1] = AnimalCard(animal_type=animal_type)


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
    # Only one bidder left → auctioneer decision phase
    assert game.phase is GamePhase.AUCTIONEER_DECISION
    assert game.current_auction.highest_bidder_index == 2
    print("  pass_auction (one bidder remains) -> AUCTIONEER_DECISION OK")


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

    # Bob passes → Alice is last bidder → AUCTIONEER_DECISION
    game.pass_auction(player_index=1)
    assert game.phase is GamePhase.AUCTIONEER_DECISION
    assert auction.highest_bidder_index == 0  # Alice
    assert auction.highest_bid == 50
    assert auction.card is card
    print("  full auction scenario OK")


# ── Phase 4: Donkey Rule ──────────────────────────────────────────────────

def test_donkey_first_payout() -> None:
    """First Donkey drawn pays every player 50."""
    game = _make_game()
    _force_draw(game, AnimalType.DONKEY)
    before = [p.total_money for p in game.players]

    game.draw_for_auction()

    assert game.donkeys_drawn == 1
    for i, player in enumerate(game.players):
        assert player.total_money == before[i] + 50, (
            f"{player.name}: expected {before[i] + 50}, got {player.total_money}"
        )
    print("  1st Donkey pays 50 to each player OK")


def test_donkey_second_payout() -> None:
    """Second Donkey drawn pays every player 100."""
    game = _make_game()

    # Draw 1st Donkey (turn 0 → 1 after end_turn is not called here,
    # but draw_for_auction doesn't advance turn, so we need to finish
    # the auction manually to get back to TURN_START before the 2nd draw).
    _force_draw(game, AnimalType.DONKEY)
    game.draw_for_auction()
    # End the auction cheaply: Carol (last bidder) passes → AUCTIONEER_DECISION,
    # then auctioneer sells, payer pays.
    game.pass_auction(player_index=1)   # Bob passes (Carol remains → AUCTIONEER_DECISION)
    game.auctioneer_decision(sell=True)
    carol = game.players[2]
    fifty = MoneyCard(MoneyValue.FIFTY)
    # Ensure Carol has a 50 card (she received 50 from donkey bonus)
    assert fifty in carol.money
    game.process_payment(cards_to_pay=[fifty])

    # Now current_turn has advanced. Draw 2nd Donkey.
    _force_draw(game, AnimalType.DONKEY)
    before = [p.total_money for p in game.players]
    game.draw_for_auction()

    assert game.donkeys_drawn == 2
    for i, player in enumerate(game.players):
        assert player.total_money == before[i] + 100
    print("  2nd Donkey pays 100 to each player OK")


def test_donkey_payout_amounts() -> None:
    """Verify the bank gives 50/100/200/500 for each successive Donkey."""
    expected_bonuses = {1: 50, 2: 100, 3: 200, 4: 500}

    for draw_n, expected_bonus in expected_bonuses.items():
        game = _make_game()
        game.donkeys_drawn = draw_n - 1  # simulate prior donkeys
        _force_draw(game, AnimalType.DONKEY)
        before = [p.total_money for p in game.players]
        game.draw_for_auction()

        assert game.donkeys_drawn == draw_n
        for i, player in enumerate(game.players):
            assert player.total_money == before[i] + expected_bonus, (
                f"Donkey #{draw_n}: expected +{expected_bonus} "
                f"for {player.name}, got {player.total_money - before[i]}"
            )
    print("  All Donkey bonus amounts (50/100/200/500) OK")


# ── Phase 4: Zero-bid auction ─────────────────────────────────────────────

def test_zero_bid_auction_all_pass() -> None:
    """When all bidders pass without a single bid, the auctioneer takes the animal free."""
    game = _make_game()
    game.draw_for_auction()

    card = game.current_auction.card
    auctioneer_idx = game.current_auction.auctioneer_index

    # Simulate all-pass by reducing to 1 active bidder then having them pass.
    # (In a 3-player game, Bob passes → 1 bidder = Carol → AUCTIONEER_DECISION
    # with bid=0 is normal. For the zero-bid shortcut we need to reach len==0
    # directly, so we reduce active_bidders to the last one manually.)
    game.current_auction.active_bidders = [game.current_auction.active_bidders[-1]]
    last_bidder = game.current_auction.active_bidders[0]

    money_before = [p.total_money for p in game.players]

    game.pass_auction(player_index=last_bidder)

    assert game.phase is GamePhase.TURN_START, (
        f"Expected TURN_START, got {game.phase.name}"
    )
    assert game.current_auction is None
    assert card in game.players[auctioneer_idx].animals
    assert game.current_turn == (auctioneer_idx + 1) % len(game.players)
    # No money should have changed hands
    for i, player in enumerate(game.players):
        assert player.total_money == money_before[i]
    print("  Zero-bid auction: auctioneer takes free OK")


# ── Phase 4: Auctioneer sells to highest bidder ───────────────────────────

def test_auctioneer_sells_to_bidder() -> None:
    """Auctioneer sells: highest bidder pays auctioneer and receives the animal."""
    game = _make_game()
    game.draw_for_auction()
    card = game.current_auction.card

    # Bob bids 50 (he has one 50-card from starting money).
    game.process_bid(player_index=1, amount=50)
    # Carol passes → only Bob remains → AUCTIONEER_DECISION
    game.pass_auction(player_index=2)
    assert game.phase is GamePhase.AUCTIONEER_DECISION

    # Alice (auctioneer) decides to sell.
    game.auctioneer_decision(sell=True)
    assert game.phase is GamePhase.AUCTION_PAYMENT
    assert game.current_auction.payer_index == 1   # Bob pays
    assert game.current_auction.payee_index == 0   # Alice receives
    assert game.current_auction.buyer_index == 1   # Bob gets animal

    alice_before = game.players[0].total_money
    bob_before = game.players[1].total_money

    fifty = MoneyCard(MoneyValue.FIFTY)
    assert fifty in game.players[1].money  # Bob must hold it

    game.process_payment(cards_to_pay=[fifty])

    # Verify the animal transferred.
    assert card in game.players[1].animals
    assert card not in game.players[0].animals
    # Verify the exact card transferred (no change given).
    assert fifty in game.players[0].money   # Alice now holds Bob's 50-card
    assert fifty not in game.players[1].money  # Bob no longer holds it
    assert game.players[1].total_money == bob_before - 50
    assert game.players[0].total_money == alice_before + 50
    # Turn and phase reset.
    assert game.phase is GamePhase.TURN_START
    assert game.current_turn == 1
    print("  Auctioneer sells to bidder: exact card transfer OK")


def test_auctioneer_sells_no_change_given() -> None:
    """Payer overpays — the full tendered amount goes to the payee, no change."""
    game = _make_game()
    game.draw_for_auction()

    # Bob bids 10, Carol passes → AUCTIONEER_DECISION
    game.process_bid(player_index=1, amount=10)
    game.pass_auction(player_index=2)
    game.auctioneer_decision(sell=True)  # Alice sells

    alice_before = game.players[0].total_money

    # Bob pays with a 50-card even though the bid was only 10.
    fifty = MoneyCard(MoneyValue.FIFTY)
    game.process_payment(cards_to_pay=[fifty])

    # Alice gains 50, not 10 — no change given.
    assert game.players[0].total_money == alice_before + 50
    print("  No-change-given rule: overpayment kept by payee OK")


# ── Phase 4: Auctioneer buys the animal themselves ────────────────────────

def test_auctioneer_buys_animal() -> None:
    """Auctioneer invokes right to buy: pays the highest bidder and takes the animal."""
    game = _make_game()
    game.draw_for_auction()
    card = game.current_auction.card

    # Bob bids 50, Carol passes → AUCTIONEER_DECISION
    game.process_bid(player_index=1, amount=50)
    game.pass_auction(player_index=2)
    assert game.phase is GamePhase.AUCTIONEER_DECISION

    # Alice (auctioneer) invokes her right to buy.
    game.auctioneer_decision(sell=False)
    assert game.phase is GamePhase.AUCTION_PAYMENT
    assert game.current_auction.payer_index == 0   # Alice pays
    assert game.current_auction.payee_index == 1   # Bob receives
    assert game.current_auction.buyer_index == 0   # Alice gets animal

    alice_before = game.players[0].total_money
    bob_before = game.players[1].total_money

    fifty = MoneyCard(MoneyValue.FIFTY)
    assert fifty in game.players[0].money  # Alice must hold it

    game.process_payment(cards_to_pay=[fifty])

    # Verify the animal went to Alice.
    assert card in game.players[0].animals
    assert card not in game.players[1].animals
    # Verify the exact card transferred.
    assert fifty in game.players[1].money   # Bob now holds Alice's 50-card
    assert fifty not in game.players[0].money  # Alice no longer holds it
    assert game.players[0].total_money == alice_before - 50
    assert game.players[1].total_money == bob_before + 50
    # Turn and phase reset.
    assert game.phase is GamePhase.TURN_START
    assert game.current_turn == 1
    print("  Auctioneer buys animal: exact card transfer OK")


# ── Phase 4: process_payment validation ──────────────────────────────────

def test_payment_rejects_insufficient_total() -> None:
    """Payment below the bid amount is rejected."""
    game = _make_game()
    game.draw_for_auction()
    game.process_bid(player_index=1, amount=50)
    game.pass_auction(player_index=2)
    game.auctioneer_decision(sell=True)

    ten = MoneyCard(MoneyValue.TEN)
    try:
        game.process_payment(cards_to_pay=[ten])  # 10 < 50
        assert False, "Expected ValueError"
    except ValueError:
        pass
    print("  process_payment rejects insufficient total OK")


def test_payment_rejects_card_not_in_hand() -> None:
    """Tendering a card the payer does not hold is rejected."""
    game = _make_game()
    game.draw_for_auction()
    game.process_bid(player_index=1, amount=50)
    game.pass_auction(player_index=2)
    game.auctioneer_decision(sell=True)

    # Bob doesn't start with a 500-card.
    five_hundred = MoneyCard(MoneyValue.FIVE_HUNDRED)
    assert five_hundred not in game.players[1].money
    try:
        game.process_payment(cards_to_pay=[five_hundred])
        assert False, "Expected ValueError"
    except ValueError:
        pass
    print("  process_payment rejects card not in hand OK")


def test_auctioneer_decision_wrong_phase() -> None:
    """auctioneer_decision raises outside AUCTIONEER_DECISION phase."""
    game = _make_game()
    game.draw_for_auction()
    try:
        game.auctioneer_decision(sell=True)
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass
    print("  auctioneer_decision rejects wrong phase OK")


def test_process_payment_wrong_phase() -> None:
    """process_payment raises outside AUCTION_PAYMENT phase."""
    game = _make_game()
    game.draw_for_auction()
    try:
        game.process_payment(cards_to_pay=[])
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass
    print("  process_payment rejects wrong phase OK")


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

    # Phase 4 – Donkey Rule
    test_donkey_first_payout()
    test_donkey_second_payout()
    test_donkey_payout_amounts()

    # Phase 4 – Zero-bid auction
    test_zero_bid_auction_all_pass()

    # Phase 4 – Auctioneer's Right
    test_auctioneer_sells_to_bidder()
    test_auctioneer_sells_no_change_given()
    test_auctioneer_buys_animal()

    # Phase 4 – Payment validation
    test_payment_rejects_insufficient_total()
    test_payment_rejects_card_not_in_hand()
    test_auctioneer_decision_wrong_phase()
    test_process_payment_wrong_phase()

    print("\nAll tests passed.")
