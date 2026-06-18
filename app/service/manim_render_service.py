"""
Manim render service — script → MP4, with the MVP's 4-attempt fallback chain
and vision-eval improvement loop.

Ported from `/Users/suniltiwari/Desktop/octoflash-ai/app/manim_pipeline/renderer.py`.
Differences from the MVP:
  - Async at the boundary (`render_clip`) so it composes with the rest of the
    request path; subprocess + ffprobe + ffmpeg are wrapped in `asyncio.to_thread`.
  - No `update_job` calls — Job status writes go through the Temporal
    `update_job_activity` instead (the workflow patches the Job between activities).
  - No simple-fallback (attempt 4 in MVP). Three Claude paths is plenty for v1;
    if all three fail, we raise and the workflow marks the clip failed.
  - No `_create_watermark_image` / `_apply_watermark` — the watermark is now
    baked into the Manim scene by `OctoflashScene.setup()` (see styles.py).
  - Storage rooted at `settings.local_storage_path` instead of a hand-computed path.

The 4-attempt chain:
  1. Claude script WITH voiceover (`OctoflashScene` + `manim-voiceover`)
  1b. Fresh Claude voice script with feedback (one retry before downgrading)
  2. `strip_voiceover` of attempt 1's output (`OctoflashSceneNoVoice`, no audio)
  3. Fresh Claude no-voice script

After a successful render: vision eval ≤3 loops, regenerating with feedback if
the score is < 7.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from app.common.enum.scene import RenderMethod
from app.service.evaluator_service import EvaluatorService
from app.service.script_generator_service import (
    generate_episode_script,
    save_script,
    sanitize_script,
    strip_voiceover,
)
from app.settings import settings

logger = logging.getLogger(__name__)


STORAGE_DIR = Path(settings.local_storage_path or "storage").resolve()
MAX_IMPROVEMENT_ITERATIONS = 3


# ─── public types ──────────────────────────────────────────────────────────────


@dataclass
class ClipBrief:
    """Everything the renderer needs to produce one clip's MP4.

    The workflow constructs this from the Project's brief (transcript +
    description + manim_prompt) plus the Scene's per-clip prompt and duration.
    """

    clip_id: str  # used as the storage subdirectory (e.g. scn_<uuid>)
    transcript: str
    description: str
    duration: float
    title: str
    orientation: str = "portrait"  # "portrait" | "landscape"
    quality: str = "qm"  # manim quality flag: ql / qm / qh / qk
    voiceover: bool = True
    voice_id: str = ""  # passed to manim subprocess as OCTOFLASH_VOICE_ID
    source_frames: list[Path] = field(default_factory=list)
    manim_prompt: str = ""


@dataclass
class RenderResult:
    """Output of `render_clip`. Caller persists the relevant bits onto Scene."""

    scene_file: Path
    video_file: Path
    script_code: str
    script_code_hash: str  # sha256 of script_code — store on Scene.script_code_hash for cache lookups
    render_method: RenderMethod
    cached: bool = False  # True if skip-if-unchanged hit; nothing was re-rendered
    eval_score: int | None = None
    eval_feedback: str | None = None
    output_frames_dir: Path | None = None


def hash_script(code: str) -> str:
    """Stable sha256 hex of a Manim script. Used as the cache key for render skip."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


class RenderError(RuntimeError):
    """All fallback attempts failed."""


# ─── service ───────────────────────────────────────────────────────────────────


