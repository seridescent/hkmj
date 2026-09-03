# Advanced Verifiers v1 patterns

Read only the sections needed when a taskset requires more than the ordinary
`TaskData` → `Task` → `Taskset` flow.

## Contents

- [Reuse built-ins first](#reuse-built-ins-first)
- [Lifecycle and scoring](#lifecycle-and-scoring)
- [Custom tools](#custom-tools)
- [User simulation](#user-simulation)
- [Multi-agent environments](#multi-agent-environments)
- [Custom harnesses](#custom-harnesses)
- [Migration from v0](#migration-from-v0)
- [Images and publishing](#images-and-publishing)

## Reuse built-ins first

Inspect `verifiers.v1.tasksets`, built-in harnesses, and bundled envs before
adding abstractions. In particular, consider `HarborTaskset` for Harbor tasks
and the bundled `best-of-n`, `agentic-judge`, or `user-sim` envs for common
control flow.

Prefer harness-provided bash, search, or other tools over custom MCP servers.
Choose a custom harness only when a built-in cannot express the required agent
program.

## Lifecycle and scoring

Implement `Task.validate(self, runtime)` when ground truth can be checked without
a model. Keep rollout work in this order:

1. `setup(self, trace, runtime)` prepares files or services.
2. The harness runs the agent.
3. `finalize(self, trace, runtime)` captures artifacts needed for scoring.
4. `@vf.reward` and `@vf.metric` evaluate while the runtime remains live.

Raise ordinary Python exceptions from hooks and scoring; the rollout records
them as `TaskError`. Metrics aid observation but do not contribute to reward.

Put judgment comparing sibling traces from one env rollout on
`Env.finalize(task, episode)`. Record values with
`trace.record_reward` and `trace.record_metric` in program order. Do not expect a
live runtime there.

## Custom tools

Use a `vf.Toolset` only when the task strictly needs a custom tool and the chosen
harness supports MCP:

```python
class SearchToolset(vf.Toolset[vf.ToolsetConfig]):
    TOOL_PREFIX = "search"

    @vf.tool
    async def query(self, text: str) -> list[str]:
        """Search the task corpus."""
        return []


class SearchTaskConfig(vf.TaskConfig):
    tools: vf.ToolsetConfig = vf.ToolsetConfig()


class SearchTask(vf.Task[vf.TaskData, vf.State, SearchTaskConfig]):
    @classmethod
    def toolsets(cls, config: SearchTaskConfig) -> list[vf.Toolset]:
        return [SearchToolset(config.tools)]
```

Choose scope from lifetime and filesystem needs:

- Construct task-scoped tools in the `Task.toolsets` classmethod; Verifiers
  launches one server per rollout.
- Set `colocated = true` when the tool must share the harness filesystem or
  processes.
- Use `vf.SharedToolsetConfig` and the `Taskset.toolsets` classmethod for a server
  shared by one environment worker's rollouts.
- Set a toolset config `url` to connect to an existing streamable-HTTP MCP
  service.

Read credentials at the earliest owning boundary so missing values fail clearly.
Do not require a user-managed server unless the contract explicitly uses a
remote URL.

## User simulation

There is no user server or `vf.User`. Drive every scripted, game-engine, or
modeled user through an interaction loop in `Env.run()`:

- Open `agents.<name>.interaction(task)` as an async context manager.
- For a prompted task, call bare `turn()` to receive the agent's opening reply;
  for a prompt-less task, open with `turn(message)`.
- Continue by passing each user reply to `turn(message)`. The harness must
  support resume, either through `SUPPORTS_RESUME` or its own `resume()`.
  The built-in `null` and `bash` harnesses support transcript-backed resume.
- For a modeled user, drive a second agent interaction or use the bundled
  `user-sim` env.

If a prompt describes a hidden user scenario rather than an assistant-facing
opening message, give the assistant interaction a task copy with `prompt=None`
and keep the scenario in another `TaskData` field for scoring and user control.

## Multi-agent environments

Export a `vf.Env` subclass when one rollout contains more than one agent
run and a bundled environment does not cover the control flow.

Declare each agent as a `vf.AgentConfig` field with a default instance on a typed
`vf.EnvConfig` bound through `vf.Env[YourConfig]`. The field name is the agent
name. Put per-agent turn, token, timeout, and retry limits on that field.

Implement imperative `run(task, agents)` control flow and return nothing. Every
completed run joins the episode automatically. Use `setup(agents)` for fixed
standing such as a non-trainable judge, and use `finalize(task, episode)` for
sibling-dependent judgment; `trace.agent.name` identifies the role. Inspect the
bundled envs and upstream `code_golf_v1` reference before inventing a new
pattern.

For a host-refereed game, use the upstream `kuhn_poker` environment as the
control-flow reference: mint prompt-less seat tasks with seat-specific system
prompts, open one live interaction per seat in a single `async with`, and have
the referee call `turn(message)` only for the seats that must act. Concurrent
moves should use `asyncio.gather`. After the contexts close, record terminal
rewards, metrics, and replay facts on each interaction's real trace. Keep this
logic in `Env.run()`; do not move it into a custom harness or parallel fake-game
layer.

## Custom harnesses

Make every model request through the supplied interception `endpoint` and
`secret`; direct provider calls bypass trace capture. Advertise capabilities
accurately:

- `SUPPORTS_MCP`
- `SUPPORTS_RESUME`
- `APPENDS_SYSTEM_PROMPT`
- `EXECUTES_CODE`, `NEEDS_CONTAINER`, and `SUPPORTS_SKILLS` when their defaults
  do not describe the program

Return the `vf.ProgramResult` from `runtime.run_program()` or
`runtime.run_uv_script()`. Do not construct trace nodes by hand.

If the harness creates per-rollout state outside the runtime's disposable
workspace, remove it in an idempotent `cleanup(trace, runtime)` override.

## Migration from v0

Map concepts directly before changing behavior:

| V0 | Native v1 |
| --- | --- |
| Dataset row | Typed `vf.TaskData` subclass |
| `load_environment(**kwargs)` | Exported `vf.Taskset` class and typed config |
| `Rubric` reward function | Task `@vf.reward` method |
| Parser object | Ordinary parsing inside task scoring |
| `ToolEnv` tools | `vf.Toolset` constructed by `Task.toolsets` or `Taskset.toolsets` |
| `MultiTurnEnv.env_response` | Interaction loop in `Env.run()` |
| Dict state | Typed `vf.State` |
| Sandbox subclass | Runtime config and task hooks |

Preserve prompt, tool, and scoring equivalence. Compare representative v0 and
v1 traces where practical.

## Images and publishing

When a task needs a custom container image, use `prime images push`; it builds in
the cloud and does not require local Docker. Name it
`<env>.x86.<task>:latest`. Do not build or publish an image merely because the
taskset mentions one.

After installability, validation, and representative behavior are stable, ask
the user whether Hub visibility should be `PUBLIC` or `PRIVATE`. Publishing is
an external state change. Run
`prime env push <taskset-id> --visibility <visibility>` only after the user
requests it and supplies the visibility.
