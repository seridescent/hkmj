"""Game engine: dealing, valid actions, and the transition function.

Everything after the deal is pure and deterministic: `step(state, actions)
-> state`, with all randomness confined to the wall order fixed by `deal`,
and the rules fixed inside the state itself. `valid_actions` is the single
source of truth for legality; `step`
validates against it and raises ValueError on any violation, so illegal
play is unrepresentable in a trajectory.

Conventions encoded here rather than in the types:

- Hands, melds, and bonus tiles are kept in canonical sorted order.
- A discarded tile lives in the phase while claimable and joins the
  discarder's `discards` only once everyone passes.
- A winning tile is absorbed into the winner's hand at `HandOver`, so a
  finished state carries no tiles in its phase.
- DeclareWin during one's own turn requires a freshly drawn tile: a hand
  completed by claiming a meld cannot win until its next draw.
- Wall exhaustion at any draw — including kong replacement draws — ends
  the hand as a goulash.
"""

from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import replace
from random import Random
from typing import cast

from hkmj_core.actions import (
    Action,
    ClaimChow,
    ClaimKong,
    ClaimPung,
    DeclareConcealedKong,
    DeclareWin,
    Discard,
    Pass,
    PromoteKong,
)
from hkmj_core.hands import has_decomposition
from hkmj_core.melds import Chow, ChowStart, Kong, Meld, Pung, meld_sort_key
from hkmj_core.rules import Rules
from hkmj_core.counting import count_faan
from hkmj_core.state import (
    AwaitingClaims,
    AwaitingDiscard,
    AwaitingKongRob,
    FromDiscard,
    FromRobbedKong,
    FromWall,
    Goulash,
    HandOver,
    Phase,
    PlayerState,
    State,
    Win,
    WinSource,
)
from hkmj_core.tiles import (
    Bonus,
    Direction,
    Flower,
    PlayTile,
    Season,
    Suited,
    Tile,
    full_tile_set,
    next_seat,
    tile_sort_key,
)


def deal(rules: Rules, prevailing: Direction, rng: Random) -> State:
    """Shuffle a full wall and deal a fresh hand, ready for the dealer's
    first discard.

    Determinism/provenance lives with the caller's `rng`; the dealt state
    is self-contained. Dealing order is simplified to sequential blocks —
    with a uniformly shuffled wall this matches the physical protocol in
    distribution.
    """
    tiles = list(full_tile_set())
    rng.shuffle(tiles)
    wall = tuple(tiles)

    hand_size = 3 * rules.melds_to_win + 1
    players: dict[Direction, PlayerState] = {}
    for seat in rules.seats:
        raw, wall = wall[:hand_size], wall[hand_size:]
        hand: list[PlayTile] = []
        bonus: list[Bonus] = []
        for tile in raw:
            if isinstance(tile, Flower | Season):
                bonus.append(tile)
            else:
                hand.append(tile)
        while len(hand) < hand_size:
            tile, wall = wall[-1], wall[:-1]
            if isinstance(tile, Flower | Season):
                bonus.append(tile)
            else:
                hand.append(tile)
        players[seat] = PlayerState(hand=_canonical(hand), bonus=_canonical(bonus))

    dealer = rules.seats[0]
    state = State(
        rules=rules,
        wall=wall,
        prevailing=prevailing,
        players=players,
        phase=HandOver(Goulash()),  # replaced by the dealer's first draw
    )
    return _draw_into_turn(state, dealer, from_back=False)


