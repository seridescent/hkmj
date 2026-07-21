# /// script
# requires-python = ">=3.11"
# dependencies = ["openai"]
# ///
"""Make one streamed model request through the Verifiers interception server."""

import argparse
import asyncio

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--system-prompt", default="")
    parser.add_argument("--prompt", default="")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    messages: list[ChatCompletionMessageParam] = []
    if args.system_prompt:
        messages.append({"role": "system", "content": args.system_prompt})
    if args.prompt:
        messages.append({"role": "user", "content": args.prompt})

    async with AsyncOpenAI(base_url=args.base_url, api_key=args.api_key) as client:
        stream = await client.chat.completions.create(
            model=args.model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        )
        async for _ in stream:
            pass


if __name__ == "__main__":
    asyncio.run(main())
