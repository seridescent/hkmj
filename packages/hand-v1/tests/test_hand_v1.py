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