def valid_actions(state: State) -> Mapping[Direction, frozenset[Action]]:
    """Legal actions for every seat that must act in the current phase.

    Totality contract with `step`: submitted actions must cover exactly the
    seats returned here, each choosing from its set. Sets are never empty
    (claim windows always contain Pass). DeclareWin requires hand shape plus
    the table minimum, judged by scoring the hypothetical win.
    """
    match state.phase:
        case AwaitingDiscard() as phase:
            return {phase.seat: _turn_actions(state, phase)}
        case AwaitingClaims(discarder=discarder, tile=tile):
            chow_seat = next_seat(discarder, state.rules.seats)
            return {
                seat: _claim_actions(
                    state, seat, discarder, tile, chow_allowed=seat == chow_seat
                )
                for seat in state.rules.seats
                if seat != discarder
            }
        case AwaitingKongRob(seat=promoter, tile=tile):
            return {
                seat: _rob_actions(state, seat, promoter, tile)
                for seat in state.rules.seats
                if seat != promoter
            }
        case HandOver():
            return {}


def _turn_actions(state: State, phase: AwaitingDiscard) -> frozenset[Action]:
    player = state.players[phase.seat]
    pool = (
        _canonical((*player.hand, phase.drawn))
        if phase.drawn is not None
        else player.hand
    )
    counts = Counter(pool)
    acts: set[Action] = {Discard(tile) for tile in counts}
    acts |= {DeclareConcealedKong(tile) for tile, n in counts.items() if n == 4}
    acts |= {PromoteKong(tile) for tile in counts if Pung(tile) in player.melds}

    if phase.drawn is not None and _can_declare(
        state, phase.seat, phase.drawn, FromWall(replacement=phase.replacement)
    ):
        acts.add(DeclareWin())
    return frozenset(acts)


def _claim_actions(
    state: State,
    seat: Direction,
    discarder: Direction,
    tile: PlayTile,
    *,
    chow_allowed: bool,
) -> frozenset[Action]:
    counts = Counter(state.players[seat].hand)
    acts: set[Action] = {Pass()}

    if counts[tile] >= 2:
        acts.add(ClaimPung())
    if counts[tile] >= 3:
        acts.add(ClaimKong())

    if chow_allowed and isinstance(tile, Suited):
        for chow in _chows_containing(tile):
            if all(counts[t] >= 1 for t in chow.tiles if t != tile):
                acts.add(ClaimChow(chow.start))

    if _can_declare(state, seat, tile, FromDiscard(discarder)):
        acts.add(DeclareWin())
    return frozenset(acts)


def _chows_containing(tile: Suited) -> Iterator[Chow]:
    for start in (tile.number - 2, tile.number - 1, tile.number):
        if 1 <= start and start + 2 <= 9:
            yield Chow(tile.suit, cast(ChowStart, start))


def _rob_actions(
    state: State, seat: Direction, promoter: Direction, tile: PlayTile
) -> frozenset[Action]:
    acts: set[Action] = {Pass()}
    if _can_declare(state, seat, tile, FromRobbedKong(promoter)):
        acts.add(DeclareWin())
    return frozenset(acts)


def _can_declare(
    state: State, winner: Direction, tile: PlayTile, source: WinSource
) -> bool:
    """Whether `winner` may declare with `tile`: hand shape plus the table
    minimum, judged by scoring the hypothetical win itself."""
    hand = state.players[winner].hand
    if len(hand) % 3 != 1 or not has_decomposition((*hand, tile)):
        return False
    return (
        count_faan(_win_state(state, winner, tile, source)).total
        >= state.rules.min_faan
    )


def step(state: State, actions: Mapping[Direction, Action]) -> State:
    """Advance one transition given every required seat's chosen action."""
    allowed = valid_actions(state)
    if actions.keys() != allowed.keys():
        raise ValueError(
            f"expected actions from seats {sorted(allowed)}, got {sorted(actions)}"
        )
    for seat, action in actions.items():
        if action not in allowed[seat]:
            raise ValueError(f"illegal action for {seat}: {action}")

    match state.phase:
        case AwaitingDiscard() as phase:
            return _turn(state, phase, actions[phase.seat])
        case AwaitingClaims(discarder=discarder, tile=tile):
            return _claims(state, discarder, tile, actions)
        case AwaitingKongRob(seat=promoter, tile=tile):
            return _rob(state, promoter, tile, actions)
        case HandOver():
            raise ValueError("cannot step a finished hand")


