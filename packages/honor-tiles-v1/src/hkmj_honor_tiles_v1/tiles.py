"""Plain-text presentation and classification of tile faces."""

from hkmj_core import Dragon, Flower, Season, Suited, Tile, Wind


def tile_label(tile: Tile) -> str:
    """Render a tile in the small vocabulary used by this taskset."""
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


def is_honor(tile: Tile) -> bool:
    """Return whether a tile is a wind or dragon."""
    return isinstance(tile, (Wind, Dragon))
