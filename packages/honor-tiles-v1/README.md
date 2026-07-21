# Honor tiles v1

This package is a small Verifiers v1 taskset. It asks a model whether a
plain-English tile name, such as `3 dot` or `white dragon`, is an honor tile.

It contains one task for each of the 42 distinct tile faces in an Old Hong
Kong mahjong set: 27 suited tiles, 7 honor tiles, and 8 bonus tiles. Winds and
dragons are positive examples; suited and bonus tiles are negative examples.
This makes the first version easy to inspect, though it is not class-balanced:
an always-`not honor` baseline scores 35 out of 42.

Inspect the resolved evaluation configuration without calling a model:

```sh
uv run --package hkmj-honor-tiles-v1 eval hkmj-honor-tiles-v1 --dry-run
```

Then supply a model and any endpoint configuration required by Verifiers:

```sh
uv run --package hkmj-honor-tiles-v1 eval hkmj-honor-tiles-v1 --model <model-id>
```

The implementation is split between `tiles.py`, which turns core tile values
into task data, and `taskset.py`, which contains the small amount of
Verifiers-specific code.