def _turn(state: State, phase: AwaitingDiscard, action: Action) -> State:
    seat, drawn = phase.seat, phase.drawn
    player = state.players[seat]
    pool = _canonical((*player.hand, drawn)) if drawn is not None else player.hand
    match action:
        case Discard(tile=tile):
            return _update(
                state,
                seat,
                replace(player, hand=_remove(pool, tile)),
                phase=AwaitingClaims(seat, tile),
            )
        case DeclareConcealedKong(tile=tile):
            return _draw_into_turn(
                _update(
                    state,
                    seat,
                    replace(
                        player,
                        hand=_remove(pool, tile, tile, tile, tile),
                        melds=_add_meld(player.melds, Kong(tile, concealed=True)),
                    ),
                ),
                seat,
                from_back=True,
            )
        case PromoteKong(tile=tile):
            return _update(
                state,
                seat,
                replace(player, hand=_remove(pool, tile)),
                phase=AwaitingKongRob(seat, tile),
            )
        case DeclareWin():
            assert drawn is not None  # guaranteed by _turn_actions
            return _win_state(
                state, seat, drawn, FromWall(replacement=phase.replacement)
            )
        case _:
            raise ValueError(f"not a turn action: {action}")


def _claims(
    state: State,
    discarder: Direction,
    tile: PlayTile,
    actions: Mapping[Direction, Action],
) -> State:
    order = _claimants(state.rules.seats, discarder)
    won = _resolve_winners(state, order, actions, tile, FromDiscard(discarder))
    if won is not None:
        return won

    for seat in order:  # at most one seat can hold enough copies
        player = state.players[seat]
        match actions[seat]:
            case ClaimKong():
                return _draw_into_turn(
                    _update(
                        state,
                        seat,
                        replace(
                            player,
                            hand=_remove(player.hand, tile, tile, tile),
                            melds=_add_meld(player.melds, Kong(tile, concealed=False)),
                        ),
                    ),
                    seat,
                    from_back=True,
                )
            case ClaimPung():
                return _update(
                    state,
                    seat,
                    replace(
                        player,
                        hand=_remove(player.hand, tile, tile),
                        melds=_add_meld(player.melds, Pung(tile)),
                    ),
                    phase=AwaitingDiscard(seat, None),
                )
            case _:
                pass

    for seat in order:
        match actions[seat]:
            case ClaimChow(start=start):
                assert isinstance(tile, Suited)  # guaranteed by _claim_actions
                chow = Chow(tile.suit, start)
                player = state.players[seat]
                return _update(
                    state,
                    seat,
                    replace(
                        player,
                        hand=_remove(
                            player.hand,
                            *(cand for cand in chow.tiles if cand != tile),
                        ),
                        melds=_add_meld(player.melds, chow),
                    ),
                    phase=AwaitingDiscard(seat, None),
                )
            case _:
                pass

    # Everyone passed: the discard becomes history and the next seat draws.
    player = state.players[discarder]
    return _draw_into_turn(
        _update(
            state,
            discarder,
            replace(player, discards=(*player.discards, tile)),
        ),
        next_seat(discarder, state.rules.seats),
        from_back=False,
    )


def _rob(
    state: State,
    promoter: Direction,
    tile: PlayTile,
    actions: Mapping[Direction, Action],
) -> State:
    order = _claimants(state.rules.seats, promoter)
    won = _resolve_winners(state, order, actions, tile, FromRobbedKong(promoter))
    if won is not None:
        return won

    player = state.players[promoter]
    return _draw_into_turn(
        _update(
            state,
            promoter,
            replace(
                player,
                melds=_add_meld(
                    _remove_meld(player.melds, Pung(tile)), Kong(tile, concealed=False)
                ),
            ),
        ),
        promoter,
        from_back=True,
    )


