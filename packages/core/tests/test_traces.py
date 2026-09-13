import random

from hkmj_core import (
    Action,
    Direction,
    HandOver,
    HandTrace,
    Pass,
    Rules,
    deal,
    step,
    valid_actions,
)
from pydantic import TypeAdapter


def test_hand_trace_serializes_and_plays_native_actions_to_end() -> None:
    initial = deal(Rules(min_faan=0, melds_to_win=1), random.Random(3))
    state = initial
    batches: list[dict[Direction, Action]] = []
    while not isinstance(state.phase, HandOver):
        actions = {
            seat: next(
                (action for action in legal if isinstance(action, Pass)),
                min(legal, key=repr),
            )
            for seat, legal in valid_actions(state).items()
        }
        batches.append(actions)
        state, _ = step(state, actions)

    adapter = TypeAdapter(HandTrace)
    trace = HandTrace(initial, tuple(batches))
    decoded = adapter.validate_json(adapter.dump_json(trace))

    assert decoded == trace
    assert decoded.play_to_end() == state
