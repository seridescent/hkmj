"""Faan scoring for winning states.

`score` is defined only on states whose phase is `HandOver(Win)` — the
engine constructs those via a single path (`_win_state`), for real wins and
hypothetical ones alike, so gating, winner resolution, and final scoring
all agree by construction.

A hand may admit several decompositions; each is scored independently and
the best reading wins.

Identification is separated from valuation: an entry is a per-pattern
frozen dataclass recording only the fact that the pattern fired, and
`default_faan` maps entries to the reference faan values. Consumers
(rewards, UIs, eval graders) can match on exactly which patterns fired, and
variant valuations only need a different function.

Win by double-kong (槓上槓) is intentionally not modeled: it would thread
chained draw provenance through two phase types for a vanishingly rare
event.

TODO: limit hands. They ignore honor and bonus faan, so they arrive as a
separate `LimitScore` variant whose entry type excludes `HonorFaan` and
`BonusFaan` structurally, with `Score` becoming a union.
TODO: seven pairs and thirteen orphans as additional readings.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from hkmj_core.hands import Decomposition, decompositions
from hkmj_core.melds import Chow, Kong, Meld, Pung
from hkmj_core.state import (
    FromDiscard,
    FromRobbedKong,
    FromWall,
    HandOver,
    State,
    Win,
)
from hkmj_core.tiles import (
    Bonus,
    Direction,
    Dragon,
    DragonColor,
    Flower,
    PlayTile,
    Season,
    Suited,
    Wind,
    bonus_direction,
)


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


type HandFaan = (
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


type HonorFaan = SeatWind | PrevailingWind | DragonMeld


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


type BonusFaan = (
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


type WinConditionFaan = (
    SelfPick
    | WinByKong
    | RobbingTheKong
    | ConcealedHand
    | WinByLastCatch
    | HeavenlyHand
    | EarthlyHand
)

type FaanEntry = HandFaan | HonorFaan | BonusFaan | WinConditionFaan


def default_faan(entry: FaanEntry) -> int:
    """Faan value from the reference tables.

    The match is exhaustive over `FaanEntry`, so the type checker flags any
    pattern added without a valuation.
    """
    match entry:
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
        case HeavenlyHand() | EarthlyHand():
            return 13


@dataclass(frozen=True, slots=True)
class Score:
    entries: tuple[FaanEntry, ...]
    total: int
    """Sum of the entries' faan values, capped at the table's faan cap."""


def score(state: State) -> Score:
    """The best-scoring reading of the winning hand.

    Raises ValueError unless `state.phase` is `HandOver(Win)`.
    """
    match state.phase:
        case HandOver(outcome=Win() as win):
            pass
        case _:
            raise ValueError("only winning states can be scored")
    player = state.players[win.winner]
    readings = [
        _score_reading(state, win, decomp) for decomp in decompositions(player.hand)
    ]
    if not readings:
        raise ValueError("winner's hand has no winning reading")
    return max(readings, key=lambda s: s.total)


def _score_reading(state: State, win: Win, decomp: Decomposition) -> Score:
    player = state.players[win.winner]
    melds = (*player.melds, *decomp.melds)
    entries: tuple[FaanEntry, ...] = (
        *_hand_entries(melds, decomp.eyes),
        *_honor_meld_entries(melds, win.winner, state.prevailing),
        *_bonus_entries(player.bonus, win.winner),
        *_win_condition_entries(state, win, player.melds),
    )
    total = sum(default_faan(entry) for entry in entries)
    return Score(entries=entries, total=min(state.rules.faan_cap, total))


def _hand_entries(melds: tuple[Meld, ...], eyes: PlayTile) -> Iterator[HandFaan]:
    tiles = [t for meld in melds for t in _distinct_tiles(meld)] + [eyes]
    suits = {t.suit for t in tiles if isinstance(t, Suited)}
    has_honors = any(not isinstance(t, Suited) for t in tiles)

    if melds and all(isinstance(m, Chow) for m in melds):
        yield CommonHand()
    if melds and all(isinstance(m, Pung | Kong) for m in melds):
        yield AllInTriplets()
        if all(_is_orphan(t) for t in tiles):
            yield MixedOrphans()
    if len(suits) == 1:
        if has_honors:
            yield MixedOneSuit()
        else:
            yield AllOneSuit()

    dragon_melds = {
        m.tile.color
        for m in melds
        if isinstance(m, Pung | Kong) and isinstance(m.tile, Dragon)
    }
    if len(dragon_melds) == 3:
        yield GreatDragons()
    elif len(dragon_melds) == 2 and isinstance(eyes, Dragon):
        yield SmallDragons()

    wind_melds = {
        m.tile.direction
        for m in melds
        if isinstance(m, Pung | Kong) and isinstance(m.tile, Wind)
    }
    if len(wind_melds) == 3 and isinstance(eyes, Wind):
        yield SmallWinds()


def _honor_meld_entries(
    melds: tuple[Meld, ...], seat: Direction, prevailing: Direction
) -> Iterator[HonorFaan]:
    for meld in melds:
        if not isinstance(meld, Pung | Kong):
            continue
        match meld.tile:
            case Wind(direction=direction):
                if direction == seat:
                    yield SeatWind()
                if direction == prevailing:
                    yield PrevailingWind()
            case Dragon(color=color):
                yield DragonMeld(color)
            case _:
                pass


def _bonus_entries(bonus: tuple[Bonus, ...], seat: Direction) -> Iterator[BonusFaan]:
    if not bonus:
        yield NoBonusTiles()
        return
    flowers = {t.number for t in bonus if isinstance(t, Flower)}
    seasons = {t.number for t in bonus if isinstance(t, Season)}
    if len(flowers) == 4:
        yield AllFlowers()
    elif any(bonus_direction(n) == seat for n in flowers):
        yield FlowerOfOwnWind()
    if len(seasons) == 4:
        yield AllSeasons()
    elif any(bonus_direction(n) == seat for n in seasons):
        yield SeasonOfOwnWind()


def _win_condition_entries(
    state: State, win: Win, declared: tuple[Meld, ...]
) -> Iterator[WinConditionFaan]:
    match win.source:
        case FromWall(replacement=replacement):
            yield SelfPick()
            if replacement:
                yield WinByKong()
        case FromRobbedKong():
            yield RobbingTheKong()
        case FromDiscard():
            pass

    # Concealed kongs do not break a concealed hand.
    if all(isinstance(m, Kong) and m.concealed for m in declared):
        yield ConcealedHand()

    if not state.wall and isinstance(win.source, FromWall | FromDiscard):
        yield WinByLastCatch()

    # First-turn wins, approximated as "no discard is on record anywhere".
    if all(not p.discards for p in state.players.values()):
        dealer = state.rules.seats[0]
        if win.winner == dealer and isinstance(win.source, FromWall):
            yield HeavenlyHand()
        elif isinstance(win.source, FromDiscard) and win.source.discarder == dealer:
            yield EarthlyHand()


def _distinct_tiles(meld: Meld) -> tuple[PlayTile, ...]:
    match meld:
        case Chow():
            return meld.tiles
        case Pung(tile=tile) | Kong(tile=tile):
            return (tile,)


def _is_orphan(tile: PlayTile) -> bool:
    return not isinstance(tile, Suited) or tile.number in (1, 9)
