"""Scoring: converting faan to points and settling payments.

Terminology per the reference: a faan count converts exponentially into
*points* — the money-analog score — via a "spicy" table, and payments then
move points between seats, always summing to zero.

Stake scaling ("divide by a constant") is intentionally out of scope: it is
an affine adjustment at the real-money boundary and does not change the
shape of the payoff curve. Old-style (pre-faan) scoring and penalty
payments are likewise unsupported.

`Scoring` has no defaults: the spicy table and payment liability are table
agreements with several live conventions and no canonical answer, so
callers must choose.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from hkmj_core.counting import count_faan
from hkmj_core.state import (
    FromDiscard,
    FromRobbedKong,
    FromWall,
    HandOver,
    State,
    Win,
)
from hkmj_core.tiles import Direction

type PointsTable = Mapping[int, int]
"""Serializable mapping from a faan total to points."""


full_spicy: PointsTable = {
    0: 1,
    1: 2,
    2: 4,
    3: 8,
    4: 16,
    5: 32,
    6: 64,
    7: 128,
    8: 256,
    9: 512,
    10: 1024,
    11: 2048,
    12: 4096,
    13: 8192,
}
"""Points double with every faan."""


half_spicy: PointsTable = {
    0: 1,
    1: 2,
    2: 4,
    3: 8,
    4: 16,
    5: 24,
    6: 32,
    7: 48,
    8: 64,
    9: 96,
    10: 128,
    11: 192,
    12: 256,
    13: 384,
}
"""Full spicy through 4 faan, then alternating 1.5x and 4/3x steps."""


@dataclass(frozen=True, slots=True)
class Scoring:
    points: PointsTable
    payments: Literal["discarder_pays_all", "discarder_pays_half"]
    """Liability for a win by discard (a robbed kong's promoter is liable
    like a discarder): the payer covers everything, or half, with the rest
    split evenly across the bystanders."""


def settle(scoring: Scoring, state: State) -> Mapping[Direction, int]:
    """Zero-sum point deltas for a finished hand; all zeros for a goulash.

    Self-pick charges every other seat half the table points (1.5x the
    table total with three payers, per the reference). Shares use floor
    division and the liable payer covers any remainder, so deltas sum to
    zero even for degenerate sub-4-point pots.

    Raises ValueError unless the hand is over.
    """
    match state.phase:
        case HandOver(outcome=Win() as win):
            pass
        case HandOver():
            return {seat: 0 for seat in state.rules.seats}
        case _:
            raise ValueError("only finished hands can be settled")

    points = scoring.points[count_faan(state).total]
    others = [seat for seat in state.rules.seats if seat != win.winner]
    deltas: dict[Direction, int]
    match win.source:
        case FromWall():
            deltas = {seat: -(points // 2) for seat in others}
        case FromDiscard(discarder=payer) | FromRobbedKong(promoter=payer):
            if scoring.payments == "discarder_pays_all":
                deltas = {seat: 0 for seat in others}
                deltas[payer] = -points
            else:
                bystanders = [seat for seat in others if seat != payer]
                share = points // (2 * len(bystanders)) if bystanders else 0
                deltas = {seat: -share for seat in bystanders}
                deltas[payer] = -(points - share * len(bystanders))
    deltas[win.winner] = -sum(deltas.values())
    return deltas
