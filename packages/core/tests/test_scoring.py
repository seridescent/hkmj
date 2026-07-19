from dataclasses import replace

import pytest

from hkmj_core import (
    DIRECTIONS,
    AllFlowers,
    AllInTriplets,
    AwaitingClaims,
    Bonus,
    Chow,
    CommonHand,
    ConcealedHand,
    DeclareWin,
    Direction,
    Dragon,
    DragonMeld,
    FaanEntry,
    Flower,
    FlowerOfOwnWind,
    FromDiscard,
    FromRobbedKong,
    FromWall,
    Goulash,
    GreatDragons,
    HandOver,
    HeavenlyHand,
    Meld,
    MixedOneSuit,
    NoBonusTiles,
    Number,
    PlayerState,
    PlayTile,
    PrevailingWind,
    RobbingTheKong,
    Rules,
    Season,
    SeasonOfOwnWind,
    SeatWind,
    SelfPick,
    SmallDragons,
    SmallWinds,
    State,
    Suit,
    Suited,
    Win,
    WinByKong,
    WinByLastCatch,
    WinSource,
    Wind,
    meld_sort_key,
    score,
    tile_sort_key,
    valid_actions,
)


def suited(suit: Suit, *numbers: Number) -> tuple[Suited, ...]:
    return tuple(Suited(suit, n) for n in numbers)


def win_state(
    *,
    hand: tuple[PlayTile, ...],
    melds: tuple[Meld, ...] = (),
    bonus: tuple[Bonus, ...] = (Flower(3),),  # a flower matching nobody
    winner: Direction = "south",
    prevailing: Direction = "east",
    source: WinSource | None = None,
    wall: tuple[PlayTile, ...] = (Wind("north"),),
    rules: Rules | None = None,
    first_turn: bool = False,
) -> State:
    players = {d: PlayerState(hand=()) for d in DIRECTIONS}
    players[winner] = PlayerState(
        hand=tuple(sorted(hand, key=tile_sort_key)),
        melds=tuple(sorted(melds, key=meld_sort_key)),
        bonus=tuple(sorted(bonus, key=tile_sort_key)),
    )
    if not first_turn:  # a discard on record suppresses heavenly/earthly
        bystander = next(d for d in DIRECTIONS if d != winner)
        players[bystander] = replace(players[bystander], discards=(Suited("dot", 1),))
    win = Win(winner, hand[0], source if source is not None else FromDiscard("east"))
    return State(
        rules=rules if rules is not None else Rules(),
        wall=wall,
        prevailing=prevailing,
        players=players,
        phase=HandOver(win),
    )


def entry_set(state: State) -> set[FaanEntry]:
    return set(score(state).entries)


COMMON_HAND = (
    *suited("dot", 1, 2, 3),
    *suited("bamboo", 4, 5, 6),
    *suited("myriad", 7, 7),
)


def test_common_hand() -> None:
    state = win_state(hand=COMMON_HAND)
    assert entry_set(state) == {CommonHand(), ConcealedHand()}
    assert score(state).total == 2


def test_all_in_triplets() -> None:
    hand = (
        *suited("dot", 1, 1, 1, 9, 9, 9),
        *suited("bamboo", 5, 5, 5),
        *suited("myriad", 7, 7, 7),
        *suited("dot", 2, 2),
    )
    assert entry_set(win_state(hand=hand)) == {AllInTriplets(), ConcealedHand()}


def test_flush_scores_best_reading() -> None:
    state = win_state(hand=(*suited("dot", 1, 1, 1, 2, 2, 2, 3, 3, 3, 9, 9),))
    s = score(state)
    # Pung reading: triplets 3 + one suit 7 + concealed 1 beats the chow
    # reading: common 1 + one suit 7 + concealed 1.
    assert AllInTriplets() in s.entries
    assert s.total == 11


def test_mixed_one_suit_with_prevailing_wind() -> None:
    hand = (
        *suited("dot", 1, 2, 3, 4, 5, 6, 9, 9),
        Wind("east"),
        Wind("east"),
        Wind("east"),
    )
    assert entry_set(win_state(hand=hand)) == {
        MixedOneSuit(),
        PrevailingWind(),
        ConcealedHand(),
    }


def test_great_dragons() -> None:
    hand = (
        Dragon("red"),
        Dragon("red"),
        Dragon("red"),
        Dragon("green"),
        Dragon("green"),
        Dragon("green"),
        Dragon("white"),
        Dragon("white"),
        Dragon("white"),
        *suited("bamboo", 5, 6, 7),
        *suited("dot", 1, 1),
    )
    assert entry_set(win_state(hand=hand)) == {
        GreatDragons(),
        DragonMeld("red"),
        DragonMeld("green"),
        DragonMeld("white"),
        ConcealedHand(),
    }