class ManimRenderService:
    async def render_clip(
        self,
        brief: ClipBrief,
        prebuilt_script: str | None = None,
        cached_script_hash: str | None = None,
        cached_video_path: Path | None = None,
        log_sink: object | None = None,
    ) -> RenderResult:
        """Run the 4-attempt fallback chain + improvement loop.

        If `prebuilt_script` is given (e.g. the workflow already called
        script_generator in a previous activity), we skip the orchestrator's
        own step1 Claude call and use it directly — saves ~$0.30 and ~60s per
        render.

        If `cached_script_hash` + `cached_video_path` are given AND the hash of
        `prebuilt_script` matches AND the cached MP4 still exists on disk, we
        return early with `cached=True` and no rendering happens at all. This
        is the skip-if-unchanged guard: editing a Project's voice settings or
        re-running an unchanged clip costs ~0s instead of ~60s + ElevenLabs.

        Raises `RenderError` on total failure.
        """
        portrait = (brief.orientation or "portrait").lower() == "portrait"
        logger.info(
            "render_clip start: clip=%s title=%r dur=%.1fs orient=%s voiceover=%s "
            "frames=%d prebuilt_script=%s cached_hash=%s",
            brief.clip_id, brief.title[:60], brief.duration, brief.orientation,
            brief.voiceover, len(brief.source_frames),
            "yes ({} chars)".format(len(prebuilt_script)) if prebuilt_script else "no",
            "yes" if cached_script_hash else "no",
        )

        # ── Step 0: skip-if-unchanged — return cached result with no render ──
        if prebuilt_script and cached_script_hash and cached_video_path:
            new_hash = hash_script(prebuilt_script)
            if new_hash == cached_script_hash and cached_video_path.exists():
                logger.info(
                    "render_clip: CACHE HIT for clip=%s (hash=%s) — returning %s "
                    "without re-rendering",
                    brief.clip_id, new_hash[:12], cached_video_path,
                )
                scene_file = (
                    STORAGE_DIR / "renders" / brief.clip_id / "scene.py"
                )
                return RenderResult(
                    scene_file=scene_file,
                    video_file=cached_video_path,
                    script_code=prebuilt_script,
                    script_code_hash=new_hash,
                    render_method=RenderMethod.CLAUDE_VOICE,  # method is whatever last produced it; caller can override
                    cached=True,
                )
            logger.info(
                "render_clip: cache miss (new_hash=%s, cached=%s, file_exists=%s) — full render",
                new_hash[:12],
                cached_script_hash[:12] if cached_script_hash else None,
                cached_video_path.exists() if cached_video_path else None,
            )

        # ── Step 1: get a Claude script — either pre-built or freshly generated ──
        claude_code: str | None = None
        script_file_path: Path | None = None
        if prebuilt_script:
            claude_code = prebuilt_script
            script_file_path = save_script(brief.clip_id, claude_code)
            logger.info(
                "step1 skipped: using prebuilt_script (%d chars), saved to %s",
                len(claude_code), script_file_path,
            )
        else:
            try:
                claude_code = await generate_episode_script(
                    transcript=brief.transcript,
                    description=brief.description,
                    duration=brief.duration,
                    title=brief.title,
                    video_id=brief.clip_id,
                    voiceover=brief.voiceover,
                    source_frames=brief.source_frames or None,
                    manin_prompt=brief.manim_prompt,
                    orientation=brief.orientation,
                )
                script_file_path = save_script(brief.clip_id, claude_code)
                logger.info(
                    "step1 ok: %d chars, voiceover=%s, saved to %s",
                    len(claude_code), brief.voiceover, script_file_path,
                )
            except Exception as e:
                logger.error("step1 failed: %s: %s", type(e).__name__, e)

        # ── Step 2: render with fallback chain ──
        scene_code: str | None = None
        result: dict | None = None
        method: RenderMethod | None = None

        # Attempt 1 — Claude script with voiceover
        if claude_code and brief.voiceover:
            try:
                logger.info("attempt 1: claude+voice (%d chars)", len(claude_code))
                result = await self._render_scene_subprocess(
                    brief.clip_id, claude_code, brief.quality, portrait, brief.voice_id,
                    log_sink=log_sink,
                )
                scene_code, method = claude_code, RenderMethod.CLAUDE_VOICE
            except Exception as e:
                logger.error("attempt 1 failed: %s", str(e)[:500])

        # Attempt 1b — fresh voice retry. The previous comment ("removed to
        # save cost; fresh-voice regenerates rarely succeed") was true when
        # the voice failure was a deterministic Manim bug; it's wrong when
        # the failure is an ElevenLabs hiccup or a transient stream error.
        # The product invariant is "every clip has its own audio" — losing
        # voice on a clip is worse than spending one extra Claude call to
        # try again. If 1 + 1b both fail we now raise RenderError so the
        # workflow's per-clip gather records the failure rather than
        # silently producing a no-voice clip the ffmpeg_concat then drops
        # audio on (see ffmpeg_concat_service for the related concat fix).
        if result is None and brief.voiceover:
            try:
                logger.info("attempt 1b: fresh voice from Claude")
                fresh_voice = await generate_episode_script(
                    transcript=brief.transcript,
                    description=brief.description,
                    duration=brief.duration,
                    title=brief.title,
                    video_id=brief.clip_id,
                    voiceover=True,
                    source_frames=brief.source_frames or None,
                    manin_prompt=brief.manim_prompt,
                    orientation=brief.orientation,
                )
                result = await self._render_scene_subprocess(
                    brief.clip_id, fresh_voice, brief.quality, portrait, brief.voice_id,
                    log_sink=log_sink,
                )
                scene_code, method = fresh_voice, RenderMethod.CLAUDE_VOICE_RETRY
                script_file_path = save_script(brief.clip_id, fresh_voice)
            except Exception as e:
                logger.error("attempt 1b failed: %s", str(e)[:500])

        # No more attempts — if voice failed twice, we fail the clip rather
        # than fall back to a no-audio render. The previous attempts 2
        # (strip_voiceover) and 3 (fresh_no_voice) were removed because they
        # produced clips with no audio, which broke "every clip has its own
        # voice" as a product invariant.

        if result is None or scene_code is None or method is None:
            raise RenderError(
                f"Voice render attempts exhausted for clip {brief.clip_id} "
                "— see logs for per-attempt failure details. Fallback to no-voice "
                "has been intentionally removed to preserve the every-clip-has-audio "
                "invariant; the workflow's per-clip gather treats this as a failed clip."
            )

        # ── Step 3: improvement loop (only for Claude-generated scripts) ──
        eval_score: int | None = None
        eval_feedback: str | None = None
        video_file = Path(result["video_file"])
        if video_file.exists():
            result, scene_code, eval_score, eval_feedback = await self._improvement_loop(
                clip_id=brief.clip_id,
                current_result=result,
                current_code=scene_code,
                brief=brief,
                log_sink=log_sink,
            )
            video_file = Path(result["video_file"])

        # ── Step 4: extract output frames for the UI preview grid ──
        output_frames_dir: Path | None = None
        if video_file.exists():
            try:
                output_frames_dir = STORAGE_DIR / "renders" / brief.clip_id / "output_frames"
                output_frames_dir.mkdir(parents=True, exist_ok=True)
                await asyncio.to_thread(
                    _extract_output_frames, video_file, output_frames_dir,
                )
            except Exception as e:
                logger.warning("output frame extraction failed: %s", e)

        final_hash = hash_script(scene_code)
        logger.info(
            "render_clip done: method=%s video=%s hash=%s",
            method.value, video_file, final_hash[:12],
        )
        return RenderResult(
            scene_file=Path(result["scene_file"]),
            video_file=video_file,
            script_code=scene_code,
            script_code_hash=final_hash,
            render_method=method,
            cached=False,
            eval_score=eval_score,
            eval_feedback=eval_feedback,
            output_frames_dir=output_frames_dir,
        )

    # ── internals ─────────────────────────────────────────────────────────────

    async def _render_scene_subprocess(
        self,
        clip_id: str,
        scene_code: str,
        quality: str,
        portrait: bool,
        voice_id: str,
        log_sink: object | None = None,
    ) -> dict:
        """Write scene.py and run `manim` as a subprocess. Returns paths + stderr."""
        return await asyncio.to_thread(
            _render_scene_sync, clip_id, scene_code, quality, portrait, voice_id,
            log_sink,
        )

    async def _improvement_loop(
        self,
        clip_id: str,
        current_result: dict,
        current_code: str,
        brief: ClipBrief,
        log_sink: object | None = None,
    ) -> tuple[dict, str, int | None, str | None]:
        """Run evaluate → regenerate → re-render up to MAX_IMPROVEMENT_ITERATIONS times.

        Returns the final (result, code, last_score, last_feedback). Keeps the
        last successfully-rendered version if a regen attempt errors out.
        """
        result, code = current_result, current_code
        portrait = (brief.orientation or "portrait").lower() == "portrait"
        evaluator = EvaluatorService()
        last_score: int | None = None
        last_feedback: str | None = None

        for it in range(MAX_IMPROVEMENT_ITERATIONS):
            video_path = result.get("video_file")
            if not video_path or not Path(video_path).exists():
                break

            try:
                output_frames = await asyncio.to_thread(
                    _extract_video_frames, Path(video_path), 8,
                )
                if not output_frames:
                    logger.warning("eval: no output frames extracted; stopping loop")
                    break

                evaluation = await evaluator.evaluate(
                    output_frame_paths=output_frames,
                    transcript=brief.transcript,
                    script_code=code,
                    source_frame_paths=brief.source_frames or None,
                )
                last_score = evaluation["score"]
                last_feedback = evaluation["feedback"]
                logger.info("eval iter %d: score=%d", it + 1, last_score)

                if evaluation["passed"]:
                    logger.info("eval passed (score=%d); stopping loop", last_score)
                    break

                # Regenerate with feedback and try again.
                improved = await generate_episode_script(
                    transcript=brief.transcript,
                    description=brief.description,
                    duration=brief.duration,
                    title=brief.title,
                    video_id=clip_id,
                    voiceover=brief.voiceover,
                    source_frames=brief.source_frames or None,
                    feedback=last_feedback,
                    manin_prompt=brief.manim_prompt,
                    orientation=brief.orientation,
                )
                new_result = await self._render_scene_subprocess(
                    clip_id, improved, brief.quality, portrait, brief.voice_id,
                    log_sink=log_sink,
                )
                code, result = improved, new_result
                save_script(clip_id, improved)
                logger.info("eval iter %d: re-render succeeded", it + 1)
            except Exception as e:
                logger.warning("eval iter %d aborted: %s", it + 1, e)
                # Keep the last successful version.
                break

        return result, code, last_score, last_feedback


