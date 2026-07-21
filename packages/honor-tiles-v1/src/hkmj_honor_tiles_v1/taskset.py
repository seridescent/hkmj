"""Verifiers taskset for recognizing honor tiles."""

import verifiers.v1 as vf
from hkmj_core import full_tile_set, tile_sort_key

from hkmj_honor_tiles_v1.tiles import is_honor, tile_label


class HonorTileData(vf.TaskData):
    """One tile face and its reference classification."""

    answer: str


class HonorTileTask(vf.Task[HonorTileData]):
    """Score an exact `honor` or `not honor` response."""

    @vf.reward
    async def exact_match(self, trace: vf.Trace) -> float:
        return float(trace.last_reply.strip().casefold() == self.data.answer)


class HonorTilesTaskset(vf.Taskset[HonorTileTask, vf.TasksetConfig]):
    """A finite taskset containing every distinct Hong Kong mahjong tile face."""

    def load(self) -> list[HonorTileTask]:
        tiles = sorted(set(full_tile_set()), key=tile_sort_key)
        return [
            HonorTileTask(
                HonorTileData(
                    idx=idx,
                    prompt=(
                        f'Is the mahjong tile "{tile_label(tile)}" an honor tile? '
                        'Reply with exactly "honor" or "not honor", without '
                        "quotation marks."
                    ),
                    answer="honor" if is_honor(tile) else "not honor",
                ),
                self.config.task,
            )
            for idx, tile in enumerate(tiles)
        ]
