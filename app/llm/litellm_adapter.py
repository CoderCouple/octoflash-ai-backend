"""Thin wrapper around LiteLLM. Owns the provider-specific kwargs.

`litellm.acompletion(model="anthropic/claude-opus-4-7", ...)` and
`litellm.acompletion(model="ollama/qwen3.5:14b", api_base=..., ...)` both
flow through here. The function:

  * builds per-provider `api_base` / `api_key` kwargs from app.settings,
  * forwards `messages`, `system`, `max_tokens`, `temperature`,
  * routes streaming vs non-streaming via the same SDK,
  * returns (`AskResult` | async iterator of `StreamChunk`) so the router
    can hand the result to callers without them caring about the SDK.

We don't strip Anthropic-specific blocks here. LiteLLM normalizes the
shape between Anthropic and OpenAI-compatible endpoints. `cache_control`
on system blocks is passed through to Anthropic and silently ignored by
Ollama (which doesn't honor it).

Errors surface raw — the router catches retriable subclasses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator

import litellm

from app.settings import settings

log = logging.getLogger(__name__)


# Honor explicit api_base via the call. LiteLLM also reads OLLAMA_API_BASE,
# but passing api_base= per-call keeps the routing layer the only place
# that touches provider config.
def _provider_kwargs(model: str) -> dict[str, Any]:
    """Build the per-provider extra kwargs LiteLLM expects."""
    if model.startswith("ollama/") or model.startswith("ollama_chat/"):
        # LiteLLM rejects empty api_key on Ollama — pass the sentinel.
        return {
            "api_base": settings.ollama_base_url or None,
            "api_key": settings.ollama_api_key or "ollama",
        }
    if model.startswith("anthropic/"):
        return {"api_key": settings.anthropic_api_key or None}
    return {}


@dataclass
class AdapterResult:
    text: str
    model_used: str
    usage: dict[str, Any] | None


@dataclass
class AdapterStreamChunk:
    """One streamed delta. `delta` is the text fragment added by the model;
    `done` is True when the stream terminates (and `text` carries the
    full concatenated text)."""

    delta: str
    done: bool = False
    text: str | None = None
    model_used: str | None = None


async def acompletion(
    *,
    model: str,
    messages: list[dict[str, Any]],
    system: str | list[dict[str, Any]] | None,
    max_tokens: int,
    temperature: float,
    timeout: float | None = None,
) -> AdapterResult:
    """Non-streaming completion. Returns the full text once.

    Anthropic accepts a `system` parameter alongside `messages`. LiteLLM
    follows Anthropic's contract when the model is `anthropic/*` and
    converts to OpenAI-style `{"role": "system", "content": …}` for
    Ollama. We always pass via the `system` kwarg and let LiteLLM map.
    """
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        **_provider_kwargs(model),
    }
    if system is not None:
        kwargs["system"] = system
    if timeout is not None:
        kwargs["timeout"] = timeout

    response = await litellm.acompletion(**kwargs)

    # LiteLLM returns a ModelResponse with .choices[0].message.content.
    text = ""
    try:
        text = response.choices[0].message.content or ""
    except Exception:  # noqa: BLE001
        # Shouldn't happen on a 2xx; surface an empty string and let the
        # caller decide whether that's acceptable.
        log.warning("LiteLLM response missing choices[0].message.content")

    usage = None
    try:
        usage = response.usage.model_dump() if response.usage else None
    except Exception:  # noqa: BLE001
        usage = None

    return AdapterResult(text=text, model_used=model, usage=usage)


async def astream(
    *,
    model: str,
    messages: list[dict[str, Any]],
    system: str | list[dict[str, Any]] | None,
    max_tokens: int,
    temperature: float,
    timeout: float | None = None,
) -> AsyncIterator[AdapterStreamChunk]:
    """Streaming completion. Yields deltas; the final chunk carries the
    full concatenated text + done=True so the caller can persist."""
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        **_provider_kwargs(model),
    }
    if system is not None:
        kwargs["system"] = system
    if timeout is not None:
        kwargs["timeout"] = timeout

    response = await litellm.acompletion(**kwargs)

    parts: list[str] = []
    async for chunk in response:
        delta = ""
        try:
            delta = chunk.choices[0].delta.content or ""
        except Exception:  # noqa: BLE001
            delta = ""
        if delta:
            parts.append(delta)
            yield AdapterStreamChunk(delta=delta, done=False)

    yield AdapterStreamChunk(
        delta="",
        done=True,
        text="".join(parts),
        model_used=model,
    )
