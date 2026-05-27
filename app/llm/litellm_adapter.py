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


def _normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic content blocks to OpenAI-compatible ones.

    LiteLLM validates messages in OpenAI shape before dispatching, so
    Anthropic-style `{type: image, source: {type: base64, media_type, data}}`
    blocks fail validation even when the target is Anthropic. Convert
    image blocks to `{type: image_url, image_url: {url: data:…;base64,…}}`
    (which LiteLLM re-maps back to Anthropic's format on the way out).
    """
    out: list[dict[str, Any]] = []
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            out.append(msg)
            continue
        new_content: list[Any] = []
        for block in content:
            if not isinstance(block, dict):
                new_content.append(block)
                continue
            btype = block.get("type")
            if btype == "image" and isinstance(block.get("source"), dict):
                src = block["source"]
                if src.get("type") == "base64":
                    media = src.get("media_type", "image/jpeg")
                    data = src.get("data", "")
                    new_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{media};base64,{data}"},
                    })
                elif src.get("type") == "url":
                    new_content.append({
                        "type": "image_url",
                        "image_url": {"url": src.get("url", "")},
                    })
                else:
                    new_content.append(block)
            elif btype == "text":
                # Strip Anthropic-only `cache_control` from inline text
                # blocks — keeping it confuses LiteLLM's validator on the
                # OpenAI path.
                new_content.append({"type": "text", "text": block.get("text", "")})
            else:
                new_content.append(block)
        out.append({**msg, "content": new_content})
    return out


def _normalize_system(system: Any, target_model: str) -> Any:
    """For non-Anthropic targets, collapse a `[{type: text, text, cache_control}]`
    system list into a plain string. Anthropic keeps the structured form
    (cache_control is meaningful there)."""
    if system is None:
        return None
    if target_model.startswith("anthropic/"):
        return system
    if isinstance(system, str):
        return system
    if isinstance(system, list):
        parts = []
        for block in system:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n\n".join(parts)
    return system


@dataclass
class AdapterResult:
    text: str
    model_used: str
    usage: dict[str, Any] | None


@dataclass
class AdapterStreamChunk:
    """One streamed delta. `delta` is the text fragment added by the model;
    `done` is True when the stream terminates (and `text` carries the
    full concatenated text). `usage` is populated on the final chunk
    when the provider reports it (Anthropic always does, Ollama doesn't)."""

    delta: str
    done: bool = False
    text: str | None = None
    model_used: str | None = None
    usage: dict[str, Any] | None = None


async def acompletion(
    *,
    model: str,
    messages: list[dict[str, Any]],
    system: str | list[dict[str, Any]] | None,
    max_tokens: int,
    temperature: float,
    timeout: float | None = None,
    response_format: dict[str, Any] | None = None,
) -> AdapterResult:
    """Non-streaming completion. Returns the full text once.

    Anthropic accepts a `system` parameter alongside `messages`. LiteLLM
    follows Anthropic's contract when the model is `anthropic/*` and
    converts to OpenAI-style `{"role": "system", "content": …}` for
    Ollama. We always pass via the `system` kwarg and let LiteLLM map.

    `response_format={"type": "json_object"}` enforces parseable JSON
    output (passed through to Ollama as `format: "json"` and to
    Anthropic as the prefill/stop trick — LiteLLM handles the mapping).
    """
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": _normalize_messages(messages),
        "max_tokens": max_tokens,
        "temperature": temperature,
        **_provider_kwargs(model),
    }
    normalized_system = _normalize_system(system, model)
    if normalized_system is not None:
        kwargs["system"] = normalized_system
    if timeout is not None:
        kwargs["timeout"] = timeout
    if response_format is not None:
        kwargs["response_format"] = response_format

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
        "messages": _normalize_messages(messages),
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        **_provider_kwargs(model),
    }
    normalized_system = _normalize_system(system, model)
    if normalized_system is not None:
        kwargs["system"] = normalized_system
    if timeout is not None:
        kwargs["timeout"] = timeout

    # Ask providers that support it (OpenAI-compat, Anthropic via LiteLLM)
    # to include usage on the final stream chunk.
    kwargs["stream_options"] = {"include_usage": True}

    response = await litellm.acompletion(**kwargs)

    parts: list[str] = []
    last_usage: dict[str, Any] | None = None
    async for chunk in response:
        delta = ""
        try:
            delta = chunk.choices[0].delta.content or ""
        except Exception:  # noqa: BLE001
            delta = ""
        # Some providers send usage on the very last chunk (which has no
        # delta). Capture whenever it appears.
        chunk_usage = getattr(chunk, "usage", None)
        if chunk_usage is not None:
            try:
                last_usage = chunk_usage.model_dump()
            except AttributeError:
                last_usage = dict(chunk_usage) if isinstance(chunk_usage, dict) else None
        if delta:
            parts.append(delta)
            yield AdapterStreamChunk(delta=delta, done=False)

    yield AdapterStreamChunk(
        delta="",
        done=True,
        text="".join(parts),
        model_used=model,
        usage=last_usage,
    )
