"""Verify that the Kuhhandel data models initialize and behave correctly."""

from models import AnimalCard, AnimalType, Deck, MoneyCard, MoneyValue, Player


def test_animal_card_properties() -> None:
    card = AnimalCard(AnimalType.COW)
    assert card.name == "Cow"
    assert card.quartet_value == 800
    print(f"  AnimalCard properties OK: {card}")


def test_money_card_properties() -> None:
    card = MoneyCard(MoneyValue.FIVE_HUNDRED)
    assert card.amount == 500
    zero = MoneyCard(MoneyValue.ZERO)
    assert zero.amount == 0
    print(f"  MoneyCard properties OK: {card}, {zero}")


def test_deck_initialization() -> None:
    deck = Deck()
    assert len(deck) == 40, f"Expected 40 cards, got {len(deck)}"

    # Verify exactly 4 copies of each animal type
    counts: dict[AnimalType, int] = {}
    temp_deck = Deck()
    while temp_deck.remaining > 0:
        card = temp_deck.draw()
        assert card is not None
        counts[card.animal_type] = counts.get(card.animal_type, 0) + 1

    assert len(counts) == 10, f"Expected 10 animal types, got {len(counts)}"
    for animal, count in counts.items():
        assert count == 4, f"{animal.animal_name} has {count} cards, expected 4"
    print(f"  Deck initialization OK: 40 cards, 10 types x 4 each")


def test_deck_shuffle() -> None:
    deck_a = Deck()
    deck_b = Deck()
    deck_b.shuffle()

    # Draw all cards from both decks and compare order
    order_a = [deck_a.draw() for _ in range(40)]
    order_b = [deck_b.draw() for _ in range(40)]

    # After shuffling, the order should (almost certainly) differ
    assert order_a != order_b, "Shuffled deck has same order as unshuffled (extremely unlikely)"
    # But they should contain the same cards
    assert sorted(order_a, key=lambda c: c.name) == sorted(order_b, key=lambda c: c.name)
    print("  Deck shuffle OK: order changed, same cards present")


def test_deck_draw_empties() -> None:
    deck = Deck()
    for _ in range(40):
        card = deck.draw()
        assert card is not None
    assert deck.draw() is None
    assert len(deck) == 0
    print("  Deck draw-to-empty OK: returns None when exhausted")


def test_player() -> None:
    player = Player(name="Alice")
    assert player.total_money == 0
    assert len(player.animals) == 0

    player.money.append(MoneyCard(MoneyValue.HUNDRED))
    player.money.append(MoneyCard(MoneyValue.FIFTY))
    assert player.total_money == 150

    player.animals.append(AnimalCard(AnimalType.HORSE))
    assert len(player.animals) == 1
    print(f"  Player OK: {player}")


if __name__ == "__main__":
    print("Running model tests...\n")
    test_animal_card_properties()
    test_money_card_properties()
    test_deck_initialization()
    test_deck_shuffle()
    test_deck_draw_empties()
    test_player()
    print("\nAll tests passed.")
