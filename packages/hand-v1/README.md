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
`[discard 9 myriad]` or `[pung]`.

Prompts are task data. `HandPrompt` carries the rules text, state, update,
system, turn, and invalid-action templates, bracket instructions, and tile
rendering. Every saved trace therefore records the prompt contract that
produced it. The rendering and parsing code is ordinary Python and can be
varied without changing the game engine.

Each episode contains four seat-stamped traces. The environment records a
zero-sum `payoff` reward, raw point and outcome metrics, and common replay facts
under `trace.info["hkmj"]`. The serialized native `HandTrace` is an initial
`State` plus one native action map per call to `step`; replay reconstructs the
final core state.

Inspect one resolved task without contacting a model:

```sh
scripts/eval-litellm hkmj-hand-v1 -n 1 --dry-run
```

## Player endpoints

Local human and non-LLM player adapters are out of scope. To evaluate one, put
it upstream of the Verifiers interception server as an OpenAI-compatible
endpoint and give it a clear model slug such as `human/local` or
`bot/greedy-v1`. The ordinary resumable null harness will then capture its calls
as real trace nodes without a special game harness.
