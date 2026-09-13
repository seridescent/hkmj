import json
from dataclasses import asdict, replace
from typing import Literal

import pytest
from hkmj_core import (
    DIRECTIONS,
    AwaitingClaims,
    Direction,
    Flower,
    FromDiscard,
    FromRobbedKong,
    FromWall,
    Goulash,
    HandOver,
    PlayerState,
    Rules,
    Scoring,
    State,
    Suited,
    Win,
    Wind,
    WinSource,
    full_spicy,
    half_spicy,
    settle,
    tile_sort_key,
)

# The reference half-spicy table, verbatim.
HALF_SPICY = {
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


def test_half_spicy_matches_the_reference_table() -> None:
    assert half_spicy == HALF_SPICY


def test_rules_and_scoring_are_json_data() -> None:
    configuration = {
        "rules": asdict(Rules(faan_cap=8)),
        "scoring": asdict(Scoring(full_spicy, "discarder_pays_all")),
    }
    assert json.loads(json.dumps(configuration))["rules"]["faan_cap"] == 8


# Common hand, concealed, no bonus faan: 2 faan by discard, 3 by self-pick
# (the reference's own payment examples use a 3-faan, 8-point hand).
HAND = (
    *(Suited("dot", n) for n in (1, 2, 3)),
    *(Suited("bamboo", n) for n in (4, 5, 6)),
    Suited("myriad", 7),
    Suited("myriad", 7),
)


def won_state(source: WinSource) -> State:
    players = {d: PlayerState(hand=()) for d in DIRECTIONS}
    players["south"] = PlayerState(
        hand=tuple(sorted(HAND, key=tile_sort_key)), bonus=(Flower(3),)
    )
    players["west"] = PlayerState(hand=(), discards=(Suited("dot", 1),))
    return State(
        rules=Rules(),
        wall=(Wind("north"),),
        prevailing="east",
        players=players,
        phase=HandOver(Win("south", HAND[0], source)),
    )


def paid(
    source: WinSource,
    payments: Literal["discarder_pays_all", "discarder_pays_half"],
) -> dict[Direction, int]:
    scoring = Scoring(points=full_spicy, payments=payments)
    return dict(settle(scoring, won_state(source)))


def test_discarder_pays_all() -> None:
    # 2 faan -> 4 points, all from the discarder.
    assert paid(FromDiscard("east"), "discarder_pays_all") == {
        "east": -4,
        "south": 4,
        "west": 0,
        "north": 0,
    }


def test_discarder_pays_half() -> None:
    # 2 faan -> 4 points: discarder 2, bystanders 1 each.
    assert paid(FromDiscard("east"), "discarder_pays_half") == {
        "east": -2,
        "south": 4,
        "west": -1,
        "north": -1,
    }


def test_self_pick_charges_everyone_half() -> None:
    # 3 faan -> 8 points -> 12 to the winner, 4 from each seat, mirroring
    # the reference's worked example.
    assert paid(FromWall(), "discarder_pays_all") == {
        "east": -4,
        "south": 12,
        "west": -4,
        "north": -4,
    }


def test_robbed_kong_promoter_is_liable() -> None:
    # 3 faan (robbing the kong adds one) -> 8 points from the promoter.
    assert paid(FromRobbedKong("north"), "discarder_pays_all") == {
        "east": 0,
        "south": 8,
        "west": 0,
        "north": -8,
    }


def test_goulash_settles_to_zeros() -> None:
    state = replace(won_state(FromWall()), phase=HandOver(Goulash()))
    scoring = Scoring(points=half_spicy, payments="discarder_pays_all")
    assert dict(settle(scoring, state)) == {d: 0 for d in DIRECTIONS}


def test_settle_requires_a_finished_hand() -> None:
    state = replace(
        won_state(FromWall()), phase=AwaitingClaims("east", Suited("dot", 5))
    )
    scoring = Scoring(points=full_spicy, payments="discarder_pays_all")
    with pytest.raises(ValueError):
        settle(scoring, state)
