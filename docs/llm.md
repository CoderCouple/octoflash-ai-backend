# LLM router

Every Claude / Ollama call goes through `app/llm/`. Services never
import `anthropic` or `litellm` directly — they call `ask()` or
`stream()` and the router picks a provider per `CallKind`.

## Policy (local-first)

When `OLLAMA_BASE_URL` is set:

- primary  = `ollama/<text|vision model>` (per kind)
- fallback = `anthropic/<settings.script_model>`

When `OLLAMA_BASE_URL` is empty: anthropic-only, no fallback (the
legacy behavior — drop the env var to opt out of routing entirely).

The fallback fires on retriable errors: rate-limit, 5xx, connection
refused, timeout, Ollama 404 ("model not pulled"), and the
Anthropic-specific 400 "credit balance is too low".

Non-retriable errors (auth, malformed request) propagate as-is.

## Setup

```bash
brew install ollama && brew services start ollama
ollama pull qwen3:8b       # text  — planner / script_gen / stream helper
ollama pull qwen3-vl:8b     # vision — synthesize / evaluate / analyze_source
```

Then in `.env.local`:

```
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_TEXT_MODEL=qwen3:8b
OLLAMA_VISION_MODEL=qwen3-vl:8b
LLM_FALLBACK_ENABLED=true
```

`ANTHROPIC_API_KEY` is still required — without it the fallback can't
fire.

## Per-kind override

Pin one `CallKind` to a different provider without rebuilding. Format
is `<provider>/<model>`. Setting `FALLBACK=""` disables the fallback
for that kind.

```
ROUTING_SCRIPT_GEN_PRIMARY=anthropic/claude-opus-4-7
ROUTING_SCRIPT_GEN_FALLBACK=ollama_chat/qwen3:8b
```

The six kinds: `CLIP_PLANNER`, `SCRIPT_GEN`, `SYNTHESIZE`,
`EVALUATE`, `ANALYZE_SOURCE`, `STREAM_HELPER`.

## Verifying fallback

With Ollama running, kill `ANTHROPIC_API_KEY` (or set it to an invalid
value) and trigger `POST /api/v1/projects/from-source`. Worker logs
will show `provider=ollama fell_back=false` on the analyze step. Then
flip the override:

```
ROUTING_ANALYZE_SOURCE_PRIMARY=anthropic/claude-opus-4-7
ROUTING_ANALYZE_SOURCE_FALLBACK=ollama_chat/qwen3-vl:8b
```

with bad anthropic creds — log line becomes
`provider=ollama fell_back=true`.

## Out of scope (deferred)

- Cost-based routing (route to local when prompt > N tokens) — add
  as a `policy=` arg later.
- Per-workspace privacy mode (one workspace never touches hosted) —
  needs `UserContext` threaded into the LLM layer.
- Streaming partial-failure recovery (mid-stream switch). Current
  design re-runs the whole stream on the fallback when the error
  arrives before the first delta; mid-stream errors propagate.
