# Streaming null v1

This package provides a one-turn Verifiers v1 harness with no tools or agent
loop. It sends the task prompt through the supplied interception endpoint using
a streaming OpenAI Chat Completions request, consumes the response, and exits.

The streaming request avoids provider adapters that fail while assembling a
non-streaming response. Verifiers still owns model selection, sampling, trace
capture, retries, and scoring.

Select it with:

```sh
uv run --all-packages eval <taskset-id> --harness.id hkmj-streaming-null-v1
```
