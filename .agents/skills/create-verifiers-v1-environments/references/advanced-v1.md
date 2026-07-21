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

Inspect `verifiers.v1.tasksets`, built-in harnesses, and bundled environments
before adding abstractions. In particular, consider `HarborTaskset` for Harbor
tasks and the bundled `best-of-n` or `agentic-judge` environments for common
multi-agent control flow.

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

Put judgment comparing sibling traces from one environment rollout on
`Environment.finalize(task, episode)`. Record values with
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
    tools = (SearchToolset,)
```

Choose scope from lifetime and filesystem needs:

- Declare task-scoped tools on `Task.tools`; Verifiers launches one server per
  rollout.
- Set `colocated = true` when the tool must share the harness filesystem or
  processes.
- Use `vf.SharedToolsetConfig` and `Taskset.tools` for a server shared by one
  worker's rollouts.
- Set a toolset config `url` to connect to an existing streamable-HTTP MCP
  service.

Read credentials at the earliest owning boundary so missing values fail clearly.
Do not require a user-managed server unless the contract explicitly uses a
remote URL.

## User simulation

Use `vf.User` when the taskset, rather than the harness, drives a simulated
conversation. Verify that the selected harness advertises `SUPPORTS_USER_SIM`;
many CLI harnesses do not, while the built-in bash harness does.

## Multi-agent environments

Export an `Environment` subclass when one rollout contains more than one agent
run and a bundled environment does not cover the control flow.

Declare each agent as an `vf.AgentConfig` field on a typed `vf.EnvConfig` bound
through `Environment[YourConfig]`. The field name is the agent name. Put
per-agent turn, token, timeout, and retry limits on that field.

Implement imperative `run(task, agents)` control flow. Every completed run joins
the episode automatically. Use `setup(agents)` for fixed standing such as a
non-trainable judge, and use `finalize(task, episode)` for sibling-dependent
judgment. Inspect the bundled environments and the upstream `code_golf_v1`
reference before inventing a new pattern.

## Custom harnesses

Make every model request through the supplied interception `endpoint` and
`secret`; direct provider calls bypass trace capture. Advertise capabilities
accurately:

- `SUPPORTS_MCP`
- `SUPPORTS_USER_SIM`
- `SUPPORTS_MESSAGE_PROMPT`
- `APPENDS_SYSTEM_PROMPT`

Return the `vf.ProgramResult` from `runtime.run_program()` or
`runtime.run_uv_script()`. Do not construct trace nodes by hand.

## Migration from v0

Map concepts directly before changing behavior:

| V0 | Native v1 |
| --- | --- |
| Dataset row | Typed `vf.TaskData` subclass |
| `load_environment(**kwargs)` | Exported `vf.Taskset` class and typed config |
| `Rubric` reward function | Task `@vf.reward` method |
| Parser object | Ordinary parsing inside task scoring |
| `ToolEnv` tools | `vf.Toolset` on `Task.tools` or `Taskset.tools` |
| `MultiTurnEnv.env_response` | `vf.User` on the task |
| Dict state | Typed `vf.State` |
| Sandbox subclass | Runtime config and task hooks |

Preserve prompt, tool, and scoring equivalence. Compare representative v0 and
v1 traces where practical.

## Images and publishing

When a task needs a custom image, use the user-approved image workflow and keep
image names scoped to the environment and task. Do not build or publish an image
merely because the taskset mentions one.

After installability, validation, and representative behavior are stable, ask
the user whether Hub visibility should be `PUBLIC` or `PRIVATE`. Publishing is
an external state change. Run `prime env push` only after the user requests it
and supplies the visibility.
