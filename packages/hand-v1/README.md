# Hand v1

`hkmj-hand-v1` is an infinite, seeded taskset and a four-agent Verifiers v1
environment. One task contains both the seed and the native `hkmj_core.State`
returned by `deal`. The state records the exact private hands, wall order,
rules, and opening draw that an episode must use; the seed remains as
provenance. Native `Scoring` and the prompt contract also live in task data.

The environment opens one resumable interaction for each seat and referees the
hand with `hkmj-core`. On a normal turn it samples the acting seat. During a
claim or kong-rob window it asks every eligible seat, with concurrency bounded
by Verifiers' `env.max_concurrent_agents` setting. A model may reason in prose,
but it must put exactly one legal action in square brackets, such as
`[discard 9 myriad]` or `[pung]`. The rollout fails if an interaction terminates
or exhausts its allowed invalid replies.

Prompts are task data. `HandPrompt` carries the rules text, state, update,
system, turn, and invalid-action templates, bracket instructions, and tile
rendering. Fixed hand context goes in the seat's system prompt; turn prompts
contain the changing player view and resolved public updates not yet shown to
that seat. Every saved trace therefore records the prompt contract that
produced it. The rendering and parsing code is ordinary Python and can be
varied without changing the game engine.

Each episode contains four seat-stamped traces. The environment records a
zero-sum `payoff` reward, raw point and outcome metrics, and common replay facts
under `trace.info["hkmj"]`. The serialized native `HandTrace` is an initial
`State` plus one native action map per call to `step`; `play_to_end()`
reconstructs the final core state.

Inspect one resolved task without contacting a model:

```sh
scripts/eval-litellm hkmj-hand-v1 -n 1 --dry-run
```

## Player endpoints

The [human player](../human) supplies a terminal-operated endpoint and an example
config for playing East against three models. Player adapters sit
upstream of the Verifiers interception server as OpenAI-compatible
endpoints with clear model slugs such as `human/local` or
`bot/greedy-v1`. The ordinary resumable null harness captures their calls
as real trace nodes without a special game harness.
