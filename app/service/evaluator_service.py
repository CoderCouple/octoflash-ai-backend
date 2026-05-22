"""
Evaluator — Claude vision compares rendered output frames vs source frames.

Thin wrapper over `script_generator_service.evaluate_output` so the renderer's
improvement loop has a one-purpose import (and so a future swap to a stronger
evaluator model / different prompt can land here without touching the script
generator).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict

from app.service.script_generator_service import evaluate_output

logger = logging.getLogger(__name__)


class EvaluationResult(TypedDict):
    score: int  # 1-10
    passed: bool  # True if score >= 7
    feedback: str  # specific code-level fixes


class EvaluatorService:
    async def evaluate(
        self,
        output_frame_paths: list[Path],
        transcript: str,
        script_code: str,
        source_frame_paths: list[Path] | None = None,
    ) -> EvaluationResult:
        """Score a rendered clip's frames against the source and the transcript.

        Returns `{score: 1-10, passed: bool, feedback: str}`. Renderer's
        improvement loop regenerates when `passed=False` (default threshold: <7).
        """
        result = await evaluate_output(
            output_frame_paths=output_frame_paths,
            transcript=transcript,
            script_code=script_code,
            source_frame_paths=source_frame_paths,
        )
        return result  # type: ignore[return-value]