# ─── sync helpers (run from `asyncio.to_thread`) ────────────────────────────────


def _render_scene_sync(
    clip_id: str,
    scene_code: str,
    quality: str,
    portrait: bool,
    voice_id: str,
    log_sink: object | None = None,
) -> dict:
    """Write scene.py and run `manim`. Sync — caller wraps in asyncio.to_thread.

    When `log_sink` is provided (a LogSink), the subprocess's stdout +
    stderr stream live into execution_log scoped to its scene_render row.
    When None (legacy callers / playground), output is captured in bulk.
    """
    import time as _time
    import threading as _threading

    job_dir = STORAGE_DIR / "renders" / clip_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Inject orientation-aware Manim config at the top of scene.py.
    #
    # `config.frame_size = [1080, 1920]` alone is NOT enough — it changes the
    # pixel canvas but the LOGICAL coordinate system keeps its default
    # frame_width=14.222 / frame_height=8 (landscape). Content built around
    # `move_to(ORIGIN)` then renders into a 16:9 strip floating in the
    # vertical center of the tall canvas, with black bands top + bottom.
    # The manim-shorts repo gets away with it because its helpers read
    # config.frame_width and reflow; our scenes use the landscape constants.
    #
    # Fix: also set frame_width/frame_height so the logical coord system is
    # genuinely portrait (9 wide × 16 tall). Now `.to_edge(UP)` goes to y=8
    # (actual top of frame), `.to_edge(DOWN)` to y=-8, and content using
    # `move_to(ORIGIN)` sits dead center of the 9:16 canvas.
    #
    # NB: existing system-prompt rules were tuned for landscape coords
    # (.shift(UP*1.5) lands at upper-third). On 16-tall they land closer to
    # the middle. Acceptable for v1; full portrait-aware prompt comes later.
    #
    # Pixel dims are env-configurable for low-RAM dev containers:
    # PORTRAIT_PIXEL_WIDTH / PORTRAIT_PIXEL_HEIGHT default to 1080×1920
    # (production-grade); set 540×960 on Railway worker if the container
    # has <1 GB RAM and ffmpeg is getting OOM-killed (BrokenPipeError
    # in the streamed stderr). Logical 9×16 stays the same so scene
    # composition is identical — only the output raster shrinks.
    import os as _os
    _pw = _os.environ.get("PORTRAIT_PIXEL_WIDTH", "1080")
    _ph = _os.environ.get("PORTRAIT_PIXEL_HEIGHT", "1920")
    portrait_config = (
        "from manim import config\n"
        f"config.pixel_width = {int(_pw)}\n"
        f"config.pixel_height = {int(_ph)}\n"
        "config.frame_width = 9\n"
        "config.frame_height = 16\n"
        "\n"
    )
    final_code = (portrait_config + scene_code) if portrait else scene_code

    scene_file = job_dir / "scene.py"
    scene_file.write_text(final_code)

    scene_class = _detect_scene_class(scene_code)
    orientation = "portrait" if portrait else "landscape"
    media_dir = job_dir / "media" / orientation

    # No --resolution flag: the in-script config block above is authoritative
    # for portrait, and landscape uses manim's defaults (1920x1080 at -ql/qm/qh
    # via quality presets).
    cmd = [
        "manim",
        f"-{quality}",
        str(scene_file),
        scene_class,
        "--media_dir", str(media_dir),
    ]
    line_count = scene_code.count("\n") + 1
    pixel_info = "1080x1920 (config.frame_size)" if portrait else "via -%s quality" % quality
    logger.info(
        "manim subprocess starting: clip=%s class=%s quality=%s orient=%s res=%s lines=%d",
        clip_id, scene_class, quality, orientation, pixel_info, line_count,
    )
    logger.info(
        "scene_code signals: MathTex=%s Axes(=%s ValueTracker=%s voiceover=%s",
        "MathTex" in scene_code, "Axes(" in scene_code,
        "ValueTracker" in scene_code, "voiceover" in scene_code,
    )
    logger.info("scene_file: %s", scene_file)
    logger.info("media_dir: %s", media_dir)
    logger.info("manim cmd: %s", " ".join(cmd))

    t0 = _time.time()
    if log_sink is None:
        # Legacy path — bulk capture. Kept for playground + any caller
        # that doesn't care about live streaming.
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,
            cwd=str(STORAGE_DIR.parent),
            env=_build_env(voice_id=voice_id),
        )
        took = _time.time() - t0
        stdout_text = result.stdout or ""
        stderr_text = result.stderr or ""
        returncode = result.returncode
    else:
        # Streaming path — Popen + two reader threads that forward each
        # line into the LogSink (which batches + INSERTs into
        # execution_log every ~500ms). Local copies still accumulate
        # so `_classify_error` + the final error log keep working.
        #
        # `stdbuf -oL -eL` forces the *subprocess* itself to line-buffer
        # its stdout + stderr. Without it, Python (Manim) detects its
        # stdout is a pipe (not a tty) and switches to block-buffering,
        # so individual lines don't reach the parent until the buffer
        # fills (4 KB+) or the subprocess exits. `bufsize=1` on Popen
        # only controls the parent-side buffering; it doesn't reach
        # into the child. Wrapping in stdbuf is the standard fix.
        # stdbuf is from coreutils — present on every debian-slim image.
        streaming_cmd = ["stdbuf", "-oL", "-eL", *cmd]
        proc = subprocess.Popen(
            streaming_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # parent-side line buffering
            cwd=str(STORAGE_DIR.parent),
            env=_build_env(voice_id=voice_id),
        )

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        def _drain(stream, sink_level: str, dest: list[str]) -> None:
            for raw in iter(stream.readline, ""):
                line = raw.rstrip("\n")
                dest.append(line)
                try:
                    log_sink.write(sink_level, line)
                except Exception:  # noqa: BLE001
                    # Sink failures are non-fatal — the render must keep going.
                    pass
            try:
                stream.close()
            except Exception:  # noqa: BLE001
                pass

        # `log_level_enum` only accepts DEBUG/INFO/WARN/ERROR. Map
        # stream-of-origin to a level: stdout=INFO (general progress),
        # stderr=ERROR (Manim writes errors + warnings + progress bars
        # to stderr — we lose level granularity but at least the rows
        # land. The FE can still distinguish source by inspecting the
        # message itself).
        t_out = _threading.Thread(target=_drain, args=(proc.stdout, "INFO", stdout_lines))
        t_err = _threading.Thread(target=_drain, args=(proc.stderr, "ERROR", stderr_lines))
        t_out.start(); t_err.start()
        try:
            returncode = proc.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            proc.kill()
            t_out.join(timeout=5); t_err.join(timeout=5)
            raise
        t_out.join(); t_err.join()
        took = _time.time() - t0
        stdout_text = "\n".join(stdout_lines)
        stderr_text = "\n".join(stderr_lines)

    logger.info(
        "manim subprocess done: returncode=%d took=%.1fs stdout_chars=%d stderr_chars=%d",
        returncode, took, len(stdout_text), len(stderr_text),
    )

    if returncode != 0:
        msg = _classify_error(stderr_text)
        logger.error(
            "manim FAILED: returncode=%d class=%s\n--- stderr (last 3000) ---\n%s",
            returncode, scene_class, stderr_text[-3000:],
        )
        raise RuntimeError(msg)

    video_file = _find_rendered_video(media_dir)
    if not video_file:
        # Manim exited with returncode 0 but produced no .mp4 — usually
        # means the FFmpeg encoder died mid-stream (OOM, disk-full, or
        # explicit kill) and Manim swallowed the BrokenPipeError without
        # marking the run as failed. Treat as a failure so the
        # render_clip fallback chain moves on to attempt 2 instead of
        # crashing on `Path(None)` further up.
        msg = (
            "Manim exited rc=0 but produced no .mp4 — likely FFmpeg "
            "subprocess was killed (OOM?). Last stderr 800 chars: "
            f"{stderr_text[-800:]}"
        )
        logger.error("manim: no-video failure: %s", msg[:300])
        raise RuntimeError(msg)
    logger.info("manim produced: %s (%d bytes)", video_file, video_file.stat().st_size)
    return {
        "scene_file": str(scene_file),
        "video_file": str(video_file),
        "media_dir": str(media_dir),
        # `stderr_text` is unified across both the legacy bulk-capture
        # and the streaming Popen paths — the latter joins line-by-line
        # captures into the same string shape callers used to read off
        # subprocess.CompletedProcess.stderr.
        "stderr": stderr_text,
    }


