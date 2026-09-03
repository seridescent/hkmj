"""Game state for a single hand.

The state is a pure value: the engine is `fn(state, actions) -> state`, and
nothing after the deal is random (regular draws come from the front of the
wall, flower/kong replacement draws from the back), so the deal seed is
provenance metadata rather than part of the state.

Player views are projections of this state; redaction of hidden information
(other hands, the wall, and — under table conventions that keep them face
down — concealed kong identities) happens in the view layer, never here.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from hkmj_core.melds import Meld
from hkmj_core.rules import Rules
from hkmj_core.tiles import Bonus, Direction, PlayTile, Tile


@dataclass(frozen=True, slots=True)
class PlayerState:
    hand: tuple[PlayTile, ...]
    """Concealed loose tiles. Always 13 minus 3 per declared meld, except
    that the seat in `AwaitingDiscard` may also hold `Phase.drawn`."""
    melds: tuple[Meld, ...] = ()
    discards: tuple[PlayTile, ...] = ()
    bonus: tuple[Bonus, ...] = ()


@dataclass(frozen=True, slots=True)
class AwaitingDiscard:
    """`seat` holds a 14th tile and must discard (or declare a kong or win)."""

    kind: Literal["awaiting_discard"] = field(kw_only=True, default="awaiting_discard")
    seat: Direction
    drawn: PlayTile | None
    """The tile just drawn, or None when the 14th tile came from a claimed
    discard (the distinction matters for self-pick scoring)."""
    replacement: bool = False
    """Whether `drawn` came from the back of the wall (a kong or bonus-tile
    replacement), which grants win-by-kong faan on a win. Chained provenance
    for win-by-double-kong is intentionally not tracked: too rare to earn
    the complexity."""


@dataclass(frozen=True, slots=True)
class AwaitingClaims:
    """`tile` was just discarded; every other seat may claim it or pass."""

    kind: Literal["awaiting_claims"] = field(kw_only=True, default="awaiting_claims")
    discarder: Direction
    tile: PlayTile


@dataclass(frozen=True, slots=True)
class AwaitingKongRob:
    """`seat` is adding a drawn fourth tile to their exposed pung; any other
    seat may rob `tile` to win. If all pass, the kong completes and `seat`
    takes a replacement draw from the back of the wall.

    Only pung promotions open this window: a kong completed from a claimed
    discard was already claimable in `AwaitingClaims`, and a concealed kong
    is not robbable under this ruleset.
    """

    kind: Literal["awaiting_kong_rob"] = field(
        kw_only=True, default="awaiting_kong_rob"
    )
    seat: Direction
    tile: PlayTile


@dataclass(frozen=True, slots=True)
class FromWall:
    """Self-pick: the winner drew the winning tile (doubles the base payment)."""

    kind: Literal["from_wall"] = field(kw_only=True, default="from_wall")
    replacement: bool = False
    """Winning tile was a kong or bonus-tile replacement draw (win by kong)."""


@dataclass(frozen=True, slots=True)
class FromDiscard:
    kind: Literal["from_discard"] = field(kw_only=True, default="from_discard")
    discarder: Direction


@dataclass(frozen=True, slots=True)
class FromRobbedKong:
    kind: Literal["from_robbed_kong"] = field(kw_only=True, default="from_robbed_kong")
    promoter: Direction


type WinSource = FromWall | FromDiscard | FromRobbedKong


@dataclass(frozen=True, slots=True)
class Win:
    kind: Literal["win"] = field(kw_only=True, default="win")
    winner: Direction
    winning_tile: PlayTile
    source: WinSource


@dataclass(frozen=True, slots=True)
class Goulash:
    """Wall exhausted with no winner."""

    kind: Literal["goulash"] = field(kw_only=True, default="goulash")


type Outcome = Win | Goulash


@dataclass(frozen=True, slots=True)
class HandOver:
    kind: Literal["hand_over"] = field(kw_only=True, default="hand_over")
    outcome: Outcome


type Phase = AwaitingDiscard | AwaitingClaims | AwaitingKongRob | HandOver


@dataclass(frozen=True, slots=True)
class State:
    rules: Rules
    """The fixed configuration this hand was dealt under. Carried in the
    state so a hand can never be stepped under mismatched rules."""
    wall: tuple[Tile, ...]
    """Remaining wall in draw order: regular draws consume the front,
    replacement draws (flowers, kongs) consume the back."""
    prevailing: Direction
    players: Mapping[Direction, PlayerState]
    """Keyed by seat wind; the east seat is the dealer by definition."""
    phase: Phase
