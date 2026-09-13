"""Seat-local hand rendering and bracketed action parsing."""

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Literal

from hkmj_core import (
    Action,
    AwaitingClaims,
    AwaitingDiscardView,
    AwaitingKongRob,
    Chow,
    ClaimChow,
    ClaimKong,
    ClaimPung,
    DeclareConcealedKong,
    DeclareWin,
    Direction,
    Discard,
    Dragon,
    Flower,
    HandOver,
    HiddenDraw,
    Kong,
    Meld,
    OpponentView,
    Pass,
    PlayerView,
    PromoteKong,
    Pung,
    Scoring,
    Season,
    Suited,
    Tile,
    Wind,
)
from pydantic import BaseModel, ConfigDict


class HandPrompt(BaseModel):
    """The complete, task-recorded contract shown to each seat."""

    model_config = ConfigDict(frozen=True)

    tile_rendering: Literal["english", "compact"] = "english"
    rules_text: str = (
        "A legal winning hand has the configured number of melds and one pair and "
        "must meet the configured minimum faan. On your turn, discard one tile "
        "unless you declare a legal win or kong. After a discard, eligible players "
        "may pass, win, pung, kong, or (only when next in turn order) chow. The "
        "referee resolves competing claims. Flowers and seasons are set aside and "
        "replaced automatically. The hand ends on a legal win or when the wall is "
        "exhausted."
    )
    bracketed_action_instructions: str = (
        "You may explain your reasoning, but include exactly one legal action in "
        "square brackets. Only the bracketed legal action counts."
    )
    system_template: str = "{hand_context}\n\n{instructions}"
    default_instructions_template: str = "Rules:\n{rules_text}\n\n{action_instructions}"
    hand_context_template: str = (
        "You are playing Old Hong Kong mahjong as {seat}{dealer_suffix}.\n"
        "Prevailing wind: {prevailing}.\n"
        "A win requires {melds_to_win} melds plus a pair and at least {min_faan} "
        "faan; faan is capped at {faan_cap}.\n"
        "Points by faan: {points}. Payment rule: {payments}.\n"
        "Tile notation: {tile_notation}."
    )
    state_template: str = "Current state:\n{state}"
    turn_template: str = (
        "Public updates since you were last asked:\n{updates}\n\n"
        "{state}\n\nLegal actions: {legal_actions}"
    )
    update_template: str = "- {seat} chose [{action}]."
    all_passed_update_template: str = "- All eligible seats chose [pass]."
    no_updates_text: str = "- None yet."
    invalid_action_template: str = (
        "That did not contain exactly one legal bracketed action. Reply again "
        "with exactly one of: {legal_actions}"
    )


def tile_label(tile: Tile, prompt: HandPrompt) -> str:
    if prompt.tile_rendering == "compact":
        match tile:
            case Suited(suit, number):
                suffix = {"dot": "D", "bamboo": "B", "myriad": "C"}[suit]
                return f"{number}{suffix}"
            case Wind(direction):
                return {"east": "E", "south": "S", "west": "W", "north": "N"}[direction]
            case Dragon(color):
                return {"red": "RD", "green": "GD", "white": "WD"}[color]
            case Flower(number):
                return f"F{number}"
            case Season(number):
                return f"S{number}"
    match tile:
        case Suited(suit, number):
            return f"{number} {suit}"
        case Wind(direction):
            return f"{direction} wind"
        case Dragon(color):
            return f"{color} dragon"
        case Flower(number):
            return f"flower {number}"
        case Season(number):
            return f"season {number}"


def _tiles(tiles: Iterable[Tile], prompt: HandPrompt) -> str:
    rendered = [tile_label(tile, prompt) for tile in tiles]
    return ", ".join(rendered) if rendered else "none"


def _melds(melds: Iterable[Meld], prompt: HandPrompt) -> str:
    rendered: list[str] = []
    for meld in melds:
        match meld:
            case Chow():
                rendered.append(
                    "chow " + " ".join(tile_label(tile, prompt) for tile in meld.tiles)
                )
            case Pung(tile):
                rendered.append(f"pung {tile_label(tile, prompt)}")
            case Kong(tile, concealed):
                kind = "concealed kong" if concealed else "kong"
                rendered.append(f"{kind} {tile_label(tile, prompt)}")
    return "; ".join(rendered) if rendered else "none"


def _opponent_block(seat: Direction, opponent: OpponentView, prompt: HandPrompt) -> str:
    return "\n".join(
        [
            f"{seat.capitalize()}:",
            f"Concealed tiles: {opponent.hand_size}.",
            f"Melds: {_melds(opponent.melds, prompt)}.",
            f"Bonus tiles: {_tiles(opponent.bonus, prompt)}.",
            f"Discards: {_tiles(opponent.discards, prompt)}.",
        ]
    )


