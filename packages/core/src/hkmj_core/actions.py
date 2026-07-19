"""Player action types.

An action is one seat's input to the transition function. Which union answers
which phase: `TurnAction` for `AwaitingDiscard`, `ClaimAction` for
`AwaitingClaims`, `RobAction` for `AwaitingKongRob`. `DeclareWin` appears in
all three — the phase determines whether it means self-pick, winning by
discard, or robbing the kong.
"""

from dataclasses import dataclass

from hkmj_core.melds import ChowStart
from hkmj_core.tiles import PlayTile


@dataclass(frozen=True, slots=True)
class Discard:
    tile: PlayTile


@dataclass(frozen=True, slots=True)
class DeclareConcealedKong:
    """Set aside four self-drawn copies of `tile` and draw a replacement."""

    tile: PlayTile


@dataclass(frozen=True, slots=True)
class PromoteKong:
    """Add the held fourth copy of `tile` to an exposed pung, opening the
    robbing window."""

    tile: PlayTile


@dataclass(frozen=True, slots=True)
class DeclareWin:
    """Declare a winning hand. Carries no payload: the engine verifies and
    decomposes the hand itself."""


@dataclass(frozen=True, slots=True)
class Pass:
    """Decline to claim."""


@dataclass(frozen=True, slots=True)
class ClaimChow:
    """Claim the discard to complete the chow starting at `start`.

    The payload disambiguates: a discarded tile can extend up to three
    different chows. Only the discarder's right-hand neighbour may chow.
    """

    start: ChowStart


@dataclass(frozen=True, slots=True)
class ClaimPung:
    """Claim the discard to expose a pung with two matching hand tiles."""


@dataclass(frozen=True, slots=True)
class ClaimKong:
    """Claim the discard to expose a kong with three matching hand tiles."""


type TurnAction = Discard | DeclareConcealedKong | PromoteKong | DeclareWin
type ClaimAction = Pass | ClaimChow | ClaimPung | ClaimKong | DeclareWin
type RobAction = Pass | DeclareWin
type Action = TurnAction | ClaimAction
