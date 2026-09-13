"""Framework-neutral records of reproducible hand play."""

from collections.abc import Mapping
from dataclasses import dataclass

from hkmj_core.actions import Action
from hkmj_core.state import HandOver, State
from hkmj_core.tiles import Direction


@dataclass(frozen=True, slots=True)
class HandTrace:
    """An initial state and the ordered action batches applied to it."""

    initial_state: State
    action_batches: tuple[Mapping[Direction, Action], ...]

    def play_to_end(self) -> State:
        """Apply every recorded action batch and return the completed hand."""
        from hkmj_core.engine import step

        state = self.initial_state
        for actions in self.action_batches:
            state, _ = step(state, actions)
        if not isinstance(state.phase, HandOver):
            raise ValueError(  # noqa: TRY004 -- the action sequence is incomplete
                "hand trace ends before the hand is over"
            )
        return state
