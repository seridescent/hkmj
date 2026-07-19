"""Faan counting for winning states.

`count_faan` is defined only on states whose phase is `HandOver(Win)` — the
engine constructs those via a single path (`_win_state`), for real wins and
hypothetical ones alike, so gating, winner resolution, and final counting
all agree by construction.

A hand may admit several decompositions; each reading's patterns are
identified here, valued by the rules' injected `FaanCounting`, and the best
reading wins.

Win by double-kong (槓上槓) is intentionally not modeled: it would thread
chained draw provenance through two phase types for a vanishingly rare
event.

TODO: limit hands. They ignore honor and bonus faan, so they arrive as a
separate variant whose pattern type excludes `HonorPattern` and
`BonusPattern` structurally.
TODO: seven pairs and thirteen orphans as additional readings.
TODO: faan-to-points conversion (full/half spicy) and payments, as a layer
on top of `FaanCount`.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from hkmj_core.faan import (
    AllFlowers,
    AllInTriplets,
    AllOneSuit,
    AllSeasons,
    BonusPattern,
    CommonHand,
    ConcealedHand,
    DragonMeld,
    EarthlyHand,
    FlowerOfOwnWind,
    GreatDragons,
    HandPattern,
    HeavenlyHand,
    HonorPattern,
    MixedOneSuit,
    MixedOrphans,
    NoBonusTiles,
    Pattern,
    PrevailingWind,
    RobbingTheKong,
    SeasonOfOwnWind,
    SeatWind,
    SelfPick,
    SmallDragons,
    SmallWinds,
    WinByKong,
    WinByLastCatch,
    WinConditionPattern,
)
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
    Flower,
    PlayTile,
    Season,
    Suited,
    Wind,
    bonus_direction,
)


@dataclass(frozen=True, slots=True)
class FaanCount:
    patterns: tuple[Pattern, ...]
    total: int
    """The rules' valuation of the patterns (capping included)."""


def count_faan(state: State) -> FaanCount:
    """The best-counting reading of the winning hand.

    Raises ValueError unless `state.phase` is `HandOver(Win)`.
    """
    match state.phase:
        case HandOver(outcome=Win() as win):
            pass
        case _:
            raise ValueError("only winning states can be counted")
    player = state.players[win.winner]
    readings = [
        _count_reading(state, win, decomp) for decomp in decompositions(player.hand)
    ]
    if not readings:
        raise ValueError("winner's hand has no winning reading")
    return max(readings, key=lambda count: count.total)


def _count_reading(state: State, win: Win, decomp: Decomposition) -> FaanCount:
    player = state.players[win.winner]
    melds = (*player.melds, *decomp.melds)
    patterns: tuple[Pattern, ...] = (
        *_hand_patterns(melds, decomp.eyes),
        *_honor_meld_patterns(melds, win.winner, state.prevailing),
        *_bonus_patterns(player.bonus, win.winner),
        *_win_condition_patterns(state, win, player.melds),
    )
    return FaanCount(patterns=patterns, total=state.rules.faan(patterns))


def _hand_patterns(melds: tuple[Meld, ...], eyes: PlayTile) -> Iterator[HandPattern]:
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


def _honor_meld_patterns(
    melds: tuple[Meld, ...], seat: Direction, prevailing: Direction
) -> Iterator[HonorPattern]:
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


def _bonus_patterns(
    bonus: tuple[Bonus, ...], seat: Direction
) -> Iterator[BonusPattern]:
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


def _win_condition_patterns(
    state: State, win: Win, declared: tuple[Meld, ...]
) -> Iterator[WinConditionPattern]:
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
