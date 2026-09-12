# Human player

`hkmj-human` is a local OpenAI-compatible server whose responses you write in
an ordinary terminal. It has no dependency on the mahjong core or Verifiers.

Start it in one terminal:

```sh
uv run --package hkmj-human hkmj-human
```

Point a client at `http://127.0.0.1:4001/v1`, with model `human/local` and any
nonempty dummy API key. Each request prints its full conversation, then waits
at `assistant>`. Type a reply such as `[discard 9 myriad]` and press Enter.
Ctrl-D declines the current request; Ctrl-C stops the server. Concurrent
requests wait their turn. Disconnected requests release the terminal.

Try it from another terminal:

```sh
curl http://127.0.0.1:4001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"human/local","messages":[{"role":"user","content":"Your move?"}]}'
```

The endpoint implements `POST /v1/chat/completions`, `POST /v1/completions`
(string prompts), and `GET /v1/models`. Both completion routes accept
`stream: true`: after Enter, the complete reply arrives as an SSE content
chunk, a stop chunk, and `[DONE]`. It does not stream keystrokes. Token usage
is omitted because there is no model tokenizer. Sampling settings are ignored;
your reply is returned verbatim. This first version supports text, one reply
per request, and single-line input. It rejects tool definitions and prompt
batches. It has no authentication and binds to loopback by default.

## Play East

Keep your ordinary model endpoint running on port 4000. With the human server
in a separate terminal, run:

```sh
scripts/eval-litellm hkmj-hand-v1 -n 1
```

The shared `config/verifiers/litellm-eval.toml` routes East through the human
endpoint and leaves the other three seats on the ordinary model endpoint.
Verifiers still intercepts the calls and
records your responses in its normal traces. Change the top-level model to
choose your opponents. Run from your usual evaluation directory if it supplies
credentials or runtime configuration. Client and rollout deadlines still apply
while you think; this server does not extend them.

For another UI, pass an async callable taking the request body and returning a
string to `hkmj_human.create_app`. HTTP handling and terminal input are separate
so the interface can evolve without changing the client contract.