def test_small_dragons() -> None:
    hand = (
        Dragon("red"),
        Dragon("red"),
        Dragon("red"),
        Dragon("green"),
        Dragon("green"),
        Dragon("green"),
        *suited("bamboo", 5, 6, 7),
        *suited("myriad", 2, 3, 4),
        Dragon("white"),
        Dragon("white"),
    )
    assert entry_set(win_state(hand=hand)) == {
        SmallDragons(),
        DragonMeld("red"),
        DragonMeld("green"),
        ConcealedHand(),
    }


def test_small_winds_stacks_per_reference() -> None:
    hand = (
        Wind("east"),
        Wind("east"),
        Wind("east"),
        Wind("south"),
        Wind("south"),
        Wind("south"),
        Wind("west"),
        Wind("west"),
        Wind("west"),
        *suited("dot", 2, 3, 4),
        Wind("north"),
        Wind("north"),
    )
    # The reference notes small winds implies mixed one suit and stacks with
    # seat/prevailing wind faan.
    assert entry_set(win_state(hand=hand)) == {
        SmallWinds(),
        MixedOneSuit(),
        SeatWind(),
        PrevailingWind(),
        ConcealedHand(),
    }


def test_double_wind_counts_twice() -> None:
    hand = (
        Wind("east"),
        Wind("east"),
        Wind("east"),
        *suited("dot", 1, 2, 3),
        *suited("bamboo", 4, 5, 6),
        *suited("myriad", 7, 8, 9),
        *suited("dot", 5, 5),
    )
    state = win_state(hand=hand, winner="east", source=FromDiscard("west"))
    assert entry_set(state) == {
        SeatWind(),
        PrevailingWind(),
        ConcealedHand(),
    }


def test_flower_of_own_wind() -> None:
    state = win_state(hand=COMMON_HAND, bonus=(Flower(2), Season(3)))
    assert entry_set(state) == {
        CommonHand(),
        ConcealedHand(),
        FlowerOfOwnWind(),
    }


def test_all_flowers_replaces_own_flower() -> None:
    state = win_state(
        hand=COMMON_HAND,
        bonus=(Flower(1), Flower(2), Flower(3), Flower(4), Season(2)),
    )
    assert entry_set(state) == {
        CommonHand(),
        ConcealedHand(),
        AllFlowers(),
        SeasonOfOwnWind(),
    }


def test_no_bonus_tiles() -> None:
    assert NoBonusTiles() in entry_set(win_state(hand=COMMON_HAND, bonus=()))


def test_self_pick_and_kong_replacement() -> None:
    assert SelfPick() in entry_set(win_state(hand=COMMON_HAND, source=FromWall()))
    replacement = entry_set(
        win_state(hand=COMMON_HAND, source=FromWall(replacement=True))
    )
    assert {SelfPick(), WinByKong()} <= replacement


def test_robbing_the_kong() -> None:
    state = win_state(hand=COMMON_HAND, source=FromRobbedKong("east"))
    assert RobbingTheKong() in entry_set(state)


def test_win_by_last_catch() -> None:
    assert WinByLastCatch() in entry_set(win_state(hand=COMMON_HAND, wall=()))


def test_heavenly_hand_is_capped() -> None:
    state = win_state(
        hand=COMMON_HAND, winner="east", source=FromWall(), first_turn=True
    )
    assert HeavenlyHand() in entry_set(state)
    assert score(state).total == 13


def test_faan_cap_applies() -> None:
    state = win_state(
        hand=(*suited("dot", 1, 1, 1, 2, 2, 2, 3, 3, 3, 9, 9),),
        rules=Rules(faan_cap=8),
    )
    assert score(state).total == 8


def test_chicken_hand_scores_zero() -> None:
    # A pung among chows, three suits, no honors, open meld, won by discard:
    # nothing fires.
    state = win_state(
        hand=(
            *suited("bamboo", 4, 4, 4),
            *suited("dot", 7, 8, 9),
            *suited("myriad", 8, 8),
        ),
        melds=(Chow("myriad", 1),),
    )
    assert score(state).entries == ()
    assert score(state).total == 0


def test_score_requires_a_win() -> None:
    state = win_state(hand=COMMON_HAND)
    with pytest.raises(ValueError):
        score(replace(state, phase=HandOver(Goulash())))


def test_min_faan_gates_declare_win() -> None:
    players = {d: PlayerState(hand=()) for d in DIRECTIONS}
    players["east"] = PlayerState(hand=(), discards=(Suited("dot", 1),))
    players["south"] = PlayerState(
        hand=tuple(
            sorted(
                (
                    *suited("bamboo", 4, 4, 4),
                    *suited("dot", 7, 8, 9),
                    Suited("myriad", 8),
                ),
                key=tile_sort_key,
            )
        ),
        melds=(Chow("myriad", 1),),
        bonus=(Flower(3),),
    )
    state = State(
        rules=Rules(),
        wall=(Wind("north"),),
        prevailing="east",
        players=players,
        phase=AwaitingClaims("east", Suited("myriad", 8)),
    )
    assert DeclareWin() not in valid_actions(state)["south"]

    lenient = replace(state, rules=Rules(min_faan=0))
    assert DeclareWin() in valid_actions(lenient)["south"]