def _detect_scene_class(scene_code: str) -> str:
    """Pull the Scene subclass name out of the generated code."""
    match = re.search(
        r"class\s+(\w+)\s*\(\s*(?:OctoflashScene|OctoflashSceneNoVoice|Scene|VoiceoverScene|Octoflash3DScene)",
        scene_code,
    )
    return match.group(1) if match else "InspiredVideoScene"


def _find_rendered_video(media_dir: Path) -> Path | None:
    """Find the output .mp4 in manim's media/ tree (skip partial_movie_files)."""
    videos_dir = media_dir / "videos"
    if not videos_dir.exists():
        return None
    for mp4 in sorted(videos_dir.rglob("*.mp4")):
        if "partial_movie_files" not in str(mp4):
            return mp4
    return None


def _extract_video_frames(video_path: Path, count: int = 8) -> list[Path]:
    """Extract `count` evenly-spaced frames for vision eval."""
    output_dir = video_path.parent / "eval_frames"
    output_dir.mkdir(exist_ok=True)

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True,
    )
    try:
        vid_duration = float(probe.stdout.strip())
    except ValueError:
        vid_duration = 30.0
    interval = max(1, vid_duration / count)

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path),
         "-vf", f"fps=1/{interval:.2f}",
         "-frames:v", str(count),
         str(output_dir / "eval_%04d.jpg")],
        capture_output=True, text=True,
        timeout=120,
    )
    return sorted(output_dir.glob("eval_*.jpg"))


