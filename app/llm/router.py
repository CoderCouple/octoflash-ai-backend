"""Routing logic: build [primary, *fallbacks] for a CallKind, then walk
the chain on retriable errors.

Public surface (exported via `app.llm.__init__`):

    AskResult, StreamChunk, ask, stream

Defaults per CallKind (computed lazily from settings — so env updates
under `uvicorn --reload` flow through without restart):

    primary  = ollama/<text|vision model> if OLLAMA_BASE_URL is set,
               else anthropic/<settings.script_model>
    fallback = anthropic/<settings.script_model> when local is primary
               (and llm_fallback_enabled is true), else none

Per-kind override via env:

    ROUTING_<KIND>_PRIMARY   = "ollama_chat/qwen3:14b"   (etc)
    ROUTING_<KIND>_FALLBACK  = "anthropic/claude-opus-4-7" | ""

Falls back to defaults above when unset.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator

import litellm

from app.llm import litellm_adapter
from app.llm.kinds import CallKind, is_vision
from app.settings import settings

log = logging.getLogger(__name__)


@dataclass
class AskResult:
    text: str
    model_used: str
    provider_used: str          # "anthropic" | "ollama" | …
    fell_back: bool             # True when the primary errored and we used a fallback
    usage: dict[str, Any] | None


@dataclass
class StreamChunk:
    """Streamed delta from `stream()`. `done=True` on the final chunk
    carries the full concatenated `text` + `model_used`."""

    delta: str
    done: bool = False
    text: str | None = None
    model_used: str | None = None
    provider_used: str | None = None
    fell_back: bool = False


# Errors that mean "this provider is unhealthy — try the next one in the
# chain". Local-first → we expect connection-refused (Ollama not running),
# 404 (model not pulled), and stalled completions to fire.
_RETRIABLE_ERRORS: tuple[type[BaseException], ...] = (
    litellm.exceptions.RateLimitError,
    litellm.exceptions.ServiceUnavailableError,
    litellm.exceptions.InternalServerError,
    litellm.exceptions.APIConnectionError,
    litellm.exceptions.Timeout,
    litellm.exceptions.NotFoundError,
)


def _is_credit_balance_400(err: BaseException) -> bool:
    """Anthropic returns 400 BadRequest with a 'credit balance is too low'
    message when the account is out of credits. LiteLLM raises this as
    BadRequestError, which we'd otherwise treat as a hard error. Treat
    it like a rate-limit so the fallback fires."""
    if not isinstance(err, litellm.exceptions.BadRequestError):
        return False
    text = str(err).lower()
    return "credit balance is too low" in text or "billing" in text


def _is_retriable(err: BaseException) -> bool:
    if isinstance(err, _RETRIABLE_ERRORS):
        return True
    if _is_credit_balance_400(err):
        return True
    return False


def _provider_of(model_spec: str) -> str:
    """`"ollama_chat/qwen3:14b"` → `"ollama_chat"`. Anything before the first `/`."""
    return model_spec.split("/", 1)[0]


def _default_primary(kind: CallKind) -> str:
    """Pick the default primary model for this kind.

    Local-first when OLLAMA_BASE_URL is set; else fall through to the
    hosted model (legacy behavior).
    """
    if settings.ollama_base_url:
        model = (
            settings.ollama_vision_model if is_vision(kind) else settings.ollama_text_model
        )
        # `ollama_chat/` routes through Ollama's /api/chat (supports
        # system + messages + vision properly). `ollama/` would hit
        # /api/generate which has a different request shape.
        return f"ollama_chat/{model}"
    return f"anthropic/{settings.script_model}"


def _default_fallback(kind: CallKind, primary: str) -> str | None:
    """Pick the default fallback. Only relevant when primary != hosted —
    nothing to fall back to if hosted is already primary."""
    if not settings.llm_fallback_enabled:
        return None
    if _provider_of(primary) == "anthropic":
        # Primary already hosted — no fallback. (User can pin a local
        # fallback via ROUTING_<KIND>_FALLBACK if they want.)
        return None
    if not settings.anthropic_api_key:
        return None
    _ = kind  # reserved for future per-kind hosted-model selection
    return f"anthropic/{settings.script_model}"


def _chain_for(kind: CallKind) -> list[str]:
    """Resolve [primary, *fallbacks] for this CallKind.

    Reads env first (`ROUTING_<KIND>_PRIMARY` / `_FALLBACK`), falls back
    to the computed defaults from settings. Empty-string env values mean
    "no fallback" — distinct from unset, which means "use default".
    """
    primary_env = os.environ.get(f"ROUTING_{kind.value}_PRIMARY")
    fallback_env = os.environ.get(f"ROUTING_{kind.value}_FALLBACK")

    primary = primary_env if primary_env else _default_primary(kind)

    if fallback_env is None:
        fallback = _default_fallback(kind, primary)
    elif fallback_env == "":
        fallback = None
    else:
        fallback = fallback_env

    chain = [primary]
    if fallback and fallback != primary:
        chain.append(fallback)
    return chain


# ─── public API ────────────────────────────────────────────────────────────

async def ask(
    *,
    kind: CallKind,
    messages: list[dict[str, Any]],
    system: str | list[dict[str, Any]] | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: float | None = None,
) -> AskResult:
    """Non-streaming. Walk the chain on retriable errors; raise the last
    error if every entry fails."""
    chain = _chain_for(kind)
    last_err: BaseException | None = None
    for attempt_idx, model in enumerate(chain):
        try:
            result = await litellm_adapter.acompletion(
                model=model,
                messages=messages,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
            return AskResult(
                text=result.text,
                model_used=result.model_used,
                provider_used=_provider_of(model),
                fell_back=attempt_idx > 0,
                usage=result.usage,
            )
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt_idx + 1 < len(chain) and _is_retriable(e):
                log.warning(
                    "LLM router: kind=%s primary=%s raised %s — falling back to %s",
                    kind.value, model, type(e).__name__, chain[attempt_idx + 1],
                )
                continue
            raise
    # Chain exhausted — re-raise the last error. (Should be unreachable
    # given the loop's `raise` above; kept for type-checker clarity.)
    assert last_err is not None
    raise last_err


async def stream(
    *,
    kind: CallKind,
    messages: list[dict[str, Any]],
    system: str | list[dict[str, Any]] | None = None,
    max_tokens: int = 8192,
    temperature: float = 0.7,
    timeout: float | None = None,
) -> AsyncIterator[StreamChunk]:
    """Streaming. Falls back BEFORE the first delta if the primary errors
    immediately — but once tokens start flowing, mid-stream errors do not
    trigger fallback (re-running the whole stream is the caller's job)."""
    chain = _chain_for(kind)
    last_err: BaseException | None = None
    for attempt_idx, model in enumerate(chain):
        agen = litellm_adapter.astream(
            model=model,
            messages=messages,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
        yielded_any = False
        try:
            async for ad_chunk in agen:
                yielded_any = True
                yield StreamChunk(
                    delta=ad_chunk.delta,
                    done=ad_chunk.done,
                    text=ad_chunk.text,
                    model_used=ad_chunk.model_used,
                    provider_used=_provider_of(model) if ad_chunk.done else None,
                    fell_back=attempt_idx > 0 if ad_chunk.done else False,
                )
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
            # Only fall back if we haven't started emitting deltas yet —
            # otherwise the consumer would receive duplicate / spliced output
            # from two providers. Mid-stream errors propagate.
            if (
                not yielded_any
                and attempt_idx + 1 < len(chain)
                and _is_retriable(e)
            ):
                log.warning(
                    "LLM router (stream): kind=%s primary=%s raised %s — falling back to %s",
                    kind.value, model, type(e).__name__, chain[attempt_idx + 1],
                )
                continue
            raise
    assert last_err is not None
    raise last_err
