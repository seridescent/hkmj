"""Faan counting for winning states.

`count_faan` is defined only on states whose phase is `HandOver(Win)` — the
engine constructs those via a single path (`_win_state`), for real wins and
hypothetical ones alike, so gating, winner resolution, and final counting
all agree by construction.

A hand may admit several readings — ordinary decompositions and limit
criteria — each valued by the exhaustive `pattern_faan` match and capped by
the rules, and the best reading wins. A limit reading is ineligible for hand,
honor, and bonus faan (win-condition faan still stacks), which `LimitCount`'s
shape encodes; it competes with ordinary readings on value like any other
reading.

Win by double-kong (槓上槓) is intentionally not modeled: it would thread
chained draw provenance through two phase types for a vanishingly rare
event. Seven pairs is likewise intentionally unsupported: a variant hand
this ruleset does not play.

Faan-to-points conversion and payments remain a separate scoring layer on
top of `FaanCount`.
"""

from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from hkmj_core.faan import (
    AllFlowers,
    AllHonorTiles,
    AllInTriplets,
    AllKongs,
    AllOneSuit,
    AllSeasons,
    BonusPattern,
    CommonHand,
    ConcealedHand,
    DragonMeld,
    EarthlyHand,
    FlowerOfOwnWind,
    GreatDragons,
    GreatWinds,
    HandPattern,
    HeavenlyHand,
    HonorPattern,
    LimitHand,
    MixedOneSuit,
    MixedOrphans,
    NineGates,
    NoBonusTiles,
    Orphans,
    Pattern,
    PrevailingWind,
    RobbingTheKong,
    SeasonOfOwnWind,
    SeatWind,
    SelfPick,
    SelfTriplets,
    SmallDragons,
    SmallWinds,
    ThirteenOrphans,
    WinByKong,
    WinByLastCatch,
    WinConditionPattern,
    pattern_faan,
)
from hkmj_core.hands import ORPHAN_KINDS, Decomposition, decompositions
from hkmj_core.melds import Chow, Kong, Meld, Pung
from hkmj_core.state import (
    FromDiscard,
    FromRobbedKong,
    FromWall,
    HandOver,
    PlayerState,
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
class OrdinaryCount:
    patterns: tuple[Pattern, ...]
    total: int
    """The rules' valuation of the patterns (capping included)."""


@dataclass(frozen=True, slots=True)
class LimitCount:
    hand: LimitHand
    conditions: tuple[WinConditionPattern, ...]
    """Only win-condition faan stacks with a limit hand; ineligibility for
    hand, honor, and bonus faan is what this type's shape encodes."""
    total: int


type FaanCount = OrdinaryCount | LimitCount


def is_thirteen_orphans(tiles: Iterable[PlayTile]) -> bool:
    """Whether the concealed tiles are the thirteen-orphans limit hand:
    every terminal and honor kind, exactly one of them duplicated."""
    pool = list(tiles)
    return len(pool) == 14 and set(pool) == ORPHAN_KINDS


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
    conditions = tuple(_win_condition_patterns(state, win, player.melds))

    counts: list[FaanCount] = []
    for decomp in decompositions(player.hand):
        melds = (*player.melds, *decomp.melds)
        patterns: tuple[Pattern, ...] = (
            *_hand_patterns(melds, decomp.eyes),
            *_honor_meld_patterns(melds, win.winner, state.prevailing),
            *_bonus_patterns(player.bonus, win.winner),
            *conditions,
        )
        counts.append(OrdinaryCount(patterns, _count_patterns(state, patterns)))

        for limit in _decomposition_limit_hands(win, player.melds, decomp):
            counts.append(_limit_count(state, limit, conditions))

    for limit in _special_shape_limit_hands(player):
        counts.append(_limit_count(state, limit, conditions))

    if not counts:
        raise ValueError("winner's hand has no winning reading")
    return max(counts, key=lambda count: count.total)


_DEFINITIONALLY_CONCEALED = (SelfTriplets, NineGates, ThirteenOrphans)
"""Limit hands that are concealed by definition and so earn no separate
concealed-hand faan."""


def _limit_count(
    state: State, hand: LimitHand, conditions: tuple[WinConditionPattern, ...]
) -> LimitCount:
    if isinstance(hand, _DEFINITIONALLY_CONCEALED):
        conditions = tuple(c for c in conditions if not isinstance(c, ConcealedHand))
    patterns: tuple[Pattern, ...] = (hand, *conditions)
    return LimitCount(hand, conditions, _count_patterns(state, patterns))


def _count_patterns(state: State, patterns: tuple[Pattern, ...]) -> int:
    return min(state.rules.faan_cap, sum(map(pattern_faan, patterns)))


def _decomposition_limit_hands(
    win: Win, declared: tuple[Meld, ...], decomp: Decomposition
) -> Iterator[LimitHand]:
    melds = (*declared, *decomp.melds)
    # Limit criteria are defined for the standard four-meld hand. Reduced
    # games deliberately never fire them: two concealed pungs at k = 2
    # should not teach limit-chasing that full-game play won't reward.
    if len(melds) != 4:
        return
    tiles = [t for meld in melds for t in _distinct_tiles(meld)] + [decomp.eyes]

    if all(not isinstance(t, Suited) for t in tiles):
        yield AllHonorTiles()

    if all(isinstance(t, Suited) and t.number in (1, 9) for t in tiles) and all(
        isinstance(m, Pung | Kong) for m in melds
    ):
        yield Orphans()

    if all(isinstance(m, Kong) for m in melds):
        yield AllKongs()

    wind_melds = {
        m.tile.direction
        for m in melds
        if isinstance(m, Pung | Kong) and isinstance(m.tile, Wind)
    }
    if len(wind_melds) == 4:
        yield GreatWinds()

    if (
        all(isinstance(m, Kong) and m.concealed for m in declared)
        and all(isinstance(m, Pung) for m in decomp.melds)
        and (
            isinstance(win.source, FromWall)
            or (isinstance(win.source, FromDiscard) and win.winning_tile == decomp.eyes)
        )
    ):
        yield SelfTriplets()


def _special_shape_limit_hands(player: PlayerState) -> Iterator[LimitHand]:
    """Limit hands identified from the whole concealed hand rather than one
    decomposition; both require a fully concealed hand."""
    if player.melds:
        return
    if is_thirteen_orphans(player.hand):
        yield ThirteenOrphans()
    if _is_nine_gates(player.hand):
        yield NineGates()


def _is_nine_gates(tiles: tuple[PlayTile, ...]) -> bool:
    suited = [t for t in tiles if isinstance(t, Suited)]
    if len(suited) != len(tiles) or len({t.suit for t in suited}) != 1:
        return False

    counts = Counter(t.number for t in suited)
    counts.subtract(Counter({1: 3, 9: 3, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1}))
    return all(n >= 0 for n in counts.values()) and counts.total() == 1


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