def render_view(view: PlayerView, prompt: HandPrompt) -> str:
    lines = [
        f"Tiles left in wall: {view.wall_count}.",
        "",
        "Opponents:",
        "",
        "\n\n".join(
            _opponent_block(seat, opponent, prompt)
            for seat, opponent in view.opponents.items()
        ),
        "",
        f"You ({view.seat}):",
        f"Concealed hand: {_tiles(view.me.hand, prompt)}.",
        f"Melds: {_melds(view.me.melds, prompt)}.",
        f"Bonus tiles: {_tiles(view.me.bonus, prompt)}.",
        f"Discards: {_tiles(view.me.discards, prompt)}.",
        "",
    ]
    match view.phase:
        case AwaitingDiscardView(seat=actor, drawn=drawn, replacement=replacement):
            if isinstance(drawn, HiddenDraw):
                rendered_draw = "a hidden tile"
            elif drawn is None:
                rendered_draw = "no tile (the turn follows a claim)"
            else:
                rendered_draw = tile_label(drawn, prompt)
            draw_kind = "replacement draw" if replacement else "draw"
            lines.append(
                f"Current turn: {actor} must act after {draw_kind}: {rendered_draw}."
            )
        case AwaitingClaims(discarder=discarder, tile=tile):
            lines.append(
                f"Claim window: {discarder} discarded {tile_label(tile, prompt)}."
            )
        case AwaitingKongRob(seat=seat, tile=tile):
            lines.append(
                f"Kong-rob window: {seat} is promoting {tile_label(tile, prompt)}."
            )
        case HandOver():
            lines.append("The hand is over.")
    return "\n".join(lines)


def action_label(action: Action, view: PlayerView, prompt: HandPrompt) -> str:
    match action:
        case Discard(tile):
            return f"discard {tile_label(tile, prompt)}"
        case DeclareConcealedKong(tile):
            return f"concealed kong {tile_label(tile, prompt)}"
        case PromoteKong(tile):
            return f"promote kong {tile_label(tile, prompt)}"
        case DeclareWin():
            return "win"
        case Pass():
            return "pass"
        case ClaimPung():
            return "pung"
        case ClaimKong():
            return "kong"
        case ClaimChow(start):
            if not isinstance(view.phase, AwaitingClaims) or not isinstance(
                view.phase.tile, Suited
            ):
                raise TypeError("a chow action requires a suited discarded tile")
            chow = Chow(view.phase.tile.suit, start)
            return "chow " + " ".join(tile_label(tile, prompt) for tile in chow.tiles)


def actions_by_label(
    actions: Iterable[Action], view: PlayerView, prompt: HandPrompt
) -> dict[str, Action]:
    return {
        action_label(action, view, prompt).casefold(): action
        for action in sorted(actions, key=repr)
    }


def parse_action(reply: str, actions_by_label: Mapping[str, Action]) -> Action | None:
    """Return the sole legal bracketed action, or reject an ambiguous reply."""
    bracketed = [
        " ".join(value.split()).casefold()
        for value in re.findall(r"\[([^\[\]]+)\]", reply)
    ]
    found = [
        actions_by_label[value] for value in bracketed if value in actions_by_label
    ]
    return found[0] if len(found) == 1 else None


def render_system_prompt(
    view: PlayerView,
    scoring: Scoring,
    prompt: HandPrompt,
    instructions_override: str | None = None,
) -> str:
    tile_notation = (
        "D=dot, B=bamboo, C=myriad, E/S/W/N=winds, RD/GD/WD=dragons, F=flower, S=season"
        if prompt.tile_rendering == "compact"
        else "English tile names"
    )
    return prompt.system_template.format(
        hand_context=prompt.hand_context_template.format(
            seat=view.seat,
            dealer_suffix=" (dealer)" if view.seat == view.rules.seats[0] else "",
            prevailing=view.prevailing,
            melds_to_win=view.rules.melds_to_win,
            min_faan=view.rules.min_faan,
            faan_cap=view.rules.faan_cap,
            points=", ".join(
                f"{faan}={points}" for faan, points in sorted(scoring.points.items())
            ),
            payments=scoring.payments.replace("_", " "),
            tile_notation=tile_notation,
        ),
        instructions=instructions_override
        or prompt.default_instructions_template.format(
            rules_text=prompt.rules_text,
            action_instructions=prompt.bracketed_action_instructions,
        ),
    )


def render_turn_prompt(
    view: PlayerView,
    actions_by_label: dict[str, Action],
    updates: Sequence[str],
    prompt: HandPrompt,
) -> str:
    return prompt.turn_template.format(
        updates="\n".join(updates) or prompt.no_updates_text,
        state=prompt.state_template.format(state=render_view(view, prompt)),
        legal_actions=" or ".join(f"[{label}]" for label in actions_by_label),
    )


def render_invalid_prompt(
    actions_by_label: dict[str, Action], prompt: HandPrompt
) -> str:
    return prompt.invalid_action_template.format(
        legal_actions=" or ".join(f"[{label}]" for label in actions_by_label)
    )
