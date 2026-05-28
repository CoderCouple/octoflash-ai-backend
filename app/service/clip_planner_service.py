"""
Clip planner — Claude segments a Project's brief into N atomic clip-briefs.

Each clip-brief becomes one Scene row, which then gets its own script_gen +
render. The planner makes one Claude call per project (cached system prompt
keeps repeat costs near zero); the per-clip script_gen calls fan out later.

Output shape:
    [
      {"n": 1, "title": "Hook",          "prompt": "...", "duration": 5.0},
      {"n": 2, "title": "CPU sequential", "prompt": "...", "duration": 8.0},
      ...
    ]

The `prompt` field is rich enough that a downstream script_gen call (which
re-sees the project's full transcript+description anyway) can produce a
focused, single-class Manim scene for just that clip.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.llm import CallKind, ask

logger = logging.getLogger(__name__)


def _coerce_duration(raw: object, fallback: float) -> float:
    """Models sometimes emit durations as `"10s"` or `"~12 seconds"`.
    Strip non-numeric chars and parse; fall back if nothing usable."""
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        m = re.search(r"-?\d+(?:\.\d+)?", raw)
        if m:
            return float(m.group(0))
    return fallback


@dataclass
class PlannedClip:
    n: int  # 1-indexed position in the final video
    title: str
    prompt: str  # creative direction for this clip's script_gen call
    duration: float  # target seconds


_SYSTEM = """You plan rapid-fire, 3Blue1Brown-style educational Manim animations by splitting a longer brief into atomic clip-briefs.

Each clip is one Manim Scene (one MP4) — ~5-15 seconds long. They render in parallel and are concatenated. Clips share no state — each clip starts with a clean frame, so cross-clip continuity (e.g. "this triangle from clip 2") must be re-established by the next clip's prompt.

OUTPUT: ONLY a JSON array. No markdown fences, no commentary. Shape:

[
  {"n": 1, "title": "Short scene title", "prompt": "What this clip shows...", "duration": 5.0},
  {"n": 2, "title": "...", "prompt": "...", "duration": 8.0}
]

Rules:
- Total clip durations must sum within ±10% of the user-requested target.
- Each `prompt` MUST be SELF-CONTAINED — restate the topic at the start since clips share no state across renders.
- For each clip's `prompt`, describe what should appear ON SCREEN visually (axes? formula? labeled diagram? MCQ?) and what the voiceover should say. Be specific so downstream script_gen produces tight code.
- Recommended scene-count by target duration:
    ≤60s   → 4-6 clips × 8-12s each (PORTRAIT shorts)
    90-120s → 6-9 clips × 12-15s each
    180-300s → 10-15 clips × 15-25s each (LANDSCAPE long-form)
- First clip is the HOOK (≤6s) — visual, no narration ramp.
- **Second-to-last clip MUST be an MCQ** (~8-10s): a multiple-choice question testing the central concept, followed by the answer reveal. Use `make_mcq_card(...)` styling — the script generator knows the helper. Phrase the `prompt` as: "Quick quiz: <question> with 3-4 options. Highlight the correct answer in green; dim the others. Voiceover reads the question, pauses, then narrates the answer."
- **Last clip MUST be the brand outro** (~3-4s): call `outro_sequence(self)` from app.manim_pipeline.styles. NO custom takeaway slide. The helper renders the "Octoflash AI / Generated from one prompt. / Make yours at octoflash.ai" end-card with the right typography. Set `title` to "Outro" and `prompt` to: "Render the Octoflash brand outro via `outro_sequence(self)`. No other content — the helper owns the entire frame."
- Middle clips alternate: concept primer → analogy → comparison → recap.
- Make EVERY clip prompt specify a primary visual element (axes/plot, diagram, formula, animated transition, MCQ card). Reject any "text-only slide" temptation.
"""


class ClipPlannerService:
    async def plan(
        self,
        transcript: str,
        description: str,
        manim_prompt: str,
        target_duration: float,
        orientation: str = "portrait",
        max_clips: int = 8,
    ) -> list[PlannedClip]:
        """Single Claude call → list of PlannedClip. Caches system prompt.

        `max_clips` is a hard cap to prevent runaway plans. Claude may produce
        fewer clips than max_clips if the content doesn't warrant more.
        """
        user_msg = (
            f"## Source brief\n\n"
            f"**Transcript:**\n{transcript}\n\n"
            f"**Visual description:**\n{description}\n\n"
            f"**Manim direction:**\n{manim_prompt}\n\n"
            f"## Constraints\n"
            f"- Target total duration: {target_duration:.0f}s\n"
            f"- Orientation: {orientation}\n"
            f"- Max clips: {max_clips} (return FEWER if content allows; don't pad to hit the cap)\n"
            f"\nNow output the JSON array of clip-briefs."
        )

        logger.info(
            "ClipPlannerService.plan: target=%.0fs orient=%s max_clips=%d "
            "transcript_chars=%d",
            target_duration, orientation, max_clips, len(transcript),
        )
        # `/no_think` is a Qwen3 directive that suppresses the <think>...</think>
        # reasoning block. Anthropic ignores it. Cheap to include unconditionally.
        result = await ask(
            kind=CallKind.CLIP_PLANNER,
            system=[{
                "type": "text",
                "text": _SYSTEM + "\n\n/no_think",
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_msg}],
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        logger.info(
            "ClipPlannerService.plan: provider=%s model=%s fell_back=%s",
            result.provider_used, result.model_used, result.fell_back,
        )
        raw = result.text.strip()
        # Strip <think>...</think> blocks emitted by reasoning models when
        # /no_think didn't take effect.
        raw = re.sub(r"<think>.*?</think>\s*", "", raw, flags=re.DOTALL)
        # Strip accidental code fences
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
            raw = re.sub(r"\n?```\s*$", "", raw)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("ClipPlannerService.plan: bad JSON: %s\nraw=%s", e, raw[:1500])
            raise RuntimeError(f"Clip planner returned invalid JSON: {e}") from e

        # Tolerant unwrap: small models often wrap the array in
        # `{"clips": [...]}` or similar. Walk one level of dict-of-lists and
        # pick the first list-of-dicts.
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    data = v
                    break
        if not isinstance(data, list):
            raise RuntimeError(f"Clip planner returned non-list: {type(data).__name__}")

        clips: list[PlannedClip] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                logger.warning("ClipPlannerService.plan: skipping non-dict entry %d", i)
                continue
            # Accept either our spec (`n`/`title`/`prompt`/`duration`) or the
            # `shot_number`/`scene_description` shape some models default to.
            try:
                clips.append(PlannedClip(
                    n=int(item.get("n") or item.get("shot_number") or (i + 1)),
                    title=str(
                        item.get("title")
                        or item.get("name")
                        or f"Clip {i + 1}"
                    ),
                    prompt=str(
                        item.get("prompt")
                        or item.get("scene_description")
                        or item.get("description")
                        or ""
                    ),
                    duration=_coerce_duration(
                        item.get("duration"),
                        fallback=target_duration / max(1, len(data)),
                    ),
                ))
            except (ValueError, TypeError) as e:
                logger.warning("ClipPlannerService.plan: skipping malformed entry %d: %s", i, e)

        if not clips:
            raise RuntimeError("Clip planner produced no usable clips")

        total = sum(c.duration for c in clips)
        logger.info(
            "ClipPlannerService.plan: %d clips, total %.1fs (target %.0fs)",
            len(clips), total, target_duration,
        )
        return clips