def _extract_output_frames(video_path: Path, output_dir: Path, count: int = 12) -> list[Path]:
    """Extract frames for the UI preview grid."""
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True,
    )
    try:
        vid_duration = float(probe.stdout.strip())
    except ValueError:
        vid_duration = 30.0
    interval = max(0.5, vid_duration / count)

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path),
         "-vf", f"fps=1/{interval:.2f}",
         "-frames:v", str(count),
         "-q:v", "2",
         str(output_dir / "frame_%04d.jpg")],
        capture_output=True, text=True,
        timeout=60,
    )
    return sorted(output_dir.glob("frame_*.jpg"))


def _build_env(voice_id: str = "") -> dict:
    """Env vars for the `manim` subprocess.

    Inherits the current process env (which pydantic-settings has already
    populated from .env.dev.local / .env.dev.dev), then adds:
      - PYTHONPATH so `from app.manim_pipeline.styles import ...` resolves
      - OCTOFLASH_VOICE_ID so styles.get_speech_service() picks the right voice
    """
    import os

    env = os.environ.copy()
    # Ensure Anthropic + ElevenLabs keys are present (the script and voice gen
    # both run inside this subprocess via manim-voiceover).
    if settings.anthropic_api_key and "ANTHROPIC_API_KEY" not in env:
        env["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    if settings.eleven_api_key and "ELEVEN_API_KEY" not in env:
        env["ELEVEN_API_KEY"] = settings.eleven_api_key

    # Project root = the directory containing the `app/` package. Derive
    # it from this file's location rather than STORAGE_DIR.parent, which
    # is misleading on Railway (storage is at /storage, so .parent is /,
    # but our code lives at /app/app/ — PYTHONPATH=/ wouldn't help).
    # __file__ = .../app/service/manim_render_service.py; parents[2] is
    # the dir holding `app/`.
    project_root = str(Path(__file__).resolve().parents[2])
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}:{existing}" if existing else project_root

    # Force unbuffered output from Manim (a Python program) so our
    # streaming LogSink + Popen reader threads see lines as they're
    # printed instead of waiting for a flush. Dockerfile already sets
    # this for the worker process; setting it again on the subprocess
    # env is belt-and-suspenders against an env not being inherited.
    env["PYTHONUNBUFFERED"] = "1"

    if voice_id:
        env["OCTOFLASH_VOICE_ID"] = voice_id
    return env


