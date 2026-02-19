"""Verify Game initialization, starting money, and repr."""

from engine.models import Player
from engine.game_state import Game


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
    assert "Turn: Player 0 (Alice)" in text
    assert "40 cards remaining" in text
    assert "Alice" in text and "Bob" in text and "Carol" in text
    print("  Game __repr__ OK")


if __name__ == "__main__":
    print("Running game_state tests...\n")

    test_game_rejects_invalid_player_count()
    test_game_accepts_valid_player_counts()
    test_deal_starting_money()
    test_game_repr()

    # ── Demo: 3-player game setup ──────────────────────────────────────
    print("\n--- Demo: 3-player game ---\n")
    demo_players = [Player(name=n) for n in ("Alice", "Bob", "Carol")]
    demo = Game(demo_players)
    demo.deal_starting_money()

    print(repr(demo))
    print()
    for p in demo.players:
        print(f"  {p.name}'s hidden money: {p.money}  (total: {p.total_money})")

    print("\nAll tests passed.")
