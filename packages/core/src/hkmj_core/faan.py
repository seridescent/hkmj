"""Faan patterns and their valuation.

Terminology, following the reference: a winning hand is awarded *faan* (番)
— the counting unit — by satisfying scoring criteria; faan is later
converted exponentially into *points* (the money-analog score) via a
full-spicy or half-spicy table, which is a separate, downstream layer.
Everything in this module is denominated in faan.

A `Pattern` records only the fact that a criterion fired; `pattern_faan`
holds the reference valuations. The cap belongs to the rules, while the
faan-to-points table belongs to scoring, so minimum-faan gating and
highest-faan winner comparison remain faan-denominated.
"""

from dataclasses import dataclass

from hkmj_core.tiles import DragonColor


@dataclass(frozen=True, slots=True)
class CommonHand:
    pass


@dataclass(frozen=True, slots=True)
class AllInTriplets:
    pass


@dataclass(frozen=True, slots=True)
class MixedOrphans:
    pass


@dataclass(frozen=True, slots=True)
class MixedOneSuit:
    pass


@dataclass(frozen=True, slots=True)
class AllOneSuit:
    pass


@dataclass(frozen=True, slots=True)
class SmallDragons:
    pass


@dataclass(frozen=True, slots=True)
class GreatDragons:
    pass


@dataclass(frozen=True, slots=True)
class SmallWinds:
    pass


type HandPattern = (
    CommonHand
    | AllInTriplets
    | MixedOrphans
    | MixedOneSuit
    | AllOneSuit
    | SmallDragons
    | GreatDragons
    | SmallWinds
)


@dataclass(frozen=True, slots=True)
class SeatWind:
    pass


@dataclass(frozen=True, slots=True)
class PrevailingWind:
    pass


@dataclass(frozen=True, slots=True)
class DragonMeld:
    color: DragonColor


type HonorPattern = SeatWind | PrevailingWind | DragonMeld


@dataclass(frozen=True, slots=True)
class NoBonusTiles:
    pass


@dataclass(frozen=True, slots=True)
class FlowerOfOwnWind:
    pass


@dataclass(frozen=True, slots=True)
class SeasonOfOwnWind:
    pass


@dataclass(frozen=True, slots=True)
class AllFlowers:
    pass


@dataclass(frozen=True, slots=True)
class AllSeasons:
    pass


type BonusPattern = (
    NoBonusTiles | FlowerOfOwnWind | SeasonOfOwnWind | AllFlowers | AllSeasons
)


@dataclass(frozen=True, slots=True)
class SelfPick:
    pass


@dataclass(frozen=True, slots=True)
class WinByKong:
    pass


@dataclass(frozen=True, slots=True)
class RobbingTheKong:
    pass


@dataclass(frozen=True, slots=True)
class ConcealedHand:
    pass


@dataclass(frozen=True, slots=True)
class WinByLastCatch:
    pass


@dataclass(frozen=True, slots=True)
class HeavenlyHand:
    pass


@dataclass(frozen=True, slots=True)
class EarthlyHand:
    pass


type WinConditionPattern = (
    SelfPick
    | WinByKong
    | RobbingTheKong
    | ConcealedHand
    | WinByLastCatch
    | HeavenlyHand
    | EarthlyHand
)


@dataclass(frozen=True, slots=True)
class AllHonorTiles:
    pass


@dataclass(frozen=True, slots=True)
class SelfTriplets:
    """Every meld a concealed pung or kong, won by self-pick or by a
    discard completing the eyes."""


@dataclass(frozen=True, slots=True)
class Orphans:
    """Pungs/kongs of ones and nines only — no honors, unlike MixedOrphans."""


@dataclass(frozen=True, slots=True)
class NineGates:
    pass


@dataclass(frozen=True, slots=True)
class GreatWinds:
    pass


@dataclass(frozen=True, slots=True)
class AllKongs:
    pass


@dataclass(frozen=True, slots=True)
class ThirteenOrphans:
    pass


type LimitHand = (
    AllHonorTiles
    | SelfTriplets
    | Orphans
    | NineGates
    | GreatWinds
    | AllKongs
    | ThirteenOrphans
)

type Pattern = (
    HandPattern | HonorPattern | BonusPattern | WinConditionPattern | LimitHand
)


def pattern_faan(pattern: Pattern) -> int:
    """Faan value of one pattern, from the reference tables.

    The match is exhaustive over `Pattern`, so the type checker flags any
    pattern added without a valuation.
    """
    match pattern:
        case (
            CommonHand()
            | MixedOrphans()
            | SeatWind()
            | PrevailingWind()
            | DragonMeld()
            | NoBonusTiles()
            | FlowerOfOwnWind()
            | SeasonOfOwnWind()
            | SelfPick()
            | WinByKong()
            | RobbingTheKong()
            | ConcealedHand()
            | WinByLastCatch()
        ):
            return 1
        case AllFlowers() | AllSeasons():
            return 2
        case AllInTriplets() | MixedOneSuit() | SmallDragons():
            return 3
        case GreatDragons():
            return 5
        case SmallWinds():
            return 6
        case AllOneSuit():
            return 7
        case AllHonorTiles() | SelfTriplets() | Orphans() | NineGates():
            return 10
        case (
            HeavenlyHand()
            | EarthlyHand()
            | GreatWinds()
            | AllKongs()
            | ThirteenOrphans()
        ):
            return 13
