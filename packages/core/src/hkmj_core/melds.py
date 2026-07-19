"""Meld types.

A `PlayerState.melds` entry is always a *declared* meld: exposed chows, pungs,
and kongs formed from claimed discards, plus concealed kongs (declared and set
aside; whether their identity is visible before the hand ends is a table
convention). Chows and pungs formed entirely by drawing stay as loose tiles in
the concealed hand.
"""

from dataclasses import dataclass
from typing import Literal, cast

from hkmj_core.tiles import Honor, Number, Suit, Suited, tile_sort_key

type ChowStart = Literal[1, 2, 3, 4, 5, 6, 7]

CHOW_STARTS: tuple[ChowStart, ...] = (1, 2, 3, 4, 5, 6, 7)


@dataclass(frozen=True, slots=True)
class Chow:
    suit: Suit
    start: ChowStart

    @property
    def tiles(self) -> tuple[Suited, Suited, Suited]:
        second = cast(Number, self.start + 1)
        third = cast(Number, self.start + 2)
        return (
            Suited(self.suit, self.start),
            Suited(self.suit, second),
            Suited(self.suit, third),
        )


@dataclass(frozen=True, slots=True)
class Pung:
    tile: Suited | Honor


@dataclass(frozen=True, slots=True)
class Kong:
    tile: Suited | Honor
    concealed: bool
    """True only for a kong declared from four self-drawn tiles.

    A kong promoted from an exposed pung, or completed from a claimed
    discard, is exposed and scores as such.
    """


type Meld = Chow | Pung | Kong


def meld_sort_key(meld: Meld) -> tuple[int, int, int, int, int]:
    """Total order over melds, for canonical (sorted) meld lists."""
    match meld:
        case Chow(suit, start):
            return (*tile_sort_key(Suited(suit, start)), 0, 0)
        case Pung(tile):
            return (*tile_sort_key(tile), 1, 0)
        case Kong(tile, concealed):
            return (*tile_sort_key(tile), 2, int(concealed))
