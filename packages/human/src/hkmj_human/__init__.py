"""Let a human answer requests from an OpenAI-compatible client."""

import argparse
import asyncio
import json
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import uvicorn
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

Answer = Callable[[dict[str, Any]], Awaitable[str]]


class Terminal:
    """Single-line terminal input; cancellation releases the active prompt."""

    def __init__(self) -> None:
        self.session: PromptSession[str] = PromptSession()

    async def __call__(self, body: dict[str, Any]) -> str:
        print(f"\n{'=' * 72}\nModel: {body['model']}")
        if "messages" in body:
            for message in body["messages"]:
                print(f"\n--- {message['role']} ---")
                content = message["content"]
                print(content if isinstance(content, str) else json.dumps(content))
        else:
            print(f"\n--- prompt ---\n{body['prompt']}")
        print("\nEnter sends. Ctrl-D declines this request. Ctrl-C stops the server.")
        return await self.session.prompt_async("assistant> ", handle_sigint=False)


def error(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        {"error": {"message": message, "type": "invalid_request_error"}},
        status_code=status,
    )


def validate(body: Any, chat: bool) -> str | None:
    if not isinstance(body, dict):
        return "Expected a JSON object."
    if not isinstance(body.get("model"), str) or not body["model"]:
        return "model must be a nonempty string."
    if body.get("n", 1) != 1:
        return "Only n=1 is supported."
    if not isinstance(body.get("stream", False), bool):
        return "stream must be a boolean."
    if body.get("tools") or body.get("functions"):
        return "Tool calls are not supported; submit a text prompt."
    if chat:
        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            return "messages must be a nonempty list."
        for message in messages:
            if (
                not isinstance(message, dict)
                or not isinstance(message.get("role"), str)
                or not isinstance(message.get("content"), str)
            ):
                return "Each message must have a string role and text content."
    elif not isinstance(body.get("prompt"), str):
        return "prompt must be a string; batches and token arrays are not supported."
    if body.get("echo") or body.get("suffix"):
        return "echo and suffix are not supported."
    return None


def create_app(answer: Answer) -> Starlette:
    """Create an endpoint with an injectable answer source for other interfaces."""
    lock = asyncio.Lock()

    async def complete(request: Request):
        chat = request.url.path.endswith("/chat/completions")
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            return error("Invalid JSON.")
        if problem := validate(body, chat):
            return error(problem)

        async def respond() -> str:
            async with lock:
                return await answer(body)

        pending = asyncio.create_task(respond())
        try:
            # Cancel abandoned requests, including ones still waiting for the terminal.
            while not pending.done():
                await asyncio.wait({pending}, timeout=0.1)
                if await request.is_disconnected():
                    return error("Client disconnected.", 499)
            content = pending.result()
        except EOFError:
            return error("Human declined this request.", 400)
        finally:
            if not pending.done():
                pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)

        common = {
            "id": f"{'chatcmpl' if chat else 'cmpl'}-{uuid.uuid4().hex}",
            "created": int(time.time()),
            "model": body["model"],
        }
        if not body.get("stream", False):
            choice = (
                {"message": {"role": "assistant", "content": content}}
                if chat
                else {"text": content, "logprobs": None}
            )
            return JSONResponse(
                {
                    **common,
                    "object": "chat.completion" if chat else "text_completion",
                    "choices": [{"index": 0, **choice, "finish_reason": "stop"}],
                }
            )

        async def events():
            for finished in (False, True):
                choice = (
                    {
                        "delta": {}
                        if finished
                        else {"role": "assistant", "content": content}
                    }
                    if chat
                    else {"text": "" if finished else content, "logprobs": None}
                )
                payload = {
                    **common,
                    "object": "chat.completion.chunk" if chat else "text_completion",
                    "choices": [
                        {
                            "index": 0,
                            **choice,
                            "finish_reason": "stop" if finished else None,
                        }
                    ],
                }
                yield f"data: {json.dumps(payload)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    async def models(request: Request):
        return JSONResponse(
            {
                "object": "list",
                "data": [
                    {
                        "id": "human/local",
                        "object": "model",
                        "created": 0,
                        "owned_by": "local",
                    }
                ],
            }
        )

    return Starlette(
        routes=[
            Route("/v1/chat/completions", complete, methods=["POST"]),
            Route("/v1/completions", complete, methods=["POST"]),
            Route("/v1/models", models),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4001)
    args = parser.parse_args()
    print(f"Human endpoint: http://{args.host}:{args.port}/v1\nWaiting for prompts…")
    with patch_stdout():
        uvicorn.run(
            create_app(Terminal()),
            host=args.host,
            port=args.port,
            access_log=False,
            log_level="warning",
            timeout_graceful_shutdown=1,
        )
