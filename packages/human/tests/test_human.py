import asyncio

import httpx
import pytest
from hkmj_human import create_app
from openai import AsyncOpenAI


@pytest.mark.parametrize("chat", [False, True])
@pytest.mark.parametrize("stream", [False, True])
def test_sdk_roundtrip(chat, stream):
    async def run():
        seen = []

        async def answer(body):
            seen.append(body)
            return "thinking… [discard 9 myriad]"

        async with AsyncOpenAI(
            base_url="http://human/v1",
            api_key="dummy",
            http_client=httpx.AsyncClient(
                transport=httpx.ASGITransport(app=create_app(answer))
            ),
        ) as client:
            if chat:
                result = await client.chat.completions.create(
                    model="human/local",
                    messages=[{"role": "user", "content": "Move?"}],
                    stream=stream,
                )
            else:
                result = await client.completions.create(
                    model="human/local", prompt="Move?", stream=stream
                )
            if stream:
                chunks = [chunk async for chunk in result]
                assert chunks[-1].choices[0].finish_reason == "stop"
                text = "".join(
                    (chunk.choices[0].delta.content or "")
                    if chat
                    else chunk.choices[0].text
                    for chunk in chunks
                )
            else:
                assert result.choices[0].finish_reason == "stop"
                text = (
                    result.choices[0].message.content
                    if chat
                    else result.choices[0].text
                )
            assert text == "thinking… [discard 9 myriad]"
            assert len(seen) == 1

    asyncio.run(run())


def test_requests_serialize_and_cancel():
    async def run():
        entered = asyncio.Event()
        release = asyncio.Event()
        prompts = []

        async def answer(body):
            prompts.append(body["prompt"])
            entered.set()
            await release.wait()
            return body["prompt"]

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(answer)),
            base_url="http://human",
        ) as client:

            async def send(prompt):
                return await client.post(
                    "/v1/completions", json={"model": "human/local", "prompt": prompt}
                )

            first = asyncio.create_task(send("first"))
            await entered.wait()
            second = asyncio.create_task(send("second"))
            await asyncio.sleep(0.02)
            assert prompts == ["first"]
            first.cancel()
            await asyncio.gather(first, return_exceptions=True)
            release.set()
            response = await asyncio.wait_for(second, 2)
            assert response.json()["choices"][0]["text"] == "second"
            assert prompts == ["first", "second"]

    asyncio.run(run())


def test_invalid_request_and_decline():
    async def run():
        called = 0

        async def answer(body):
            nonlocal called
            called += 1
            raise EOFError

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(answer)),
            base_url="http://human",
        ) as client:
            for body in [
                [],
                {},
                {"model": "human/local", "prompt": ["a", "b"]},
                {"model": "human/local", "prompt": "x", "n": 2},
            ]:
                response = await client.post("/v1/completions", json=body)
                assert response.status_code == 400
                assert "error" in response.json()
            assert called == 0
            response = await client.post(
                "/v1/completions", json={"model": "human/local", "prompt": "x"}
            )
            assert response.status_code == 400
            assert "declined" in response.json()["error"]["message"]

    asyncio.run(run())
