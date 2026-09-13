import json
from dataclasses import asdict, fields

import pytest
from hkmj_core import (
    Action,
    AllKongs,
    AwaitingDiscardView,
    ClaimKong,
    ClaimPung,
    CommonHand,
    DeclareWin,
    Discard,
    Dragon,
    DragonMeld,
    FaanCount,
    Flower,
    FromRobbedKong,
    HandOver,
    HiddenDraw,
    Kong,
    LimitCount,
    OrdinaryCount,
    Pass,
    PlayerState,
    PlayerView,
    Rules,
    Season,
    SeatWind,
    SelfPick,
    State,
    Suited,
    Win,
)
from pydantic import BaseModel, TypeAdapter


@pytest.mark.parametrize(
    "action",
    [
        Discard(Dragon("green")),
        ClaimPung(),
        ClaimKong(),
        DeclareWin(),
        Pass(),
    ],
)
def test_action_json_round_trip_distinguishes_payload_free_variants(
    action: Action,
) -> None:
    adapter = TypeAdapter(Action)

    encoded = adapter.dump_json(action)

    assert json.loads(encoded, object_pairs_hook=dict)["kind"] == action.kind
    assert adapter.validate_json(encoded) == action


def test_state_json_round_trip_preserves_nested_unions() -> None:
    state = State(
        rules=Rules(min_faan=0),
        wall=(Flower(1), Season(1)),
        prevailing="east",
        players={
            "east": PlayerState(
                hand=(Suited("dot", 3),),
                melds=(Kong(Dragon("red"), concealed=True),),
                bonus=(Season(4),),
            )
        },
        phase=HandOver(
            Win(
                winner="east",
                winning_tile=Suited("dot", 3),
                source=FromRobbedKong("south"),
            )
        ),
    )
    adapter = TypeAdapter(State)

    encoded = adapter.dump_json(state)
    decoded = json.loads(encoded)

    assert decoded["wall"] == [
        {"kind": "flower", "number": 1},
        {"kind": "season", "number": 1},
    ]
    assert decoded["phase"]["kind"] == "hand_over"
    assert decoded["phase"]["outcome"]["kind"] == "win"
    assert decoded["phase"]["outcome"]["source"]["kind"] == "from_robbed_kong"
    assert adapter.validate_json(encoded) == state


@pytest.mark.parametrize(
    "count",
    [
        OrdinaryCount(
            patterns=(CommonHand(), SeatWind(), DragonMeld("red"), SelfPick()),
            total=4,
        ),
        LimitCount(hand=AllKongs(), conditions=(SelfPick(),), total=13),
    ],
)
def test_faan_count_json_round_trip_preserves_nested_pattern_unions(
    count: FaanCount,
) -> None:
    adapter = TypeAdapter(FaanCount)
    encoded = adapter.dump_json(count)

    assert adapter.validate_json(encoded) == count


def test_player_view_composes_inside_a_pydantic_model() -> None:
    view = PlayerView(
        seat="east",
        rules=Rules(),
        prevailing="south",
        wall_count=42,
        me=PlayerState(hand=(Suited("bamboo", 7),)),
        opponents={},
        phase=AwaitingDiscardView("south", HiddenDraw()),
    )

    class ConsumerModel(BaseModel):
        view: PlayerView
        action: Action

    model = ConsumerModel(view=view, action=ClaimKong())

    assert ConsumerModel.model_validate_json(model.model_dump_json()) == model


def test_kind_is_the_first_dataclass_and_json_field() -> None:
    tile = Season(2)

    assert fields(tile)[0].name == "kind"
    assert json.dumps(asdict(tile)).startswith('{"kind": "season"')
