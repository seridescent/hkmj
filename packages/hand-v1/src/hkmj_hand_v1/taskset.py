"""A seeded four-seat Verifiers environment for complete mahjong hands."""

import asyncio
from collections.abc import Iterator
from itertools import count
from random import Random
from typing import Self, cast

from pydantic import Field, TypeAdapter, model_validator

import verifiers.v1 as vf
from hkmj_core import (
    Action,
    DIRECTIONS,
    Direction,
    FaanCount,
    Goulash,
    HandOver,
    HandTrace,
    Outcome,
    Rules,
    Scoring,
    State,
    Win,
    count_faan,
    deal,
    full_spicy,
    player_view,
    settle,
    step,
    valid_actions,
)

from hkmj_hand_v1.presentation import (
    HandPrompt,
    action_label,
    actions_by_label,
    parse_action,
    render_invalid_prompt,
    render_system_prompt,
    render_turn_prompt,
)

HAND_TRACE_ADAPTER = TypeAdapter(HandTrace)
STATE_ADAPTER = TypeAdapter(State)
OUTCOME_ADAPTER = TypeAdapter(Outcome)
FAAN_COUNT_ADAPTER = TypeAdapter(FaanCount)


class HandData(vf.TaskData):
    """One reproducible deal and the complete contract used to present it."""

    seed: int
    initial_state: State
    scoring: Scoring
    prompt_contract: HandPrompt


class HandTask(vf.Task[HandData]):
    pass


class HandTasksetConfig(vf.TasksetConfig):
    start_seed: int = 0
    prevailing: Direction = "east"
    rules: Rules = Rules()
    scoring: Scoring = Scoring(
        points=full_spicy,
        payments="discarder_pays_half",
    )
    prompt_contract: HandPrompt = HandPrompt()

    @model_validator(mode="after")
    def require_four_standard_seats(self) -> Self:
        if self.rules.seats != DIRECTIONS:
            raise ValueError("hkmj-hand-v1 requires east, south, west, and north")
        return self


class HandEnvConfig(vf.EnvConfig):
    east: vf.AgentConfig = vf.AgentConfig(harness={"id": "null"})
    south: vf.AgentConfig = vf.AgentConfig(harness={"id": "null"})
    west: vf.AgentConfig = vf.AgentConfig(harness={"id": "null"})
    north: vf.AgentConfig = vf.AgentConfig(harness={"id": "null"})
    max_concurrent_agents: int | None = Field(4, ge=1)
    invalid_retries: int = Field(1, ge=0)


