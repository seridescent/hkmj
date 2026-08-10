---
name: create-verifiers-v1-environments
description: Create or migrate native verifiers.v1 taskset, Env, toolset, and harness packages in the hkmj uv workspace. Use when adding a Hong Kong mahjong evaluation taskset under packages/, exposing core game data to models, adding tools or user-driven interaction, building multi-agent control flow or a harness, running local Verifiers evaluations, or migrating a v0 environment to typed v1 traces.
---

# Create hkmj Verifiers environments

Build each evaluation as a small workspace package that consumes `hkmj-core` and
exports native `verifiers.v1` classes.

## Choose the smallest contract

Define the dataset fields, prompts, reference answers, scoring, and configurable
values before writing code. Prefer deterministic scoring. Use an LLM judge only
when semantic judgment is unavoidable.

Start with a taskset alone. Add a toolset, interaction loop, `Env`, or custom
harness only when the rollout cannot use a built-in harness and ordinary task
hooks. Read [references/advanced-v1.md](references/advanced-v1.md) before adding
any of those components, migrating v0 code, using custom images, or publishing.

For ports, preserve source rows, prompts, restrictions, score extraction, and
exceptions before improving the design. Ask about unresolved semantic choices
instead of inventing them.

## Follow the repository package layout

Use `packages/honor-tiles-v1` as the local template. Do not run `init` directly
into this repository: its generic scaffold uses a flat Hatchling layout and does
not follow this workspace's conventions. If the installed Verifiers contract may
have changed, generate a scaffold in a temporary directory and compare it with
the local template.

Name a taskset consistently:

| Item | Pattern | Example |
| --- | --- | --- |
| Directory | `packages/<task>-v1` | `packages/honor-tiles-v1` |
| Distribution/taskset id | `hkmj-<task>-v1` | `hkmj-honor-tiles-v1` |
| Import package | `hkmj_<task>_v1` | `hkmj_honor_tiles_v1` |

Use a `src/` layout, include `py.typed`, require Python 3.12 or later, and build
with the same `uv_build` range as `hkmj-core`:

```toml
[project]
name = "hkmj-example-v1"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "hkmj-core",
    "verifiers",
]

[build-system]
requires = ["uv_build>=0.11.28,<0.12.0"]
build-backend = "uv_build"
```

Keep Mahjong rules, tile models, game logic, and broadly reusable presentation
in `hkmj-core`. Keep the taskset package as a thin translation from core values
to prompts, task data, and rewards.

## Respect workspace dependency ownership

Declare every import-time dependency in the member package. Declare
`hkmj-core` and plain `verifiers` as shown above.

The root `pyproject.toml` owns shared uv policy:

- `constraint-dependencies` pins the workspace's Verifiers version;
- `[tool.uv.sources]` maps `hkmj-core` to the workspace member;
- the root `uv.lock` resolves every member together.

Do not add a member lockfile, repeat the exact Verifiers pin in each member, or
use `uv pip install -e`. Run `uv lock` at the repository root after adding a
member or dependency. Change the root constraint or source only when the shared
workspace policy itself should change.

Use `uv run --package <distribution>` for commands that need one package's
runtime dependencies. Use `uv run --all-packages` when a command must load
independent local plugins, such as a taskset and a harness. If `uv` is not on
`PATH`, use the repository's Nix shell or `nix run nixpkgs#uv -- ...`.

## Implement the native v1 contract

Use only `verifiers.v1` objects:

```python
import verifiers.v1 as vf
```

Export one `vf.Taskset` subclass through `__all__`. Optionally export a `vf.Env`
or `vf.Harness` subclass when the contract needs one. Do not add
`load_environment`, `load_taskset`, or `load_harness` functions, and do not mix
v0 `Environment`, `Rubric`, `Parser`, or `*Env` objects into the package.

Keep the basic implementation direct:

```python
class ExampleData(vf.TaskData):
    answer: str


class ExampleTask(vf.Task[ExampleData]):
    @vf.reward
    async def exact_match(self, trace: vf.Trace) -> float:
        return float(trace.last_reply == self.data.answer)


class ExampleTaskset(vf.Taskset[ExampleTask, vf.TasksetConfig]):
    def load(self) -> list[ExampleTask]:
        return [
            ExampleTask(
                ExampleData(idx=0, prompt="...", answer="..."),
                self.config.task,
            )
        ]
```

Do not override `Taskset.__init__`.

Apply these ownership rules:

- Put immutable, serializable row values on `TaskData`.
- Put hooks, stop conditions, rewards, metrics, and task-facing config on `Task`.
- Put dataset loading, split, seed, selection-time concerns, and shared
  task-agnostic toolsets on `Taskset`.
- Use typed `vf.State` for live counters or coordination.
- Put inspectable JSON-serializable artifacts in `trace.info`.
- Use the provided `vf.Runtime` in hooks instead of assuming a runtime backend.

## Keep validation proportional

Do not add tests by default for a trivial adapter. Add tests when parsing,
sampling, state, lifecycle behavior, or scoring has enough logic to fail in a
non-obvious way. Test reusable Mahjong behavior in `hkmj-core`, not again in
every taskset.

For a normal taskset change:

1. Run `uv lock --check` after the lock has been updated.
2. Run Ruff check and format-check on the member's `src/` directory.
3. Run ty on the member's `src/` directory with `--package`.
4. Import the export and materialize representative tasks as a smoke check.
5. Run a Verifiers dry run without contacting a model.

Run the existing core test suite when core code changes. Do not run a paid or
model-backed evaluation unless the user asks for it.

## Use the shared local evaluation workflow

Evaluate through the repository launcher so every worktree uses
`config/verifiers/litellm-eval.toml` and writes UUID-scoped results beneath the
main checkout's `outputs/` directory:

```bash
scripts/eval-litellm hkmj-example-v1 --dry-run
scripts/eval-litellm hkmj-example-v1 -n 5 --no-push
```

During automated dry-run validation, pass `-o` with a temporary directory so a
config-only check does not clutter the main checkout. Remember that an explicit
`output_dir` is the complete run directory and suppresses the usual UUID path.

A dry run writes only the resolved `config.toml`. A real evaluation also writes
`traces.jsonl` and `eval.log`. Treat local proxy availability and credentials as
external prerequisites; do not start services or publish results without the
user's request.