# ─── error classification (verbatim from MVP) ──────────────────────────────────


def _classify_error(stderr: str) -> str:
    """Categorize manim subprocess errors for actionable diagnostics."""
    s = stderr.lower()

    if "modulenotfounderror" in s or "importerror" in s:
        return f"Import error — missing dependency:\n{stderr.strip()}"
    if "elevenlabs" in s or "api_key" in s or "voiceover" in s:
        return f"Voiceover/ElevenLabs error:\n{stderr.strip()}"
    if "syntaxerror" in s:
        return f"Syntax error in generated scene:\n{stderr.strip()}"
    if "timeout" in s:
        return f"Render timed out:\n{stderr.strip()}"
    if "cannot create a mobject from an empty string" in s:
        return f"Empty string mobject error (Text/Tex/MathTex given empty string):\n{stderr.strip()}"
    if "latex error converting" in s or "pdflatex error" in s:
        return f"LaTeX compilation error (invalid TeX in MathTex/Tex):\n{stderr.strip()}"
    if "no tex installation" in s or "no such file or directory: 'latex'" in s:
        return f"LaTeX not installed:\n{stderr.strip()}"
    if "only works for vmobjects" in s or "only works for vectorized" in s:
        return f"Animation type error (Create/Write used on non-VMobject):\n{stderr.strip()}"
    if "truth value of an array" in s:
        return f"Numpy array truth value error (use np.maximum/np.minimum instead of max/min):\n{stderr.strip()}"
    if "called scene.play with no animations" in s:
        return f"Empty play() call:\n{stderr.strip()}"
    if "animation only works on mobjects" in s:
        return f"Non-Mobject passed to animation:\n{stderr.strip()}"
    if "run_time" in s and "cannot be negative" in s:
        return f"Negative run_time error (guard with 'if remaining > 0'):\n{stderr.strip()}"
    if "nameerror" in s:
        return f"NameError (likely missing imports):\n{stderr.strip()}"
    if "attributeerror" in s:
        return f"Attribute error (possibly wrong API — check manimlib vs CE):\n{stderr.strip()}"
    if "typeerror" in s:
        return f"Type error in generated scene:\n{stderr.strip()}"
    if "valueerror" in s:
        return f"Value error in generated scene:\n{stderr.strip()}"
    if "memoryerror" in s or "killed" in s:
        return f"Memory/resource error (scene too complex):\n{stderr.strip()}"

    return f"Manim render failed:\n{stderr.strip()}"
