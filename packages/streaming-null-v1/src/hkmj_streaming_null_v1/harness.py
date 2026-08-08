from pathlib import Path

import verifiers.v1 as vf

PROGRAM_SOURCE = (Path(__file__).resolve().parent / "program.py").read_text()


class StreamingNullHarnessConfig(vf.HarnessConfig):
    """Configuration for the one-turn, tool-free streaming harness."""


class StreamingNullHarness(vf.Harness[StreamingNullHarnessConfig]):
    """Make one streaming Chat Completions request and then exit."""

    APPENDS_SYSTEM_PROMPT = True

    async def setup(self, runtime: vf.Runtime) -> None:
        await runtime.prepare_uv_script(PROGRAM_SOURCE, self.config.resolved_env)

    async def launch(
        self,
        ctx: vf.ModelContext,
        trace: vf.Trace,
        runtime: vf.Runtime,
        endpoint: str,
        secret: str,
        mcp_urls: dict[str, str],
        data: vf.TaskData,
    ) -> vf.ProgramResult:
        del mcp_urls
        system_prompt, prompt = self.resolve_prompt(data)
        args = [
            f"--base-url={endpoint}",
            f"--api-key={secret}",
            f"--model={ctx.model}",
        ]
        if system_prompt:
            args.append(f"--system-prompt={system_prompt}")
        if prompt is not None:
            assert isinstance(prompt, str)
            args.append(f"--prompt={prompt}")
        program = await runtime.prepare_uv_script(
            PROGRAM_SOURCE, self.config.resolved_env
        )
        return await runtime.run_program([*program, *args], self.config.resolved_env)