class HandEnv(vf.Env[HandEnvConfig]):
    """Open one real interaction per seat and referee a complete native hand."""

    async def run(self, task: vf.Task, agents: vf.Agents) -> None:
        if not isinstance(task, HandTask):
            raise TypeError(f"HandEnv requires HandTask, got {type(task).__name__}")
        hand_task = cast(HandTask, task)
        data = hand_task.data
        seat_tasks = {
            seat: HandTask(
                data.model_copy(
                    update={
                        "prompt": None,
                        "system_prompt": render_system_prompt(
                            player_view(data.initial_state, seat),
                            data.scoring,
                            data.prompt_contract,
                            data.system_prompt,
                        ),
                    }
                ),
                hand_task.config,
            )
            for seat in DIRECTIONS
        }

        state = data.initial_state
        action_batches: list[dict[Direction, Action]] = []
        # Append-only public log with one resolved result for each completed step.
        updates: list[str] = []
        # Per-seat cursor into `updates`, so each prompt gets only unseen results.
        seen = {seat: 0 for seat in DIRECTIONS}
        invalid_actions = {seat: 0 for seat in DIRECTIONS}

        async with (
            agents.east.interaction(seat_tasks["east"]) as east,
            agents.south.interaction(seat_tasks["south"]) as south,
            agents.west.interaction(seat_tasks["west"]) as west,
            agents.north.interaction(seat_tasks["north"]) as north,
        ):
            interactions = {
                "east": east,
                "south": south,
                "west": west,
                "north": north,
            }

            async def choose_action(
                seat: Direction, legal_actions: frozenset[Action]
            ) -> Action:
                if len(legal_actions) == 1:
                    return next(iter(legal_actions))

                view = player_view(state, seat)
                labeled_actions = actions_by_label(
                    legal_actions, view, data.prompt_contract
                )
                prompt = render_turn_prompt(
                    view,
                    labeled_actions,
                    updates[seen[seat] :],
                    data.prompt_contract,
                )
                seen[seat] = len(updates)
                for _ in range(self.config.invalid_retries + 1):
                    segment = await interactions[seat].turn(prompt)
                    if segment.terminated:
                        trace = interactions[seat].trace
                        reason = trace.stop_condition or "no stop condition recorded"
                        if trace.last_error is not None:
                            reason += f": {trace.last_error.message}"
                        raise RuntimeError(
                            f"{seat} interaction terminated before choosing an action "
                            f"({reason})"
                        )

                    action = parse_action(segment.last_reply, labeled_actions)
                    if action is not None:
                        return action

                    invalid_actions[seat] += 1
                    prompt = render_invalid_prompt(
                        labeled_actions, data.prompt_contract
                    )

                raise ValueError(
                    f"{seat} failed to choose a legal bracketed action; "
                    f"invalid reply limit: {self.config.invalid_retries + 1}"
                )

            while not isinstance(state.phase, HandOver):
                legal_actions_by_seat = valid_actions(state)
                seats = tuple(legal_actions_by_seat)
                try:
                    async with asyncio.TaskGroup() as group:
                        action_tasks = {
                            seat: group.create_task(
                                choose_action(seat, legal_actions_by_seat[seat])
                            )
                            for seat in seats
                        }
                except* (RuntimeError, ValueError) as errors:
                    raise errors.exceptions[0] from None
                actions = {seat: action_tasks[seat].result() for seat in seats}
                next_state, resolved = step(state, actions)
                action_batches.append(actions)
                if resolved is None:
                    updates.append(data.prompt_contract.all_passed_update_template)
                else:
                    seat, action = resolved
                    updates.append(
                        data.prompt_contract.update_template.format(
                            seat=seat,
                            action=action_label(
                                action,
                                player_view(state, seat),
                                data.prompt_contract,
                            ),
                        )
                    )
                state = next_state

        hand_trace = HandTrace(data.initial_state, tuple(action_batches))
        if hand_trace.play_to_end() != state:
            raise RuntimeError("recorded hand trace does not reproduce the final state")

        phase = state.phase
        assert isinstance(phase, HandOver)
        outcome = phase.outcome
        faan_count = count_faan(state) if isinstance(outcome, Win) else None
        deltas = settle(data.scoring, state)
        common_info = {
            "seed": data.seed,
            "hand_trace": HAND_TRACE_ADAPTER.dump_python(hand_trace, mode="json"),
            "final_state": STATE_ADAPTER.dump_python(state, mode="json"),
            "outcome": OUTCOME_ADAPTER.dump_python(outcome, mode="json"),
            "faan_count": (
                FAAN_COUNT_ADAPTER.dump_python(faan_count, mode="json")
                if faan_count is not None
                else None
            ),
            "points": dict(deltas),
            "steps": len(action_batches),
            "invalid_actions": invalid_actions,
        }
        for seat, trace in zip(
            DIRECTIONS,
            (east.trace, south.trace, west.trace, north.trace),
            strict=True,
        ):
            trace.record_reward("payoff", float(deltas[seat]))
            trace.record_metric("raw_points", float(deltas[seat]))
            trace.record_metric(
                "win", float(isinstance(outcome, Win) and outcome.winner == seat)
            )
            trace.record_metric("goulash", float(isinstance(outcome, Goulash)))
            trace.record_metric(
                "winner_faan", float(faan_count.total if faan_count is not None else 0)
            )
            trace.record_metric("invalid_actions", float(invalid_actions[seat]))
            trace.info["hkmj"] = {"seat": seat, **common_info}


class HandTaskset(vf.Taskset[HandTask, HandTasksetConfig]):
    INFINITE = True

    def load(self) -> Iterator[HandTask]:
        for idx, seed in enumerate(count(self.config.start_seed)):
            yield HandTask(
                HandData(
                    idx=idx,
                    name=f"hand#{seed}",
                    prompt=None,
                    seed=seed,
                    initial_state=deal(
                        self.config.rules,
                        self.config.prevailing,
                        Random(seed),
                    ),
                    scoring=self.config.scoring,
                    prompt_contract=self.config.prompt_contract,
                ),
                self.config.task,
            )
