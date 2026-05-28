"""Semantic labels for each LLM callsite in the codebase.

Each kind maps to one routing chain (primary + fallback) configured in
settings. Names mirror the function names in app/service/ so callers can
pass `kind=CallKind.CLIP_PLANNER` and ops can override that single
callsite via `ROUTING_CLIP_PLANNER_PRIMARY=anthropic/...`.

`is_vision` tells the router which default model (text vs vision) to use
when OLLAMA_BASE_URL is set and no per-kind override is provided.
"""

from __future__ import annotations

from enum import Enum


class CallKind(str, Enum):
    """Semantic label for each LLM callsite. Pass to ask()/stream()."""

    CLIP_PLANNER = "CLIP_PLANNER"
    SCRIPT_GEN = "SCRIPT_GEN"
    SYNTHESIZE = "SYNTHESIZE"
    EVALUATE = "EVALUATE"
    ANALYZE_SOURCE = "ANALYZE_SOURCE"
    STREAM_HELPER = "STREAM_HELPER"


# Callsites that pass image blocks to the model. The router routes these
# to settings.ollama_vision_model when the local primary is Ollama, and to
# the same hosted model regardless when the primary is anthropic
# (Claude's text/vision are the same model).
#
# SCRIPT_GEN is here because generate_episode_script attaches up to 6
# source frames as vision input when a Project has a source video.
_VISION_KINDS: frozenset[CallKind] = frozenset(
    {
        CallKind.SYNTHESIZE,
        CallKind.EVALUATE,
        CallKind.ANALYZE_SOURCE,
        CallKind.SCRIPT_GEN,
    }
)


def is_vision(kind: CallKind) -> bool:
    return kind in _VISION_KINDS
