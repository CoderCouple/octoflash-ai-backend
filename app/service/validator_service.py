"""
Validator — enforces hard rules on Claude-generated Manim code.

The system prompt is a *suggestion*; this validator is a *contract*. Anything
that must be true should be checked here, not just asked for in the prompt.

Two layers:
  - `validate(code)` returns a list of human-readable errors (empty = OK).
  - `generate_with_retry(call, validate_fn, max_attempts)` calls `call()` then
    `validate_fn()` and, on failure, re-invokes `call()` with the errors fed
    back as feedback. Stops after the first passing result or `max_attempts`.

Used by `script_generator_service.generate_episode_script` to retry-with-feedback
when Claude produces code that violates the rules. This is meaningfully better
than blind regeneration because each retry sees *why* the previous attempt
failed.
"""

from __future__ import annotations

import ast
import logging
import re
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


# Each entry: (compiled_regex, human_message). Patterns matched anywhere in the
# source are flagged. Be careful — patterns are intentionally tight to avoid
# false positives. Add a fix in the message so the retry knows what to do.
_BANNED_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"(?<!\w)Text\s*\("),
        "Bare `Text(...)` is banned — use `BodyText(...)`, `Title(...)`, or `Caption(...)` "
        "from `app.manim_pipeline.styles` so text picks up the brand color/size automatically.",
    ),
    (
        re.compile(r"self\.camera\.background_color\s*="),
        "Don't set `self.camera.background_color` in scenes — `OctoflashScene.setup()` "
        "already sets it to BG_COLOR. Remove this line.",
    ),
    (
        re.compile(r"^\s*import\s+(os|sys|subprocess|socket|shutil|random)\s*$", re.MULTILINE),
        "Banned import — scenes may not import os/sys/subprocess/socket/shutil/random.",
    ),
    (
        re.compile(r"\bShowCreation\b"),
        "`ShowCreation` is manimgl-only. Use `Create` instead.",
    ),
    (
        re.compile(r"\.get_graph\("),
        "`.get_graph()` is manimgl-only. Use `axes.plot(...)` instead.",
    ),
    (
        re.compile(r"\b(ThreeDAxes|ThreeDScene|Surface|ParametricSurface|Arrow3D)\b"),
        "3D primitives are banned — this is a 2D-only pipeline. Use Axes/Arrow/etc.",
    ),
]


# Each entry: (compiled_regex, human_message). MUST match somewhere in the
# source or it's flagged. Use for "the script must include X".
_REQUIRED_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"from\s+manim\s+import"),
        "Missing `from manim import *` (or equivalent) at the top of the file.",
    ),
    (
        re.compile(r"from\s+app\.manim_pipeline\.styles\s+import"),
        "Missing `from app.manim_pipeline.styles import (...)` — every scene must "
        "import the branded helpers (OctoflashScene/Title/BodyText/Caption/...).",
    ),
    (
        re.compile(r"class\s+\w+\s*\(\s*(OctoflashScene|OctoflashSceneNoVoice|Octoflash3DScene)\b"),
        "Scene class must inherit from `OctoflashScene` (with voiceover), "
        "`OctoflashSceneNoVoice` (no voice), or `Octoflash3DScene`. Plain `Scene` "
        "is rejected — those skip the brand watermark + background.",
    ),
]


