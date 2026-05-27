"""LLM router — single entry point for all Claude / Ollama calls.

Public surface:

    from app.llm import ask, stream, CallKind

    result = await ask(
        kind=CallKind.CLIP_PLANNER,
        messages=[{"role": "user", "content": "..."}],
        system="You plan…",
    )
    print(result.text, result.model_used)

    async for chunk in stream(
        kind=CallKind.SCRIPT_GEN,
        messages=[...],
        system=[{"type": "text", "text": "…", "cache_control": {"type": "ephemeral"}}],
    ):
        print(chunk.delta, end="")

Routing policy (set in app.settings):

    OLLAMA_BASE_URL set     → local-first; fall back to anthropic.
    OLLAMA_BASE_URL empty   → anthropic-only (legacy behavior).
    LLM_FALLBACK_ENABLED=false → primary only, no fallback.

Per-call-kind override via env: ROUTING_<KIND>_PRIMARY / _FALLBACK with
LiteLLM-style model strings (`anthropic/claude-opus-4-7`, `ollama/qwen3.5:14b`).

Adapter: LiteLLM. One unified call shape across providers; Anthropic-only
features (`cache_control`) pass through to Anthropic and are silently
stripped for Ollama (LiteLLM handles the normalization).
"""

from app.llm.kinds import CallKind
from app.llm.router import (
    AskResult,
    StreamChunk,
    ask,
    stream,
)

__all__ = ["CallKind", "AskResult", "StreamChunk", "ask", "stream"]
