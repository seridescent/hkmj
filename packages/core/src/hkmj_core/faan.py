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

from dataclasses import dataclass, field
from typing import Literal

from hkmj_core.tiles import DragonColor


@dataclass(frozen=True, slots=True)
class CommonHand:
    kind: Literal["common_hand"] = field(kw_only=True, default="common_hand")


@dataclass(frozen=True, slots=True)
class AllInTriplets:
    kind: Literal["all_in_triplets"] = field(kw_only=True, default="all_in_triplets")


@dataclass(frozen=True, slots=True)
class MixedOrphans:
    kind: Literal["mixed_orphans"] = field(kw_only=True, default="mixed_orphans")


@dataclass(frozen=True, slots=True)
class MixedOneSuit:
    kind: Literal["mixed_one_suit"] = field(kw_only=True, default="mixed_one_suit")


@dataclass(frozen=True, slots=True)
class AllOneSuit:
    kind: Literal["all_one_suit"] = field(kw_only=True, default="all_one_suit")


@dataclass(frozen=True, slots=True)
class SmallDragons:
    kind: Literal["small_dragons"] = field(kw_only=True, default="small_dragons")


@dataclass(frozen=True, slots=True)
class GreatDragons:
    kind: Literal["great_dragons"] = field(kw_only=True, default="great_dragons")


@dataclass(frozen=True, slots=True)
class SmallWinds:
    kind: Literal["small_winds"] = field(kw_only=True, default="small_winds")


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
    kind: Literal["seat_wind"] = field(kw_only=True, default="seat_wind")


@dataclass(frozen=True, slots=True)
class PrevailingWind:
    kind: Literal["prevailing_wind"] = field(kw_only=True, default="prevailing_wind")


@dataclass(frozen=True, slots=True)
class DragonMeld:
    kind: Literal["dragon_meld"] = field(kw_only=True, default="dragon_meld")
    color: DragonColor


type HonorPattern = SeatWind | PrevailingWind | DragonMeld


@dataclass(frozen=True, slots=True)
class NoBonusTiles:
    kind: Literal["no_bonus_tiles"] = field(kw_only=True, default="no_bonus_tiles")


@dataclass(frozen=True, slots=True)
class FlowerOfOwnWind:
    kind: Literal["flower_of_own_wind"] = field(
        kw_only=True, default="flower_of_own_wind"
    )


@dataclass(frozen=True, slots=True)
class SeasonOfOwnWind:
    kind: Literal["season_of_own_wind"] = field(
        kw_only=True, default="season_of_own_wind"
    )


@dataclass(frozen=True, slots=True)
class AllFlowers:
    kind: Literal["all_flowers"] = field(kw_only=True, default="all_flowers")


@dataclass(frozen=True, slots=True)
class AllSeasons:
    kind: Literal["all_seasons"] = field(kw_only=True, default="all_seasons")


type BonusPattern = (
    NoBonusTiles | FlowerOfOwnWind | SeasonOfOwnWind | AllFlowers | AllSeasons
)


@dataclass(frozen=True, slots=True)
class SelfPick:
    kind: Literal["self_pick"] = field(kw_only=True, default="self_pick")


@dataclass(frozen=True, slots=True)
class WinByKong:
    kind: Literal["win_by_kong"] = field(kw_only=True, default="win_by_kong")


@dataclass(frozen=True, slots=True)
class RobbingTheKong:
    kind: Literal["robbing_the_kong"] = field(kw_only=True, default="robbing_the_kong")


@dataclass(frozen=True, slots=True)
class ConcealedHand:
    kind: Literal["concealed_hand"] = field(kw_only=True, default="concealed_hand")


@dataclass(frozen=True, slots=True)
class WinByLastCatch:
    kind: Literal["win_by_last_catch"] = field(
        kw_only=True, default="win_by_last_catch"
    )


@dataclass(frozen=True, slots=True)
class HeavenlyHand:
    kind: Literal["heavenly_hand"] = field(kw_only=True, default="heavenly_hand")


@dataclass(frozen=True, slots=True)
class EarthlyHand:
    kind: Literal["earthly_hand"] = field(kw_only=True, default="earthly_hand")


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
    kind: Literal["all_honor_tiles"] = field(kw_only=True, default="all_honor_tiles")


@dataclass(frozen=True, slots=True)
class SelfTriplets:
    """Every meld a concealed pung or kong, won by self-pick or by a
    discard completing the eyes."""

    kind: Literal["self_triplets"] = field(kw_only=True, default="self_triplets")


@dataclass(frozen=True, slots=True)
class Orphans:
    """Pungs/kongs of ones and nines only — no honors, unlike MixedOrphans."""

    kind: Literal["orphans"] = field(kw_only=True, default="orphans")


@dataclass(frozen=True, slots=True)
class NineGates:
    kind: Literal["nine_gates"] = field(kw_only=True, default="nine_gates")


@dataclass(frozen=True, slots=True)
class GreatWinds:
    kind: Literal["great_winds"] = field(kw_only=True, default="great_winds")


@dataclass(frozen=True, slots=True)
class AllKongs:
    kind: Literal["all_kongs"] = field(kw_only=True, default="all_kongs")


@dataclass(frozen=True, slots=True)
class ThirteenOrphans:
    kind: Literal["thirteen_orphans"] = field(kw_only=True, default="thirteen_orphans")


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
