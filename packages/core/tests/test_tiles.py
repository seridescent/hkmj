from collections import Counter

from hkmj_core import (
    CHOW_STARTS,
    SUITS,
    Chow,
    Kong,
    Pung,
    Dragon,
    Flower,
    Season,
    Suited,
    Wind,
    bonus_direction,
    full_tile_set,
    meld_sort_key,
    next_seat,
    tile_sort_key,
)


def test_meld_sort_key_is_a_total_order() -> None:
    pungable = sorted(
        {t for t in full_tile_set() if isinstance(t, (Suited, Wind, Dragon))},
        key=tile_sort_key,
    )
    melds = [
        *(Chow(suit, start) for suit in SUITS for start in CHOW_STARTS),
        *(Pung(t) for t in pungable),
        *(Kong(t, concealed) for t in pungable for concealed in (False, True)),
    ]
    assert len({meld_sort_key(m) for m in melds}) == len(melds)


def test_tile_sort_key_is_a_total_order() -> None:
    distinct = set(full_tile_set())
    assert len({tile_sort_key(t) for t in distinct}) == len(distinct)


def test_full_tile_set_composition() -> None:
    tiles = full_tile_set()
    assert len(tiles) == 144

    counts = Counter(tiles)
    assert all(counts[t] == 4 for t in counts if isinstance(t, (Suited, Wind, Dragon)))
    assert all(counts[t] == 1 for t in counts if isinstance(t, (Flower, Season)))
    assert sum(isinstance(t, Suited) for t in tiles) == 108


def test_turn_order_cycles() -> None:
    assert next_seat("east") == "south"
    assert next_seat("north") == "east"


def test_turn_order_skips_absent_seats() -> None:
    assert next_seat("west", ("east", "south", "west")) == "east"
    assert next_seat("east", ("east",)) == "east"


def test_bonus_direction() -> None:
    assert bonus_direction(1) == "east"
    assert bonus_direction(4) == "north"


def test_chow_tiles() -> None:
    assert Chow("bamboo", 7).tiles == (
        Suited("bamboo", 7),
        Suited("bamboo", 8),
        Suited("bamboo", 9),
    )
