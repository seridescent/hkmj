"""Winning-hand decomposition.

Decomposes the concealed part of a hand (3m + 2 tiles) into m melds plus a
pair of eyes. Declared melds are fixed and public, so the win check for a
full hand reduces to: does any decomposition of the concealed tiles exist?
The target meld count k (4 in standard play) never appears here — hand sizes
enforce it upstream.

Thirteen orphans, the one limit hand that is not melds-plus-eyes shaped,
gets its own predicate here.
"""

from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import cast

from hkmj_core.melds import Chow, ChowStart, Pung, meld_sort_key
from hkmj_core.tiles import (
    DIRECTIONS,
    DRAGON_COLORS,
    SUITS,
    Dragon,
    Number,
    PlayTile,
    Suited,
    Wind,
    tile_sort_key,
)

type ConcealedMeld = Chow | Pung
"""A meld hidden in the concealed hand — kongs only exist once declared."""


@dataclass(frozen=True, slots=True)
class Decomposition:
    eyes: PlayTile
    melds: tuple[ConcealedMeld, ...]
    """Canonically sorted by `meld_sort_key`."""


def decompositions(tiles: Iterable[PlayTile]) -> Iterator[Decomposition]:
    """All ways to read `tiles` as melds plus one pair of eyes.

    `tiles` must number 3m + 2 for some m >= 0. Yields each distinct reading
    exactly once; every reading uses the input multiset exactly.
    """
    counts = Counter(tiles)
    if (n := sum(counts.values())) % 3 != 2:
        raise ValueError(f"decomposable hands have 3m + 2 tiles, got {n}")

    distinct = sorted(counts, key=tile_sort_key)
    for eyes in distinct:
        if counts[eyes] < 2:
            continue

        counts[eyes] -= 2
        for melds in _melds(counts, distinct):
            yield Decomposition(eyes, tuple(sorted(melds, key=meld_sort_key)))
        counts[eyes] += 2


ORPHAN_KINDS: frozenset[PlayTile] = frozenset(
    {Suited(suit, number) for suit in SUITS for number in (1, 9)}
    | {Wind(direction) for direction in DIRECTIONS}
    | {Dragon(color) for color in DRAGON_COLORS}
)
"""The thirteen terminal and honor kinds."""


def is_thirteen_orphans(tiles: Iterable[PlayTile]) -> bool:
    """Whether the concealed tiles are the thirteen-orphans limit hand:
    every terminal and honor kind, exactly one of them duplicated."""
    pool = list(tiles)
    return len(pool) == 14 and set(pool) == ORPHAN_KINDS


def has_decomposition(tiles: Iterable[PlayTile]) -> bool:
    """Whether the concealed tiles (3m + 2 of them) read as melds plus eyes.

    Deliberately narrower than "is a win": special hands and any minimum-faan
    requirement are rules-layer concerns.
    """
    return next(decompositions(tiles), None) is not None


def _melds(
    counts: Counter[PlayTile], distinct: list[PlayTile]
) -> Iterator[tuple[ConcealedMeld, ...]]:
    lowest = next((t for t in distinct if counts[t]), None)
    if lowest is None:
        yield ()
        return

    # Every remaining copy of `lowest` must be consumed right here: melds are
    # peeled off in canonical order, so no later meld can reach back to it.
    # It fits in at most one pung; every other copy must start a chow. This
    # branching yields each decomposition exactly once (a plain pung-or-chow
    # choice would find e.g. {pung 111, chow 123} once per ordering).
    n = counts[lowest]
    for use_pung in (False, True) if n >= 3 else (False,):
        # how many chows must we construct to use all `lowest` tiles?
        n_chows = n - 3 if use_pung else n

        if n_chows == 0:
            # implies `use_pung`, else lowest would be None
            counts[lowest] = 0
            for rest in _melds(counts, distinct):
                yield (Pung(lowest), *rest)
            counts[lowest] = n
            continue

        if not (isinstance(lowest, Suited) and lowest.number <= 7):
            continue

        second = Suited(lowest.suit, cast(Number, lowest.number + 1))
        third = Suited(lowest.suit, cast(Number, lowest.number + 2))
        if counts[second] < n_chows or counts[third] < n_chows:
            continue

        chow = Chow(lowest.suit, cast(ChowStart, lowest.number))
        taken: tuple[ConcealedMeld, ...] = (
            (Pung(lowest), *([chow] * n_chows)) if use_pung else (chow,) * n_chows
        )
        counts[lowest] = 0
        counts[second] -= n_chows
        counts[third] -= n_chows
        for rest in _melds(counts, distinct):
            yield (*taken, *rest)
        counts[lowest] = n
        counts[second] += n_chows
        counts[third] += n_chows
