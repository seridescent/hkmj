"""Player action types.

An action is one seat's input to the transition function. Which union answers
which phase: `TurnAction` for `AwaitingDiscard`, `ClaimAction` for
`AwaitingClaims`, `RobAction` for `AwaitingKongRob`. `DeclareWin` appears in
all three — the phase determines whether it means self-pick, winning by
discard, or robbing the kong.
"""

from dataclasses import dataclass, field
from typing import Literal

from hkmj_core.melds import ChowStart
from hkmj_core.tiles import PlayTile


@dataclass(frozen=True, slots=True)
class Discard:
    kind: Literal["discard"] = field(kw_only=True, default="discard")
    tile: PlayTile


@dataclass(frozen=True, slots=True)
class DeclareConcealedKong:
    """Set aside four self-drawn copies of `tile` and draw a replacement."""

    kind: Literal["declare_concealed_kong"] = field(
        kw_only=True, default="declare_concealed_kong"
    )
    tile: PlayTile


@dataclass(frozen=True, slots=True)
class PromoteKong:
    """Add the held fourth copy of `tile` to an exposed pung, opening the
    robbing window."""

    kind: Literal["promote_kong"] = field(kw_only=True, default="promote_kong")
    tile: PlayTile


@dataclass(frozen=True, slots=True)
class DeclareWin:
    """Declare a winning hand. Carries no payload: the engine verifies and
    decomposes the hand itself."""

    kind: Literal["declare_win"] = field(kw_only=True, default="declare_win")


@dataclass(frozen=True, slots=True)
class Pass:
    """Decline to claim."""

    kind: Literal["pass"] = field(kw_only=True, default="pass")


@dataclass(frozen=True, slots=True)
class ClaimChow:
    """Claim the discard to complete the chow starting at `start`.

    The payload disambiguates: a discarded tile can extend up to three
    different chows. Only the discarder's right-hand neighbour may chow.
    """

    kind: Literal["claim_chow"] = field(kw_only=True, default="claim_chow")
    start: ChowStart


@dataclass(frozen=True, slots=True)
class ClaimPung:
    """Claim the discard to expose a pung with two matching hand tiles."""

    kind: Literal["claim_pung"] = field(kw_only=True, default="claim_pung")


@dataclass(frozen=True, slots=True)
class ClaimKong:
    """Claim the discard to expose a kong with three matching hand tiles."""

    kind: Literal["claim_kong"] = field(kw_only=True, default="claim_kong")


type TurnAction = Discard | DeclareConcealedKong | PromoteKong | DeclareWin
type ClaimAction = Pass | ClaimChow | ClaimPung | ClaimKong | DeclareWin
type RobAction = Pass | DeclareWin
type Action = TurnAction | ClaimAction
