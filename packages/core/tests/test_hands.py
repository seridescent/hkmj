from collections import Counter

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from hkmj_core import (
    CHOW_STARTS,
    DIRECTIONS,
    DRAGON_COLORS,
    NUMBERS,
    SUITS,
    Chow,
    ConcealedMeld,
    Decomposition,
    Dragon,
    Number,
    PlayTile,
    Pung,
    Suited,
    Wind,
    decompositions,
    has_decomposition,
    meld_sort_key,
)

play_tiles = st.one_of(
    st.builds(Suited, st.sampled_from(SUITS), st.sampled_from(NUMBERS)),
    st.builds(Wind, st.sampled_from(DIRECTIONS)),
    st.builds(Dragon, st.sampled_from(DRAGON_COLORS)),
)

concealed_melds = st.one_of(
    st.builds(Chow, st.sampled_from(SUITS), st.sampled_from(CHOW_STARTS)),
    st.builds(Pung, play_tiles),
)


def meld_tiles(meld: ConcealedMeld) -> tuple[PlayTile, ...]:
    match meld:
        case Chow():
            return meld.tiles
        case Pung(tile):
            return (tile, tile, tile)


@st.composite
def decomposable_hands(
    draw: st.DrawFn,
) -> tuple[Decomposition, tuple[PlayTile, ...]]:
    """A constructed decomposition plus a shuffled flattening of its tiles."""
    eyes = draw(play_tiles)
    melds = draw(st.lists(concealed_melds, min_size=0, max_size=4))
    tiles = [eyes, eyes, *(t for m in melds for t in meld_tiles(m))]
    assume(max(Counter(tiles).values()) <= 4)
    built = Decomposition(eyes, tuple(sorted(melds, key=meld_sort_key)))
    return built, tuple(draw(st.permutations(tiles)))


@given(decomposable_hands())
def test_constructed_decompositions_are_found(
    case: tuple[Decomposition, tuple[PlayTile, ...]],
) -> None:
    built, tiles = case
    assert built in set(decompositions(tiles))


@given(decomposable_hands())
def test_decompositions_are_sound_and_duplicate_free(
    case: tuple[Decomposition, tuple[PlayTile, ...]],
) -> None:
    _, tiles = case
    found = list(decompositions(tiles))
    assert len(found) == len(set(found))
    for d in found:
        used = [d.eyes, d.eyes, *(t for m in d.melds for t in meld_tiles(m))]
        assert Counter(used) == Counter(tiles)


def dots(*numbers: Number) -> tuple[Suited, ...]:
    return tuple(Suited("dot", n) for n in numbers)


def test_pungs_versus_chows_ambiguity() -> None:
    found = set(decompositions(dots(1, 1, 1, 2, 2, 2, 3, 3, 3, 9, 9)))
    assert found == {
        Decomposition(
            Suited("dot", 9),
            (Pung(Suited("dot", 1)), Pung(Suited("dot", 2)), Pung(Suited("dot", 3))),
        ),
        Decomposition(Suited("dot", 9), (Chow("dot", 1),) * 3),
    }


def test_pung_and_chow_sharing_a_tile_found_once() -> None:
    found = list(decompositions(dots(1, 1, 1, 1, 2, 3, 9, 9)))
    assert found == [
        Decomposition(Suited("dot", 9), (Chow("dot", 1), Pung(Suited("dot", 1))))
    ]


def test_seven_pairs_only_wins_when_chowable() -> None:
    assert has_decomposition(dots(1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7))
    honour_pairs = [t for d in DIRECTIONS for t in (Wind(d), Wind(d))] + [
        t for c in DRAGON_COLORS for t in (Dragon(c), Dragon(c))
    ]
    assert not has_decomposition(honour_pairs)


def test_thirteen_orphans_is_not_a_standard_win() -> None:
    orphans = [
        *(Suited(s, n) for s in SUITS for n in (1, 9)),
        *(Wind(d) for d in DIRECTIONS),
        *(Dragon(c) for c in DRAGON_COLORS),
        Wind("east"),
    ]
    assert not has_decomposition(orphans)


def test_wrong_size_is_rejected() -> None:
    with pytest.raises(ValueError):
        has_decomposition(dots(1, 2, 3))
