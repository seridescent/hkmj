"""Framework-neutral records of reproducible hand play."""

from collections.abc import Mapping
from dataclasses import dataclass

from hkmj_core.actions import Action
from hkmj_core.state import State
from hkmj_core.tiles import Direction


@dataclass(frozen=True, slots=True)
class HandTrace:
    """An initial state and the ordered action batches applied to it."""

    initial_state: State
    action_batches: tuple[Mapping[Direction, Action], ...]

    def replay(self) -> State:
        """Replay every batch through the native engine."""
        from hkmj_core.engine import step

        state = self.initial_state
        for actions in self.action_batches:
            state, _ = step(state, actions)
        return state
