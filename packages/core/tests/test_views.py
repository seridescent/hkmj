import random

from hkmj_core import (
    DIRECTIONS,
    AwaitingClaims,
    AwaitingDiscard,
    AwaitingDiscardView,
    Discard,
    HiddenDraw,
    Rules,
    deal,
    player_view,
    step,
    valid_actions,
)


def test_views_redact_exactly_the_hidden_information() -> None:
    state = deal(Rules(), random.Random(11))
    assert isinstance(state.phase, AwaitingDiscard)
    dealer, drawn = state.phase.seat, state.phase.drawn

    dealer_view = player_view(state, dealer)
    assert isinstance(dealer_view.phase, AwaitingDiscardView)
    assert dealer_view.phase.drawn == drawn
    assert dealer_view.me == state.players[dealer]
    assert dealer_view.wall_count == len(state.wall)
    assert dealer not in dealer_view.opponents

    other = next(d for d in DIRECTIONS if d != dealer)
    view = player_view(state, other)
    assert isinstance(view.phase, AwaitingDiscardView)
    assert view.phase.drawn == HiddenDraw()
    assert set(view.opponents) == set(DIRECTIONS) - {other}
    for seat, opponent in view.opponents.items():
        assert opponent.hand_size == len(state.players[seat].hand)
        assert not hasattr(opponent, "hand")


def test_public_phases_pass_through() -> None:
    state = deal(Rules(), random.Random(11))
    (seat,) = valid_actions(state)
    discard = next(
        action
        for action in sorted(valid_actions(state)[seat], key=repr)
        if isinstance(action, Discard)
    )
    state, _ = step(state, {seat: discard})
    assert isinstance(state.phase, AwaitingClaims)
    for direction in DIRECTIONS:
        assert player_view(state, direction).phase == state.phase
