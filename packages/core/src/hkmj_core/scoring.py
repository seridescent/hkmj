"""Faan scoring for winning states.

`score` is defined only on states whose phase is `HandOver(Win)` — the
engine constructs those via a single path (`_win_state`), for real wins and
hypothetical ones alike, so gating, winner resolution, and final scoring
all agree by construction.

A hand may admit several decompositions; each is scored independently and
the best reading wins. Entries are itemized so consumers (rewards, UIs,
eval graders) can see exactly which patterns fired, not just a number.

TODO: limit hands (score as hand + winning condition only, ignoring
wind/dragon/flower faan).
TODO: seven pairs and thirteen orphans as additional readings.
TODO: win by double-kong (8 faan) once chained draw provenance exists.
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
    Flower,
    PlayTile,
    Season,
    Suited,
    Wind,
    bonus_direction,
)


@dataclass(frozen=True, slots=True)
class FaanEntry:
    name: str
    faan: int


@dataclass(frozen=True, slots=True)
class Score:
    entries: tuple[FaanEntry, ...]
    total: int
    """Sum of entries, capped at the table's faan cap."""


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
    entries = (
        *_hand_entries(melds, decomp.eyes),
        *_honor_meld_entries(melds, win.winner, state.prevailing),
        *_bonus_entries(player.bonus, win.winner),
        *_win_condition_entries(state, win, player.melds),
    )
    return Score(
        entries=entries,
        total=min(state.rules.faan_cap, sum(e.faan for e in entries)),
    )


def _hand_entries(melds: tuple[Meld, ...], eyes: PlayTile) -> Iterator[FaanEntry]:
    tiles = [t for meld in melds for t in _distinct_tiles(meld)] + [eyes]
    suits = {t.suit for t in tiles if isinstance(t, Suited)}
    has_honors = any(not isinstance(t, Suited) for t in tiles)

    if melds and all(isinstance(m, Chow) for m in melds):
        yield FaanEntry("common hand", 1)
    if melds and all(isinstance(m, Pung | Kong) for m in melds):
        yield FaanEntry("all in triplets", 3)
        if all(_is_orphan(t) for t in tiles):
            yield FaanEntry("mixed orphans", 1)
    if len(suits) == 1:
        if has_honors:
            yield FaanEntry("mixed one suit", 3)
        else:
            yield FaanEntry("all one suit", 7)

    dragon_melds = {
        m.tile.color
        for m in melds
        if isinstance(m, Pung | Kong) and isinstance(m.tile, Dragon)
    }
    if len(dragon_melds) == 3:
        yield FaanEntry("great dragons", 5)
    elif len(dragon_melds) == 2 and isinstance(eyes, Dragon):
        yield FaanEntry("small dragons", 3)

    wind_melds = {
        m.tile.direction
        for m in melds
        if isinstance(m, Pung | Kong) and isinstance(m.tile, Wind)
    }
    if len(wind_melds) == 3 and isinstance(eyes, Wind):
        yield FaanEntry("small winds", 6)


def _honor_meld_entries(
    melds: tuple[Meld, ...], seat: Direction, prevailing: Direction
) -> Iterator[FaanEntry]:
    for meld in melds:
        if not isinstance(meld, Pung | Kong):
            continue
        match meld.tile:
            case Wind(direction=direction):
                if direction == seat:
                    yield FaanEntry("seat wind", 1)
                if direction == prevailing:
                    yield FaanEntry("prevailing wind", 1)
            case Dragon(color=color):
                yield FaanEntry(f"{color} dragon", 1)
            case _:
                pass


def _bonus_entries(bonus: tuple[Bonus, ...], seat: Direction) -> Iterator[FaanEntry]:
    if not bonus:
        yield FaanEntry("no bonus tiles", 1)
        return
    flowers = {t.number for t in bonus if isinstance(t, Flower)}
    seasons = {t.number for t in bonus if isinstance(t, Season)}
    if len(flowers) == 4:
        yield FaanEntry("all flowers", 2)
    elif any(bonus_direction(n) == seat for n in flowers):
        yield FaanEntry("flower of own wind", 1)
    if len(seasons) == 4:
        yield FaanEntry("all seasons", 2)
    elif any(bonus_direction(n) == seat for n in seasons):
        yield FaanEntry("season of own wind", 1)


def _win_condition_entries(
    state: State, win: Win, declared: tuple[Meld, ...]
) -> Iterator[FaanEntry]:
    match win.source:
        case FromWall(replacement=replacement):
            yield FaanEntry("self-pick", 1)
            if replacement:
                yield FaanEntry("win by kong", 1)
        case FromRobbedKong():
            yield FaanEntry("robbing the kong", 1)
        case FromDiscard():
            pass

    # Concealed kongs do not break a concealed hand.
    if all(isinstance(m, Kong) and m.concealed for m in declared):
        yield FaanEntry("concealed hand", 1)

    if not state.wall and isinstance(win.source, FromWall | FromDiscard):
        yield FaanEntry("win by last catch", 1)

    # First-turn wins, approximated as "no discard is on record anywhere".
    if all(not p.discards for p in state.players.values()):
        dealer = state.rules.seats[0]
        if win.winner == dealer and isinstance(win.source, FromWall):
            yield FaanEntry("heavenly hand", 13)
        elif isinstance(win.source, FromDiscard) and win.source.discarder == dealer:
            yield FaanEntry("earthly hand", 13)


def _distinct_tiles(meld: Meld) -> tuple[PlayTile, ...]:
    match meld:
        case Chow():
            return meld.tiles
        case Pung(tile=tile) | Kong(tile=tile):
            return (tile,)


def _is_orphan(tile: PlayTile) -> bool:
    return not isinstance(tile, Suited) or tile.number in (1, 9)
