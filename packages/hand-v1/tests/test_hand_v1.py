import asyncio
import random
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import cast

from pydantic import TypeAdapter

import verifiers.v1 as vf
from hkmj_core import (
    Action,
    DIRECTIONS,
    Direction,
    HandTrace,
    Pass,
    Rules,
    State,
    deal,
    player_view,
    step,
    valid_actions,
)
from hkmj_hand_v1 import HandData, HandEnv, HandPrompt, HandTaskset
from hkmj_hand_v1.presentation import legal_action_map, parse_action
from hkmj_hand_v1.taskset import HandEnvConfig, HandTasksetConfig


def test_seeded_task_materialization_is_native_and_deterministic() -> None:
    taskset = HandTaskset(HandTasksetConfig(start_seed=11))
    tasks = list(taskset.head(2))

    assert [task.data.seed for task in tasks] == [11, 12]
    assert isinstance(tasks[0].data.initial_state, State)
    assert tasks[0].data.initial_state == deal(Rules(), "east", random.Random(11))

    encoded = tasks[0].data.model_dump_json()
    decoded = HandData.model_validate_json(encoded)
    assert decoded == tasks[0].data
    assert '"kind":"awaiting_discard"' in encoded


def test_hand_trace_serializes_and_replays_native_actions() -> None:
    initial = deal(Rules(min_faan=0, melds_to_win=1), "east", random.Random(3))
    state = initial
    batches: list[dict[Direction, Action]] = []
    for _ in range(4):
        available = valid_actions(state)
        if not available:
            break
        actions = {
            seat: next(
                (action for action in legal if isinstance(action, Pass)),
                min(legal, key=repr),
            )
            for seat, legal in available.items()
        }
        batches.append(actions)
        state, _ = step(state, actions)

    hand_trace = HandTrace(initial, tuple(batches))
    adapter = TypeAdapter(HandTrace)
    decoded = adapter.validate_json(adapter.dump_json(hand_trace))

    assert decoded == hand_trace
    assert decoded.replay() == state


def test_bracket_parser_allows_reasoning_but_rejects_ambiguity() -> None:
    state = deal(Rules(), "east", random.Random(5))
    seat = state.rules.seats[0]
    legal = legal_action_map(
        valid_actions(state)[seat],
        player_view(state, seat),
        HandPrompt(),
    )
    label = next(iter(legal))

    assert (
        parse_action(f"Because of the shape, I choose [{label}].", legal)
        == legal[label]
    )
    assert parse_action(f"Maybe [{label}], or perhaps [{label}].", legal) is None
    assert parse_action("[not a legal action]", legal) is None


class FakeTrace:
    def __init__(self) -> None:
        self.rewards: dict[str, float] = {}
        self.metrics: dict[str, float] = {}
        self.info: dict[str, object] = {}

    def record_reward(self, name: str, value: float) -> None:
        self.rewards[name] = value

    def record_metric(self, name: str, value: float) -> None:
        self.metrics[name] = value


class FakeInteraction:
    def __init__(self) -> None:
        self.trace = FakeTrace()

    async def turn(self, prompt: str) -> SimpleNamespace:
        del prompt
        return SimpleNamespace(terminated=False, last_reply="No bracketed action.")


class FakeAgent:
    def __init__(self) -> None:
        self.current: FakeInteraction | None = None

    @asynccontextmanager
    async def interaction(self, task: object):
        del task
        self.current = FakeInteraction()
        yield self.current


class FakeAgents:
    def __init__(self) -> None:
        self.east = FakeAgent()
        self.south = FakeAgent()
        self.west = FakeAgent()
        self.north = FakeAgent()


def test_four_interaction_environment_smoke() -> None:
    taskset = HandTaskset(
        HandTasksetConfig(
            rules=Rules(min_faan=0, melds_to_win=1),
            prompt_contract=HandPrompt(tile_rendering="compact"),
        )
    )
    task = next(iter(taskset))
    env = object.__new__(HandEnv)
    env.config = HandEnvConfig(taskset={"id": "hkmj-hand-v1"}, invalid_retries=0)
    agents = FakeAgents()

    assert all(
        isinstance(getattr(env.config, seat), vf.AgentConfig) for seat in DIRECTIONS
    )
    asyncio.run(env.run(task, cast(vf.Agents, agents)))

    traces = [
        cast(FakeInteraction, getattr(agents, seat).current).trace
        for seat in DIRECTIONS
    ]
    assert sum(trace.rewards["payoff"] for trace in traces) == 0
    assert all("raw_points" in trace.metrics for trace in traces)
    assert all(trace.metrics["invalid_actions"] > 0 for trace in traces)
    assert all(trace.metrics["fallbacks"] > 0 for trace in traces)
    serialized = cast(dict, traces[0].info["hkmj"])["hand_trace"]
    assert TypeAdapter(HandTrace).validate_python(serialized).replay()
