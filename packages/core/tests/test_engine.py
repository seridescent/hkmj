import random
from collections import Counter

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hkmj_core import (
    AwaitingClaims,
    AwaitingDiscard,
    AwaitingKongRob,
    Chow,
    ClaimPung,
    Discard,
    HandOver,
    Kong,
    Meld,
    Pass,
    PlayTile,
    Pung,
    Rules,
    Scoring,
    State,
    Suited,
    Win,
    count_faan,
    deal,
    full_spicy,
    full_tile_set,
    meld_sort_key,
    settle,
    step,
    tile_sort_key,
    valid_actions,
)

SCORING = Scoring(points=full_spicy, payments="discarder_pays_half")

RULESETS = (
    Rules(),
    # Reduced games: short trajectories, and with chicken hands legal
    # (min_faan=0) random play actually wins sometimes, so the win paths
    # get exercised too.
    Rules(seats=("east", "west"), melds_to_win=2, min_faan=0),
    Rules(seats=("east", "south", "west"), melds_to_win=3, min_faan=0),
)


def owned_tiles(meld: Meld) -> list[PlayTile]:
    match meld:
        case Chow():
            return list(meld.tiles)
        case Pung(tile=tile):
            return [tile] * 3
        case Kong(tile=tile):
            return [tile] * 4


def assert_invariants(state: State) -> None:
    # Tile conservation: every tile of the set is somewhere, exactly once.
    seen = Counter(state.wall)
    for player in state.players.values():
        seen.update(player.hand)
        seen.update(player.discards)
        seen.update(player.bonus)
        for meld in player.melds:
            seen.update(owned_tiles(meld))
    match state.phase:
        case AwaitingDiscard(drawn=tile) if tile is not None:
            seen[tile] += 1
        case AwaitingClaims(tile=tile) | AwaitingKongRob(tile=tile):
            seen[tile] += 1
        case _:
            pass
    assert seen == Counter(full_tile_set())

    # Hand sizes: base holding everywhere, one extra for the acting seat's
    # (drawn-inclusive) pool and for a winner's absorbed winning tile.
    base = 3 * state.rules.melds_to_win + 1
    for seat, player in state.players.items():
        held = len(player.hand) + 3 * len(player.melds)
        match state.phase:
            case AwaitingDiscard(seat=actor, drawn=drawn) if actor == seat:
                held += 1 if drawn is not None else 0
                expected = base + 1
            case HandOver(outcome=Win(winner=winner)) if winner == seat:
                expected = base + 1
            case _:
                expected = base
        assert held == expected, (seat, state.phase)

        # Canonical form everywhere.
        assert player.hand == tuple(sorted(player.hand, key=tile_sort_key))
        assert player.melds == tuple(sorted(player.melds, key=meld_sort_key))
        assert player.bonus == tuple(sorted(player.bonus, key=tile_sort_key))

    # Any win the engine allowed must satisfy the table minimum, and every
    # finished hand settles to zero-sum payments over exactly the seats.
    match state.phase:
        case HandOver(outcome=outcome):
            deltas = settle(SCORING, state)
            assert set(deltas) == set(state.rules.seats)
            assert sum(deltas.values()) == 0
            if isinstance(outcome, Win):
                assert count_faan(state).total >= state.rules.min_faan
                assert deltas[outcome.winner] >= 0
        case _:
            pass


@given(
    seed=st.integers(0, 2**32 - 1),
    rules=st.sampled_from(RULESETS),
)
@settings(max_examples=30, deadline=None)
def test_random_playouts_terminate_with_invariants(seed: int, rules: Rules) -> None:
    rng = random.Random(seed)
    state = deal(rules, rng)
    assert_invariants(state)
    for _ in range(600):
        if isinstance(state.phase, HandOver):
            break
        chosen = {
            seat: rng.choice(sorted(acts, key=repr))
            for seat, acts in valid_actions(state).items()
        }
        state, _ = step(state, chosen)
        assert_invariants(state)
    assert isinstance(state.phase, HandOver)


def test_deal_is_deterministic() -> None:
    assert deal(Rules(), random.Random(7)) == deal(Rules(), random.Random(7))


def test_step_validates_actions() -> None:
    state = deal(Rules(), random.Random(0))
    assert isinstance(state.phase, AwaitingDiscard)
    with pytest.raises(ValueError):
        step(state, {})
    with pytest.raises(ValueError):
        step(state, {state.phase.seat: Pass()})


def test_step_reports_the_action_selected_by_resolution() -> None:
    state = deal(Rules(min_faan=0, melds_to_win=1), random.Random(27))
    discard = Discard(Suited("dot", 7))
    claims, resolved = step(state, {"east": discard})
    assert resolved == ("east", discard)

    passed = {seat: Pass() for seat in valid_actions(claims)}
    _, resolved = step(claims, passed)
    assert resolved is None

    pung = {
        seat: ClaimPung() if seat == "west" else Pass()
        for seat in valid_actions(claims)
    }
    _, resolved = step(claims, pung)
    assert resolved == ("west", ClaimPung())
