"""Player views: seat-local projections of the game state.

A view is the information set a seat plays from (minus history, which
trajectory records carry): own player state in full, public information
about everyone else, and the phase with the one hidden datum — another
seat's freshly drawn tile — redacted.

Redactions: opponents' concealed hands become tile counts, the wall becomes
a tile count, and a non-viewer's drawn tile becomes `HiddenDraw`. That a
draw happened, whether it was a replacement, and a `None` drawn tile (the
actor claimed instead of drawing) are all public. Declared melds are shown
as-is, including concealed kongs, matching the two-tiles-up table
convention; an all-face-down table would need a redaction knob here.

`HandOver` passes through unredacted-but-unrevealed: the winner and winning
tile are public, other hands stay counts, and any richer end-of-hand
reveal is the consumer's affair, since it holds the true state.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from hkmj_core.melds import Meld
from hkmj_core.rules import Rules
from hkmj_core.state import (
    AwaitingClaims,
    AwaitingDiscard,
    AwaitingKongRob,
    HandOver,
    PlayerState,
    State,
)
from hkmj_core.tiles import Bonus, Direction, PlayTile


@dataclass(frozen=True, slots=True)
class HiddenDraw:
    """Another seat's drawn tile: known to exist, identity unknown."""


type ViewedDraw = PlayTile | HiddenDraw | None


@dataclass(frozen=True, slots=True)
class AwaitingDiscardView:
    seat: Direction
    drawn: ViewedDraw
    replacement: bool = False


type ViewPhase = AwaitingDiscardView | AwaitingClaims | AwaitingKongRob | HandOver


@dataclass(frozen=True, slots=True)
class OpponentView:
    hand_size: int
    """Count of concealed hand tiles."""
    melds: tuple[Meld, ...]
    discards: tuple[PlayTile, ...]
    bonus: tuple[Bonus, ...]


@dataclass(frozen=True, slots=True)
class PlayerView:
    seat: Direction
    rules: Rules
    prevailing: Direction
    wall_count: int
    me: PlayerState
    opponents: Mapping[Direction, OpponentView]
    phase: ViewPhase


def player_view(state: State, seat: Direction) -> PlayerView:
    """Project the state onto what `seat` can observe."""
    phase: ViewPhase
    match state.phase:
        case AwaitingDiscard(seat=actor, drawn=drawn, replacement=replacement):
            viewed = drawn if actor == seat or drawn is None else HiddenDraw()
            phase = AwaitingDiscardView(actor, viewed, replacement)
        case AwaitingClaims() | AwaitingKongRob() | HandOver() as public:
            phase = public
    return PlayerView(
        seat=seat,
        rules=state.rules,
        prevailing=state.prevailing,
        wall_count=len(state.wall),
        me=state.players[seat],
        opponents={
            other: OpponentView(
                hand_size=len(player.hand),
                melds=player.melds,
                discards=player.discards,
                bonus=player.bonus,
            )
            for other, player in state.players.items()
            if other != seat
        },
        phase=phase,
    )
