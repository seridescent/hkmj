from hkmj_core import ClaimPung, Pass
from hkmj_hand_v1 import HandTaskset
from hkmj_hand_v1.presentation import parse_action
from hkmj_hand_v1.taskset import HandTasksetConfig


def test_seeded_task_materialization_is_deterministic() -> None:
    tasks = list(HandTaskset(HandTasksetConfig(start_seed=11)).head(2))
    repeated = list(HandTaskset(HandTasksetConfig(start_seed=11)).head(2))

    assert [task.data.seed for task in tasks] == [11, 12]
    assert [task.data for task in tasks] == [task.data for task in repeated]


def test_bracket_parser_allows_reasoning_but_rejects_ambiguity() -> None:
    actions_by_label = {"pass": Pass(), "pung": ClaimPung()}

    assert parse_action("Because of the shape, I choose [pung].", actions_by_label) == (
        ClaimPung()
    )
    assert parse_action("Maybe [pass], or perhaps [pung].", actions_by_label) is None
    assert parse_action("[not a legal action]", actions_by_label) is None


def test_forced_actions_skip_prompts_but_preserve_updates_and_replay(monkeypatch):
    import asyncio
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from hkmj_core import DIRECTIONS, HandTrace, player_view, valid_actions
    from hkmj_hand_v1 import taskset as module
    from hkmj_hand_v1.presentation import action_label, actions_by_label
    from hkmj_hand_v1.taskset import HandEnv, HandEnvConfig

    task = next(iter(HandTaskset(HandTasksetConfig(start_seed=11)).head(1)))
    contract = task.data.prompt_contract
    state = task.data.initial_state
    public_updates = []
    forced = []
    calls = []
    delivered = {seat: 0 for seat in DIRECTIONS}
    original_step = module.step

    def record_step(before, actions):
        nonlocal state
        legal = valid_actions(before)
        for seat, choices in legal.items():
            if len(choices) == 1:
                assert actions[seat] == next(iter(choices))
                forced.append((seat, actions[seat]))
        state, resolved = original_step(before, actions)
        if resolved is None:
            public_updates.append(contract.all_passed_update_template)
        else:
            seat, action = resolved
            public_updates.append(
                contract.update_template.format(
                    seat=seat,
                    action=action_label(action, player_view(before, seat), contract),
                )
            )
        return state, resolved

    monkeypatch.setattr(module, "step", record_step)

    class Player:
        def __init__(self, seat):
            self.seat = seat
            self.trace = SimpleNamespace(
                info={},
                record_reward=lambda *args: None,
                record_metric=lambda *args: None,
            )

        @asynccontextmanager
        async def interaction(self, task):
            yield self

        async def turn(self, prompt):
            legal = valid_actions(state)[self.seat]
            assert len(legal) > 1, "A forced move must not prompt the player"
            unseen = public_updates[delivered[self.seat] :]
            if unseen:
                assert "\n".join(unseen) in prompt
            delivered[self.seat] = len(public_updates)
            calls.append(self.seat)
            labels = actions_by_label(legal, player_view(state, self.seat), contract)
            label = "pass" if "pass" in labels else next(iter(labels))
            return SimpleNamespace(terminated=False, last_reply=f"[{label}]")

    players = {seat: Player(seat) for seat in DIRECTIONS}
    env = HandEnv(HandEnvConfig(taskset={"id": "hkmj-hand-v1"}))
    asyncio.run(env.run(task, SimpleNamespace(**players)))
    assert calls
    assert any(isinstance(action, Pass) for _, action in forced)
    assert contract.all_passed_update_template in public_updates
    for player in players.values():
        replay = module.HAND_TRACE_ADAPTER.validate_python(
            player.trace.info["hkmj"]["hand_trace"]
        )
        assert isinstance(replay, HandTrace)
        assert replay.play_to_end() == state
    assert sum(len(batch) for batch in replay.action_batches) == len(calls) + len(
        forced
    )
