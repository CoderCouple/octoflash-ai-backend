"""Unit tests for the LLM router fallback logic.

Mocks the LiteLLM adapter so we don't hit real providers. Covers the four
behaviors from the plan:

  1. No fallback configured + primary raises → re-raises.
  2. Fallback configured + primary raises RateLimitError → fallback's
     text is returned.
  3. Fallback configured + primary raises BadRequestError with
     "credit balance is too low" → fallback fires (special-cased).
  4. Fallback configured + primary raises a non-retriable error
     (AuthenticationError) → fallback is NOT called.

Tests env-override the per-kind ROUTING_<KIND>_PRIMARY / _FALLBACK keys
because the default chain depends on whether OLLAMA_BASE_URL is set in
the developer's `.env.local`. Override leaves the test deterministic.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import litellm
import pytest

from app.llm import CallKind, ask
from app.llm.litellm_adapter import AdapterResult


def _stub(text: str = "ok", model: str = "stub") -> AdapterResult:
    return AdapterResult(text=text, model_used=model, usage=None)


@pytest.fixture(autouse=True)
def _pin_chain(monkeypatch: pytest.MonkeyPatch):
    """Pin the routing chain for the CLIP_PLANNER kind via env so the
    test doesn't depend on whether OLLAMA_BASE_URL is configured in the
    developer's shell."""
    monkeypatch.setenv("ROUTING_CLIP_PLANNER_PRIMARY", "ollama/qwen3.5:14b")
    yield


@pytest.mark.asyncio
async def test_no_fallback_reraises():
    """`ROUTING_<KIND>_FALLBACK=""` (empty) → primary error propagates."""
    os.environ["ROUTING_CLIP_PLANNER_FALLBACK"] = ""
    try:
        boom = litellm.exceptions.RateLimitError(
            "rate limited", model="ollama/qwen3.5:14b", llm_provider="ollama",
        )
        with patch(
            "app.llm.router.litellm_adapter.acompletion",
            new=AsyncMock(side_effect=boom),
        ):
            with pytest.raises(litellm.exceptions.RateLimitError):
                await ask(kind=CallKind.CLIP_PLANNER, messages=[{"role": "user", "content": "hi"}])
    finally:
        os.environ.pop("ROUTING_CLIP_PLANNER_FALLBACK", None)


@pytest.mark.asyncio
async def test_rate_limit_triggers_fallback(monkeypatch: pytest.MonkeyPatch):
    """Primary RateLimitError → fallback runs and its text is returned."""
    monkeypatch.setenv("ROUTING_CLIP_PLANNER_FALLBACK", "anthropic/claude-opus-4-7")

    primary_err = litellm.exceptions.RateLimitError(
        "rate limited", model="ollama/qwen3.5:14b", llm_provider="ollama",
    )
    fallback_ok = _stub(text="fallback-text", model="anthropic/claude-opus-4-7")
    mock_complete = AsyncMock(side_effect=[primary_err, fallback_ok])

    with patch("app.llm.router.litellm_adapter.acompletion", new=mock_complete):
        result = await ask(
            kind=CallKind.CLIP_PLANNER,
            messages=[{"role": "user", "content": "hi"}],
        )

    assert result.text == "fallback-text"
    assert result.fell_back is True
    assert result.provider_used == "anthropic"
    assert mock_complete.await_count == 2


@pytest.mark.asyncio
async def test_credit_balance_400_triggers_fallback(monkeypatch: pytest.MonkeyPatch):
    """Anthropic's BadRequest with 'credit balance is too low' is treated
    as a rate-limit-equivalent — fallback fires (relevant when a kind has
    been pinned hosted-first via override)."""
    monkeypatch.setenv("ROUTING_CLIP_PLANNER_PRIMARY", "anthropic/claude-opus-4-7")
    monkeypatch.setenv("ROUTING_CLIP_PLANNER_FALLBACK", "ollama/qwen3.5:14b")

    cred_err = litellm.exceptions.BadRequestError(
        "Your credit balance is too low to access the Anthropic API.",
        model="anthropic/claude-opus-4-7",
        llm_provider="anthropic",
    )
    fallback_ok = _stub(text="local-rescued", model="ollama/qwen3.5:14b")
    mock_complete = AsyncMock(side_effect=[cred_err, fallback_ok])

    with patch("app.llm.router.litellm_adapter.acompletion", new=mock_complete):
        result = await ask(
            kind=CallKind.CLIP_PLANNER,
            messages=[{"role": "user", "content": "hi"}],
        )

    assert result.text == "local-rescued"
    assert result.fell_back is True
    assert result.provider_used == "ollama"


@pytest.mark.asyncio
async def test_auth_error_does_not_trigger_fallback(monkeypatch: pytest.MonkeyPatch):
    """AuthenticationError isn't in the retriable set — bubbles up
    without touching the fallback."""
    monkeypatch.setenv("ROUTING_CLIP_PLANNER_FALLBACK", "anthropic/claude-opus-4-7")

    auth_err = litellm.exceptions.AuthenticationError(
        "bad key", model="ollama/qwen3.5:14b", llm_provider="ollama",
    )
    mock_complete = AsyncMock(side_effect=auth_err)

    with patch("app.llm.router.litellm_adapter.acompletion", new=mock_complete):
        with pytest.raises(litellm.exceptions.AuthenticationError):
            await ask(
                kind=CallKind.CLIP_PLANNER,
                messages=[{"role": "user", "content": "hi"}],
            )

    # Fallback should NOT have run.
    assert mock_complete.await_count == 1