def _resolve_winners(
    state: State,
    order: list[Direction],
    actions: Mapping[Direction, Action],
    tile: PlayTile,
    source: WinSource,
) -> State | None:
    """Settle any DeclareWin claims, or None when there are none.

    Highest faan wins; max() keeps the earliest seat on ties, and `order`
    is closest-first from the tile's source, so ties fall to the closest
    seat in turn order.
    """
    winners = [seat for seat in order if isinstance(actions[seat], DeclareWin)]
    if not winners:
        return None
    best = max(
        winners,
        key=lambda seat: count_faan(_win_state(state, seat, tile, source)).total,
    )
    return _win_state(state, best, tile, source)


def _win_state(
    state: State, winner: Direction, tile: PlayTile, source: WinSource
) -> State:
    """The finished state for `winner` completing their hand with `tile`.

    Single source of truth for win construction: `step` ends real hands with
    it, and hypothetical-win consumers (the min-faan gate, faan comparison)
    score its output, so gating and scoring can never disagree with play.
    """
    player = state.players[winner]
    return _update(
        state,
        winner,
        replace(player, hand=_add_tiles(player.hand, tile)),
        phase=HandOver(Win(winner, tile, source)),
    )


def _draw(
    wall: tuple[Tile, ...], *, from_back: bool
) -> tuple[PlayTile | None, tuple[Bonus, ...], tuple[Tile, ...]]:
    """Draw one playable tile; bonus tiles are set aside, with replacements
    always taken from the back. Returns None when the wall runs out."""
    bonus: list[Bonus] = []
    while wall:
        if from_back:
            tile, wall = wall[-1], wall[:-1]
        else:
            tile, wall = wall[0], wall[1:]
        if isinstance(tile, Flower | Season):
            bonus.append(tile)
            from_back = True
            continue
        return tile, tuple(bonus), wall
    return None, tuple(bonus), wall


def _draw_into_turn(state: State, seat: Direction, *, from_back: bool) -> State:
    tile, bonus, wall = _draw(state.wall, from_back=from_back)
    player = state.players[seat]
    if bonus:
        player = replace(player, bonus=_canonical((*player.bonus, *bonus)))
    # A bonus tile mid-draw means the kept tile came from the back, even
    # when the draw started at the front.
    phase: Phase = (
        AwaitingDiscard(seat, tile, replacement=from_back or bool(bonus))
        if tile is not None
        else HandOver(Goulash())
    )
    return replace(
        state, wall=wall, players={**state.players, seat: player}, phase=phase
    )


def _claimants(seats: tuple[Direction, ...], from_seat: Direction) -> list[Direction]:
    """Seats other than `from_seat`, closest first in turn order."""
    order: list[Direction] = []
    seat = from_seat
    while (seat := next_seat(seat, seats)) != from_seat:
        order.append(seat)
    return order


def _update(
    state: State, seat: Direction, player: PlayerState, *, phase: Phase | None = None
) -> State:
    """Replace one player's state, and the phase unless it is settled later
    in the transition (e.g. by a follow-up draw)."""
    return replace(
        state,
        players={**state.players, seat: player},
        phase=state.phase if phase is None else phase,
    )


def _canonical[T: Tile](tiles: Iterable[T]) -> tuple[T, ...]:
    return tuple(sorted(tiles, key=tile_sort_key))


def _add_tiles(hand: tuple[PlayTile, ...], *tiles: PlayTile) -> tuple[PlayTile, ...]:
    return _canonical((*hand, *tiles))


def _remove(pool: tuple[PlayTile, ...], *tiles: PlayTile) -> tuple[PlayTile, ...]:
    out = list(pool)
    for tile in tiles:
        out.remove(tile)  # membership guaranteed by valid_actions
    return tuple(out)


def _add_meld(melds: tuple[Meld, ...], meld: Meld) -> tuple[Meld, ...]:
    return tuple(sorted((*melds, meld), key=meld_sort_key))


def _remove_meld(melds: tuple[Meld, ...], meld: Meld) -> tuple[Meld, ...]:
    out = list(melds)
    out.remove(meld)
    return tuple(out)
