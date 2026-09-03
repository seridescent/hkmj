"""Tile types for Old Hong Kong mahjong.

Each variant is its own frozen dataclass with a literal `kind` discriminator.
Class patterns and `isinstance` still narrow the `Tile` union in Python, while
the tag keeps the same union unambiguous after serialization.

Discriminators are keyword-only rather than `init=False`: real data keeps its
clean positional constructor and pattern matching, while validators can still
check the tag when reconstructing a value.
"""

from collections.abc import Collection
from dataclasses import dataclass, field
from typing import Literal

type Direction = Literal["east", "south", "west", "north"]
"""A table direction: seat position, prevailing wind, or wind-tile face."""

type Suit = Literal["dot", "bamboo", "myriad"]
type DragonColor = Literal["red", "green", "white"]
type Number = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]
type BonusNumber = Literal[1, 2, 3, 4]


@dataclass(frozen=True, slots=True)
class Suited:
    kind: Literal["suited"] = field(kw_only=True, default="suited")
    suit: Suit
    number: Number


@dataclass(frozen=True, slots=True)
class Wind:
    kind: Literal["wind"] = field(kw_only=True, default="wind")
    direction: Direction


@dataclass(frozen=True, slots=True)
class Dragon:
    kind: Literal["dragon"] = field(kw_only=True, default="dragon")
    color: DragonColor


@dataclass(frozen=True, slots=True)
class Flower:
    kind: Literal["flower"] = field(kw_only=True, default="flower")
    number: BonusNumber


@dataclass(frozen=True, slots=True)
class Season:
    kind: Literal["season"] = field(kw_only=True, default="season")
    number: BonusNumber


type Honor = Wind | Dragon
type Bonus = Flower | Season

type PlayTile = Suited | Honor
"""A tile that can appear in a hand, meld, or discard pile.

Bonus tiles never can: they are set aside the moment they are drawn.
"""

type Tile = PlayTile | Bonus


DIRECTIONS: tuple[Direction, ...] = ("east", "south", "west", "north")
"""All directions in turn order (counter-clockwise at a physical table)."""

SUITS: tuple[Suit, ...] = ("dot", "bamboo", "myriad")
DRAGON_COLORS: tuple[DragonColor, ...] = ("red", "green", "white")
NUMBERS: tuple[Number, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 9)
BONUS_NUMBERS: tuple[BonusNumber, ...] = (1, 2, 3, 4)


def next_seat(
    direction: Direction, seats: Collection[Direction] = DIRECTIONS
) -> Direction:
    """The seat that acts after `direction` in regular turn order.

    `seats` is the set of occupied seats, for reduced-player games; absent
    seats are skipped.
    """
    i = DIRECTIONS.index(direction)
    for step in (1, 2, 3, 4):
        candidate = DIRECTIONS[(i + step) % 4]
        if candidate in seats:
            return candidate
    raise ValueError("seats is empty")


def bonus_direction(number: BonusNumber) -> Direction:
    """The seat a flower or season is associated with for scoring."""
    return DIRECTIONS[number - 1]


def tile_sort_key(tile: Tile) -> tuple[int, int, int]:
    """Total order over tiles, for canonical (sorted) hands and rendering."""
    match tile:
        case Suited(suit, number):
            return (0, SUITS.index(suit), number)
        case Wind(direction):
            return (1, DIRECTIONS.index(direction), 0)
        case Dragon(color):
            return (2, DRAGON_COLORS.index(color), 0)
        case Flower(number):
            return (3, 0, number)
        case Season(number):
            return (4, 0, number)


def full_tile_set() -> tuple[Tile, ...]:
    """All 144 tiles: 4 of each suited and honor tile, 1 of each bonus tile."""
    suited = [Suited(s, n) for s in SUITS for n in NUMBERS]
    honors = [*(Wind(d) for d in DIRECTIONS), *(Dragon(c) for c in DRAGON_COLORS)]
    bonus = [*(Flower(n) for n in BONUS_NUMBERS), *(Season(n) for n in BONUS_NUMBERS)]
    return (*[t for t in suited + honors for _ in range(4)], *bonus)
