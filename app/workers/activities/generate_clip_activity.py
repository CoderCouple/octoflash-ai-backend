"""
Generate-clip activity — one clip's script_gen + render + persist.

This is the per-clip unit that fans out in parallel from the workflow. It:
  1. Reads the existing Scene row to check the script_code_hash cache
  2. Generates a fresh Manim script for this clip's prompt (Claude)
  3. Hashes the new script; if it matches the cached hash AND the previous
     MP4 still exists, returns cached (skips Manim entirely)
  4. Otherwise renders via the 4-attempt fallback chain
  5. Persists script_code, hash, video_url, render_method, eval_* onto Scene

Failure isolation: the workflow uses `return_exceptions=True` so one clip's
crash doesn't kill the siblings. This activity raises on render failure;
the workflow then marks just this clip's Scene.status = "failed".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from temporalio import activity

import app.model  # noqa: F401
from app.common.enum.scene import SceneStatus
from app.service.manim_render_service import (
    ClipBrief,
    ManimRenderService,
    hash_script,
)
from app.service.script_generator_service import generate_episode_script
from app.settings import settings
from app.workers.activities.project_activity import (
    GetSceneCacheInput,
    PersistClipResultInput,
    get_scene_cache_activity,
    persist_clip_result_activity,
    video_path,
)


@dataclass
class GenerateClipInput:
    scene_id: str
    project_id: str

    # Per-clip
    n: int
    title: str
    clip_prompt: str
    duration: float

    # Project-level context (denormalized into the input to avoid an extra DB read)
    transcript: str
    description: str
    manim_prompt: str
    orientation: str
    voiceover: bool
    voice_id: str
    quality: str = "ql"

    # Optional source frames (paths relative to STORAGE_DIR root) for vision context
    source_frame_paths: list[str] = field(default_factory=list)


@dataclass
class GenerateClipOutput:
    scene_id: str
    video_file: str
    script_code_hash: str
    render_method: str
    cached: bool
    eval_score: int | None = None


@activity.defn(name="generate_clip")
async def generate_clip_activity(payload: GenerateClipInput) -> GenerateClipOutput:
    """One clip's full lifecycle: script_gen → render → persist."""
    activity.logger.info(
        "generate_clip: scene=%s n=%d title=%r dur=%.1fs orient=%s voiceover=%s",
        payload.scene_id, payload.n, payload.title[:50],
        payload.duration, payload.orientation, payload.voiceover,
    )

    # 1. Read existing Scene cache (script_code, hash, video_url) for skip-if-unchanged
    cache = await get_scene_cache_activity(GetSceneCacheInput(scene_id=payload.scene_id))
    activity.heartbeat("cache_read")

    # 2. Re-hydrate source frame Paths (the input passes relative strings since
    # Temporal serializes via JSON; Path objects don't round-trip cleanly)
    storage_root = Path(settings.local_storage_path or "storage").resolve()
    source_frames = [storage_root / p for p in payload.source_frame_paths if p]

    # 3. Build a per-clip manim_prompt that includes both the project-level brief
    # and this clip's specific direction. The script_generator sees them as one
    # combined prompt — keeps the system prompt cached across all N clips.
    per_clip_brief = (
        f"{payload.manim_prompt}\n\n"
        f"---\n\n"
        f"## THIS CLIP (n={payload.n} of N)\n"
        f"**Title:** {payload.title}\n"
        f"**Duration target:** {payload.duration:.1f}s\n"
        f"**Creative direction for this clip:**\n{payload.clip_prompt}\n\n"
        f"Generate a SINGLE Manim Scene class for THIS clip only. The full video "
        f"is a concatenation of N independent clips; this one runs {payload.duration:.1f}s. "
        f"Hook visually in the first second, end with a clean fade."
    )

    # 4. Generate script — uses the cached system prompt + validator-with-retry
    activity.logger.info("generate_clip: calling script_generator (Claude)...")
    script_code = await generate_episode_script(
        transcript=payload.transcript,
        description=payload.description,
        duration=payload.duration,
        title=payload.title,
        video_id=payload.scene_id,
        voiceover=payload.voiceover,
        source_frames=source_frames or None,
        manin_prompt=per_clip_brief,
        orientation=payload.orientation,
    )
    activity.heartbeat("script_generated")

    # 5. Render — passes prebuilt_script (skips render_clip's own redundant Claude
    # call) and cache hints so an unchanged clip skips the manim subprocess too
    cached_video_path = video_path(cache.video_url)
    brief = ClipBrief(
        clip_id=payload.scene_id,
        transcript=payload.transcript,
        description=payload.description,
        duration=payload.duration,
        title=payload.title,
        orientation=payload.orientation,
        quality=payload.quality,
        voiceover=payload.voiceover,
        voice_id=payload.voice_id,
        source_frames=source_frames,
        manim_prompt=per_clip_brief,
    )

    result = await ManimRenderService().render_clip(
        brief,
        prebuilt_script=script_code,
        cached_script_hash=cache.script_code_hash,
        cached_video_path=cached_video_path,
    )
    activity.heartbeat("rendered")

    # 6. Persist onto the Scene row
    await persist_clip_result_activity(PersistClipResultInput(
        scene_id=payload.scene_id,
        script_code=result.script_code,
        script_code_hash=result.script_code_hash,
        script_file=str(result.scene_file),
        video_url=str(result.video_file),
        render_method=result.render_method.value,
        eval_score=result.eval_score,
        eval_feedback=result.eval_feedback,
        status=SceneStatus.READY.value,
    ))

    activity.logger.info(
        "generate_clip done: scene=%s method=%s cached=%s video=%s",
        payload.scene_id, result.render_method.value, result.cached, result.video_file,
    )
    return GenerateClipOutput(
        scene_id=payload.scene_id,
        video_file=str(result.video_file),
        script_code_hash=result.script_code_hash,
        render_method=result.render_method.value,
        cached=result.cached,
        eval_score=result.eval_score,
    )
