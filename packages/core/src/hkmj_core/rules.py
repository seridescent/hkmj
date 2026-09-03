"""Rules configuration.

House-rule knobs and structural parameters. Fixed at deal time and carried
in `State`, so a hand can never be stepped under rules other than the ones
it was dealt with; transitions never modify them.
"""

from dataclasses import dataclass

from hkmj_core.tiles import DIRECTIONS, Direction


@dataclass(frozen=True, slots=True)
class Rules:
    min_faan: int = 3
    """Table minimum for a declarable win; 0 permits chicken hands."""

    faan_cap: int = 13
    """Maximum faan awarded to a winning reading after its patterns are
    summed. Faan-to-points conversion (full or half spicy) is deliberately
    not part of the rules: `min_faan` gating and highest-faan winner
    resolution compare in faan."""

    seats: tuple[Direction, ...] = DIRECTIONS
    """Occupied seats in turn order; seats[0] is the dealer. Fewer than four
    seats plays a reduced-player game (wall composition currently
    unchanged)."""

    melds_to_win: int = 4
    """k: a winning hand is k melds plus eyes, so players hold 3k + 1 tiles.
    Smaller k plays a shorter, motif-preserving game; limit hands only fire
    with four melds, so reduced games never reward limit-chasing."""
