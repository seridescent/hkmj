"""Seat-local hand rendering and bracketed action parsing."""

import re
from collections.abc import Iterable, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict

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
    Season,
    Suited,
    Tile,
    Wind,
)


class HandPrompt(BaseModel):
    """The complete, task-recorded contract shown to each seat."""

    model_config = ConfigDict(frozen=True)

    tile_rendering: Literal["english", "compact"] = "english"
    rules_text: str = (
        "A legal winning hand normally has four melds and one pair and must meet "
        "the table's minimum faan. On your turn, discard one tile unless you "
        "declare a legal win or kong. After a discard, eligible players may pass, "
        "win, pung, kong, or (only when next in turn order) chow. The referee "
        "resolves competing claims. Flowers and seasons are set aside and replaced "
        "automatically. The hand ends on a legal win or when the wall is exhausted."
    )
    bracketed_action_instructions: str = (
        "You may explain your reasoning, but include exactly one legal action in "
        "square brackets. Only the bracketed legal action counts."
    )
    system_template: str = (
        "You are playing Old Hong Kong mahjong as {seat}.\n\n"
        "Rules:\n{rules_text}\n\n{action_instructions}"
    )
    state_template: str = "Current state:\n{state}"
    turn_template: str = (
        "Public updates since you were last asked:\n{updates}\n\n"
        "{state}\n\nLegal actions: {legal_actions}"
    )
    update_template: str = "- {seat} chose [{action}]."
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


def _opponent_line(seat: Direction, opponent: OpponentView, prompt: HandPrompt) -> str:
    return (
        f"- {seat}: {opponent.hand_size} concealed tiles; "
        f"melds: {_melds(opponent.melds, prompt)}; "
        f"bonus: {_tiles(opponent.bonus, prompt)}; "
        f"discards: {_tiles(opponent.discards, prompt)}"
    )


def render_view(view: PlayerView, prompt: HandPrompt) -> str:
    lines = [
        f"You are {view.seat}{' (dealer)' if view.seat == view.rules.seats[0] else ''}.",
        f"Prevailing wind: {view.prevailing}.",
        f"Tiles left in wall: {view.wall_count}.",
        f"Your concealed hand: {_tiles(view.me.hand, prompt)}.",
        f"Your melds: {_melds(view.me.melds, prompt)}.",
        f"Your bonus tiles: {_tiles(view.me.bonus, prompt)}.",
        f"Your discards: {_tiles(view.me.discards, prompt)}.",
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
    lines.append("Opponents:")
    lines.extend(
        _opponent_line(seat, opponent, prompt)
        for seat, opponent in view.opponents.items()
    )
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
                raise ValueError("a chow action requires a suited discarded tile")
            chow = Chow(view.phase.tile.suit, start)
            return "chow " + " ".join(tile_label(tile, prompt) for tile in chow.tiles)


def legal_action_map(
    actions: Iterable[Action], view: PlayerView, prompt: HandPrompt
) -> dict[str, Action]:
    return {
        action_label(action, view, prompt).casefold(): action
        for action in sorted(actions, key=repr)
    }


def parse_action(reply: str, legal: dict[str, Action]) -> Action | None:
    """Return the sole legal bracketed action, or reject an ambiguous reply."""
    bracketed = [
        " ".join(value.split()).casefold()
        for value in re.findall(r"\[([^\[\]]+)\]", reply)
    ]
    found = [legal[value] for value in bracketed if value in legal]
    return found[0] if len(found) == 1 else None


def render_system_prompt(seat: Direction, prompt: HandPrompt) -> str:
    return prompt.system_template.format(
        seat=seat,
        rules_text=prompt.rules_text,
        action_instructions=prompt.bracketed_action_instructions,
    )


def render_turn_prompt(
    view: PlayerView,
    legal: dict[str, Action],
    updates: Sequence[str],
    prompt: HandPrompt,
) -> str:
    actions = " or ".join(f"[{label}]" for label in legal)
    state = prompt.state_template.format(state=render_view(view, prompt))
    return prompt.turn_template.format(
        updates="\n".join(updates) or prompt.no_updates_text,
        state=state,
        legal_actions=actions,
    )


def render_invalid_prompt(legal: dict[str, Action], prompt: HandPrompt) -> str:
    actions = " or ".join(f"[{label}]" for label in legal)
    return prompt.invalid_action_template.format(legal_actions=actions)


def render_update(seat: Direction, action: str, prompt: HandPrompt) -> str:
    return prompt.update_template.format(seat=seat, action=action)
