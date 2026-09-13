from dataclasses import replace

import pytest
from hkmj_core import (
    DIRECTIONS,
    ORPHAN_KINDS,
    AllFlowers,
    AllInTriplets,
    AllKongs,
    AwaitingClaims,
    Bonus,
    Chow,
    CommonHand,
    ConcealedHand,
    DeclareWin,
    Direction,
    Dragon,
    DragonMeld,
    Flower,
    FlowerOfOwnWind,
    FromDiscard,
    FromRobbedKong,
    FromWall,
    Goulash,
    GreatDragons,
    GreatWinds,
    HandOver,
    HeavenlyHand,
    Kong,
    LimitCount,
    Meld,
    MixedOneSuit,
    NineGates,
    NoBonusTiles,
    Number,
    OrdinaryCount,
    Orphans,
    Pattern,
    PlayerState,
    PlayTile,
    PrevailingWind,
    RobbingTheKong,
    Rules,
    Season,
    SeasonOfOwnWind,
    SeatWind,
    SelfPick,
    SelfTriplets,
    SmallDragons,
    SmallWinds,
    State,
    Suit,
    Suited,
    ThirteenOrphans,
    Win,
    WinByKong,
    WinByLastCatch,
    Wind,
    WinSource,
    count_faan,
    meld_sort_key,
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
    winning_tile: PlayTile | None = None,
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
    win = Win(
        winner,
        winning_tile if winning_tile is not None else hand[0],
        source if source is not None else FromDiscard("east"),
    )
    return State(
        rules=rules if rules is not None else Rules(),
        wall=wall,
        prevailing=prevailing,
        players=players,
        phase=HandOver(win),
    )


def pattern_set(state: State) -> set[Pattern]:
    count = count_faan(state)
    assert isinstance(count, OrdinaryCount)
    return set(count.patterns)


COMMON_HAND = (
    *suited("dot", 1, 2, 3),
    *suited("bamboo", 4, 5, 6),
    *suited("myriad", 7, 7),
)


def test_common_hand() -> None:
    state = win_state(hand=COMMON_HAND)
    assert pattern_set(state) == {CommonHand(), ConcealedHand()}
    assert count_faan(state).total == 2


def test_all_in_triplets() -> None:
    hand = (
        *suited("dot", 1, 1, 1, 9, 9, 9),
        *suited("bamboo", 5, 5, 5),
        *suited("myriad", 7, 7, 7),
        *suited("dot", 2, 2),
    )
    assert pattern_set(win_state(hand=hand)) == {AllInTriplets(), ConcealedHand()}


def test_flush_counts_best_reading() -> None:
    state = win_state(hand=(*suited("dot", 1, 1, 1, 2, 2, 2, 3, 3, 3, 9, 9),))
    count = count_faan(state)
    assert isinstance(count, OrdinaryCount)
    # Pung reading: triplets 3 + one suit 7 + concealed 1 beats the chow
    # reading: common 1 + one suit 7 + concealed 1.
    assert AllInTriplets() in count.patterns
    assert count.total == 11


def test_mixed_one_suit_with_prevailing_wind() -> None:
    hand = (
        *suited("dot", 1, 2, 3, 4, 5, 6, 9, 9),
        Wind("east"),
        Wind("east"),
        Wind("east"),
    )
    assert pattern_set(win_state(hand=hand)) == {
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
    assert pattern_set(win_state(hand=hand)) == {
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
    assert pattern_set(win_state(hand=hand)) == {
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
    assert pattern_set(win_state(hand=hand)) == {
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
    assert pattern_set(state) == {
        SeatWind(),
        PrevailingWind(),
        ConcealedHand(),
    }


def test_flower_of_own_wind() -> None:
    state = win_state(hand=COMMON_HAND, bonus=(Flower(2), Season(3)))
    assert pattern_set(state) == {
        CommonHand(),
        ConcealedHand(),
        FlowerOfOwnWind(),
    }


def test_all_flowers_replaces_own_flower() -> None:
    state = win_state(
        hand=COMMON_HAND,
        bonus=(Flower(1), Flower(2), Flower(3), Flower(4), Season(2)),
    )
    assert pattern_set(state) == {
        CommonHand(),
        ConcealedHand(),
        AllFlowers(),
        SeasonOfOwnWind(),
    }


def test_no_bonus_tiles() -> None:
    assert NoBonusTiles() in pattern_set(win_state(hand=COMMON_HAND, bonus=()))


def test_self_pick_and_kong_replacement() -> None:
    assert SelfPick() in pattern_set(win_state(hand=COMMON_HAND, source=FromWall()))
    replacement = pattern_set(
        win_state(hand=COMMON_HAND, source=FromWall(replacement=True))
    )
    assert {SelfPick(), WinByKong()} <= replacement


def test_robbing_the_kong() -> None:
    state = win_state(hand=COMMON_HAND, source=FromRobbedKong("east"))
    assert RobbingTheKong() in pattern_set(state)


def test_win_by_last_catch() -> None:
    assert WinByLastCatch() in pattern_set(win_state(hand=COMMON_HAND, wall=()))


def test_heavenly_hand_is_capped() -> None:
    state = win_state(
        hand=COMMON_HAND, winner="east", source=FromWall(), first_turn=True
    )
    assert HeavenlyHand() in pattern_set(state)
    assert count_faan(state).total == 13


def test_rules_can_change_the_faan_cap() -> None:
    capped = Rules(faan_cap=8)
    state = win_state(
        hand=(*suited("dot", 1, 1, 1, 2, 2, 2, 3, 3, 3, 9, 9),),
        rules=capped,
    )
    assert count_faan(state).total == 8


def test_chicken_hand_counts_zero() -> None:
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
    count = count_faan(state)
    assert isinstance(count, OrdinaryCount)
    assert count.patterns == ()
    assert count.total == 0


def test_count_faan_requires_a_win() -> None:
    state = win_state(hand=COMMON_HAND)
    with pytest.raises(ValueError):
        count_faan(replace(state, phase=HandOver(Goulash())))


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


def winds(*directions: Direction) -> tuple[Wind, ...]:
    return tuple(Wind(d) for d in directions)


def test_ordinary_reading_can_beat_a_limit_reading() -> None:
    # "Ineligible for additional faan" restricts what a limit reading may
    # count, not which reading is taken: here ordinary counting (triplets,
    # mixed orphans, small dragons, both wind faan, two dragon melds,
    # self-pick, concealed) reaches 13 and beats all-honor-tiles' 10 + 2.
    hand = (
        *winds("south", "south", "south", "east", "east", "east"),
        Dragon("red"),
        Dragon("red"),
        Dragon("red"),
        Dragon("green"),
        Dragon("green"),
        Dragon("green"),
        Dragon("white"),
        Dragon("white"),
    )
    count = count_faan(win_state(hand=hand, source=FromWall()))
    assert isinstance(count, OrdinaryCount)
    assert count.total == 13


def test_limit_hands_require_four_melds() -> None:
    # A two-meld all-honor hand is not the all-honor-tiles limit hand:
    # reduced games never reward limit-chasing.
    hand = (
        *winds("south", "south", "south", "east", "east", "east"),
        Dragon("red"),
        Dragon("red"),
    )
    assert isinstance(count_faan(win_state(hand=hand)), OrdinaryCount)


def test_great_winds_beats_all_honor_tiles() -> None:
    # Non-stacking among limit criteria: only the highest applies.
    hand = (
        *winds("east", "east", "east", "south", "south", "south"),
        *winds("west", "west", "west", "north", "north", "north"),
        Dragon("red"),
        Dragon("red"),
    )
    count = count_faan(win_state(hand=hand))
    assert isinstance(count, LimitCount)
    assert count.hand == GreatWinds()
    assert count.total == 13


def test_orphans() -> None:
    hand = (
        *suited("dot", 1, 1, 1, 9, 9, 9),
        *suited("bamboo", 1, 1, 1, 9, 9, 9),
        *suited("myriad", 1, 1),
    )
    count = count_faan(win_state(hand=hand))
    assert count == LimitCount(Orphans(), (ConcealedHand(),), 11)


def test_self_triplets_requires_self_pick_or_pair_completion() -> None:
    hand = (
        *suited("dot", 1, 1, 1, 7, 7, 7),
        *suited("bamboo", 3, 3, 3),
        *suited("myriad", 5, 5, 5),
        *suited("dot", 9, 9),
    )
    self_pick = count_faan(win_state(hand=hand, source=FromWall()))
    assert self_pick == LimitCount(SelfTriplets(), (SelfPick(),), 11)

    pair_completion = count_faan(win_state(hand=hand, winning_tile=Suited("dot", 9)))
    assert pair_completion == LimitCount(SelfTriplets(), (), 10)

    meld_completion = count_faan(win_state(hand=hand, winning_tile=Suited("dot", 1)))
    assert isinstance(meld_completion, OrdinaryCount)


def test_nine_gates() -> None:
    hand = (*suited("bamboo", 1, 1, 1, 2, 3, 4, 5, 5, 6, 7, 8, 9, 9, 9),)
    count = count_faan(win_state(hand=hand, source=FromWall()))
    # Definitionally concealed: no separate concealed-hand faan.
    assert count == LimitCount(NineGates(), (SelfPick(),), 11)


def test_all_kongs() -> None:
    melds = (
        Kong(Suited("dot", 8), concealed=False),
        Kong(Suited("bamboo", 5), concealed=False),
        Kong(Wind("north"), concealed=False),
        Kong(Suited("dot", 4), concealed=False),
    )
    count = count_faan(win_state(hand=(*suited("myriad", 9, 9),), melds=melds))
    assert isinstance(count, LimitCount)
    assert count.hand == AllKongs()
    assert count.total == 13


def test_thirteen_orphans_counts_and_is_declarable() -> None:
    orphans = tuple(sorted(ORPHAN_KINDS, key=tile_sort_key))
    count = count_faan(win_state(hand=(*orphans, Wind("east"))))
    assert count == LimitCount(ThirteenOrphans(), (), 13)

    # The shape is not melds-plus-eyes, so the win gate must admit it.
    players = {d: PlayerState(hand=()) for d in DIRECTIONS}
    players["east"] = PlayerState(hand=(), discards=(Suited("dot", 1),))
    players["south"] = PlayerState(hand=orphans, bonus=(Flower(3),))
    state = State(
        rules=Rules(),
        wall=(Wind("north"),),
        prevailing="east",
        players=players,
        phase=AwaitingClaims("east", Wind("west")),
    )
    assert DeclareWin() in valid_actions(state)["south"]