def validate(code: str, *, voiceover: bool = True) -> list[str]:
    """Return a list of human-readable validation errors. Empty = pass.

    Always runs the syntax check first; if the code doesn't parse, returns just
    the syntax error and skips the pattern checks (they'd be misleading).

    `voiceover` enforces scene-class / voiceover-call coherence:

      * voiceover=True (default) — script must subclass `OctoflashScene` or
        `Octoflash3DScene` (the VoiceoverScene-backed variants). Plain
        `OctoflashSceneNoVoice` is rejected because the project asked for
        narration.
      * voiceover=False — script must subclass `OctoflashSceneNoVoice` AND
        contain NO `self.voiceover(...)` calls. Otherwise Manim's runtime
        invokes manim-voiceover → ElevenLabs from inside a "no voice"
        render and the subprocess hangs on the HTTP call (root cause of
        the 2026-06-15 generate stall — see scene_render execution_log
        for the post-animation silent freeze).
    """
    if not code or not code.strip():
        return ["Code is empty."]

    # Syntax check first — pattern checks on syntactically-broken code lie.
    try:
        ast.parse(code)
    except SyntaxError as e:
        return [f"SyntaxError at line {e.lineno}: {e.msg}"]

    errors: list[str] = []

    for pattern, message in _BANNED_PATTERNS:
        match = pattern.search(code)
        if match:
            errors.append(f"Banned pattern (found at offset {match.start()}): {message}")

    for pattern, message in _REQUIRED_PATTERNS:
        if not pattern.search(code):
            errors.append(f"Missing required pattern: {message}")

    # ── voiceover-mode coherence ────────────────────────────────────────
    # Single source of truth — runs after the generic pattern check so
    # the broader "must inherit Octoflash*" rule has already fired if
    # the script uses a plain Scene.
    if voiceover:
        if re.search(r"class\s+\w+\s*\(\s*OctoflashSceneNoVoice\b", code):
            errors.append(
                "voiceover=True was requested but the scene class subclasses "
                "`OctoflashSceneNoVoice`. Use `OctoflashScene` (or `Octoflash3DScene`) "
                "so manim-voiceover binds the audio track."
            )
    else:
        if re.search(r"class\s+\w+\s*\(\s*(?:OctoflashScene|Octoflash3DScene)\b", code):
            errors.append(
                "voiceover=False was requested but the scene class subclasses a "
                "VoiceoverScene variant (`OctoflashScene` / `Octoflash3DScene`). "
                "Use `OctoflashSceneNoVoice` instead — otherwise Manim's runtime "
                "calls ElevenLabs and the subprocess hangs on the HTTP request."
            )
        if re.search(r"\bself\.voiceover\s*\(", code):
            errors.append(
                "voiceover=False but the script calls `self.voiceover(...)`. "
                "Remove every voiceover block and replace its timing budget "
                "with `self.wait(N)` calls."
            )

    return errors


async def generate_with_retry(
    call: Callable[[str | None], Awaitable[str]],
    max_attempts: int = 3,
    *,
    voiceover: bool = True,
) -> tuple[str, list[str]]:
    """Call → validate → retry-with-feedback loop.

    `call(feedback)` runs the (Claude) generator. On attempt 1, `feedback` is
    None. On attempts 2+, `feedback` is the concatenated error messages from
    the previous attempt — the generator should fold this into its prompt.

    `voiceover` is forwarded to `validate()` so the mode-coherence checks
    (right scene class, no stray `self.voiceover(` in no-voice scripts)
    apply. The wrong-mode error becomes feedback for the next attempt
    so Claude self-corrects.

    Returns `(passing_code, errors_history)`. If max_attempts is exhausted,
    returns the *last* code and the accumulated errors so the caller can decide
    whether to ship a partial result or raise.

    Logs each attempt so you can see in the smoke output exactly what the
    validator caught and how the retry recovered.
    """
    errors_history: list[str] = []
    last_code = ""
    feedback: str | None = None

    for attempt in range(1, max_attempts + 1):
        logger.info("validator: attempt %d/%d (feedback=%s)",
                    attempt, max_attempts, "yes" if feedback else "no")
        code = await call(feedback)
        last_code = code
        errors = validate(code, voiceover=voiceover)

        if not errors:
            logger.info("validator: attempt %d passed (%d chars)", attempt, len(code))
            return code, errors_history

        logger.warning(
            "validator: attempt %d failed with %d error(s):\n%s",
            attempt, len(errors), "\n".join(f"  - {e}" for e in errors),
        )
        errors_history.extend(errors)
        feedback = (
            f"Your previous attempt failed validation with these {len(errors)} error(s):\n"
            + "\n".join(f"- {e}" for e in errors)
            + "\n\nRegenerate the entire scene, fixing every error listed above."
        )

    logger.error(
        "validator: %d attempts exhausted, returning last (still-failing) code",
        max_attempts,
    )
    return last_code, errors_history
