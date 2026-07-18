## Background

I hope for `hkmj` to be a personal project monorepo to house program explorations on what Wikipedia currently calls "Old Hong Kong mahjong", which appears to be basically the ruleset my family plays. I'm not very practiced at mahjong, but I do find it fairly fun, so I figured this could both put me in more contact with the game and yield some interesting programming work.

I expect implementing the core ruleset and gameloop to be fairly straightforward, with the most interesting bits probably being structuring abstractions for varied use-cases and verification. Afterwards, I'm primarily thinking of educational explorations into improving mahjong decision-making in language models. I figure this will motivate the way I write my code and be a low-stakes way to dip my toes into evaluation and probably RL. I'm now familiar with some basics of language model inference and transformers, and this was the next thing I was curious about.

Given the high-level goal, I expect to write code for various things. Bots might come in handy for building familiarity with the game, consuming and refining abstraction design, data generation, and as components of single-agent environments. I expect to fit the mahjong core into frameworks for learning like `verifiers` or Tinker, and to think about and/or play with rewarding strong play. There are many unknown unknowns to me, an engineer with zero ML background, but I am fairly interested in learning :')

## Structure

This monorepo is currently a `uv` workspace, with applications/consumer packages intended to consume a pure and dependency-free core package implementing Hong Kong mahjong.

## Environment

This monorepo currently uses a minimal nix flake for adding `uv`.
I am not expecting to build things with nix right now.
Instead, everything should be encapsulated in this project's definition, likely via `pyproject.toml` files.
