"""
End-to-end smoke test: source URL → transcript → frames → description →
manim brief → Claude script → Manim render → MP4.

Bypasses the (still-pending) Temporal workflow rewire — runs the same service
calls a future activity would make, in order, so we can see exactly where
things hold up. Usage:

    poetry run python scripts/smoke_pipeline.py <url> [--voice]

Defaults to voiceover=False to keep the render fast and avoid ElevenLabs
dependency on the first pass. Pass --voice to flip it on.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import subprocess
import sys
import time
from pathlib import Path

# Make `app.*` importable when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.service.describer_service import DescriberService
from app.service.frame_extractor_service import extract_frames
from app.service.manim_render_service import ClipBrief, ManimRenderService
from app.service.prompt_builder_service import PromptBuilderService
from app.service.script_generator_service import (
    generate_episode_script,
    sanitize_script,
    save_script,
)
from app.service.source_fetcher_service import classify_source_url
from app.service.transcript_service import TranscriptService
from app.settings import settings

# Verbose logging across every relevant module — the smoke run is for diagnosis.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
for name in (
    "app.service.script_generator_service",
    "app.service.manim_render_service",
    "app.service.describer_service",
    "app.service.evaluator_service",
    "app.service.frame_extractor_service",
    "app.service.transcript_service",
    "app.service.source_fetcher_service",
    "anthropic",
    "httpx",
):
    logging.getLogger(name).setLevel(logging.INFO)

log = logging.getLogger("smoke")


_phase_t0 = time.time()


def step(name: str) -> None:
    global _phase_t0
    elapsed = time.time() - _phase_t0
    if elapsed > 0.01:
        log.info("  → previous phase took %.1fs", elapsed)
    print(f"\n{'━' * 70}\n  {name}\n{'━' * 70}")
    _phase_t0 = time.time()


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n //= 1024
    return f"{n} TB"


def _download_video(url: str, project_id: str) -> Path:
    """yt-dlp the source video into storage/<project_id>/source.<ext>."""
    storage_root = Path(settings.local_storage_path or "storage").resolve()
    target_dir = storage_root / "projects" / project_id
    target_dir.mkdir(parents=True, exist_ok=True)

    outtmpl = str(target_dir / "source.%(ext)s")
    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "--no-playlist",
        "-f", "best[height<=720]/best",
        "-o", outtmpl,
        url,
    ]
    log.info("yt-dlp cmd: %s", " ".join(cmd))
    t0 = time.time()
    subprocess.run(cmd, check=True, timeout=180)
    log.info("yt-dlp finished in %.1fs", time.time() - t0)

    found = next(target_dir.glob("source.*"), None)
    if not found:
        raise FileNotFoundError(f"yt-dlp ran but no source.* file in {target_dir}")
    return found


async def main(url: str, voiceover: bool) -> int:
    t_start = time.time()
    project_id = f"smoke_{int(t_start)}"
    log.info("project_id=%s  voiceover=%s  storage_root=%s",
             project_id, voiceover, settings.local_storage_path)

    step(f"Phase 0 — Classify {url!r}")
    source_type = classify_source_url(url)
    log.info("classified as: %s", source_type.value)

    step("Phase 1 — Download source video (yt-dlp)")
    video_path = await asyncio.to_thread(_download_video, url, project_id)
    size = video_path.stat().st_size
    log.info("video saved: %s  size=%s", video_path, _human_size(size))

    step("Phase 2 — Extract frames @ 1 fps (ffmpeg)")
    extracted = await asyncio.to_thread(extract_frames, project_id, video_path, 1.0, 2)
    log.info("frames_dir: %s", extracted.frames_dir)
    log.info("frame_count: %d  duration: %.1fs",
             len(extracted.frame_paths), extracted.duration_seconds or 0.0)
    log.info("frame head/tail: %s ... %s",
             extracted.frame_paths[0].name if extracted.frame_paths else "(none)",
             extracted.frame_paths[-1].name if extracted.frame_paths else "(none)")

    step("Phase 3 — Transcript (yt-dlp captions → Whisper fallback)")
    transcript = await asyncio.to_thread(TranscriptService().fetch, url)
    log.info("source=%s  language=%s  chars=%d",
             transcript.source, transcript.language, len(transcript.text))
    log.info("transcript head: %r", transcript.text[:240])
    if len(transcript.text) > 240:
        log.info("transcript tail: %r", transcript.text[-160:])

    step("Phase 4 — Claude vision describer (frames + transcript → visual style)")
    # describer expects paths relative to STORAGE_DIR
    storage_root = Path(settings.local_storage_path or "storage").resolve()
    rel_frames = [str(p.relative_to(storage_root)) for p in extracted.frame_paths]
    log.info("sending %d frame paths to describer (Claude vision will sample 8)", len(rel_frames))
    t0 = time.time()
    description = await DescriberService().describe(
        rel_frames, transcript.text, extracted.duration_seconds or 0.0,
    )
    log.info("describer returned in %.1fs", time.time() - t0)
    log.info("description chars: %d", len(description))
    log.info("description preview:\n%s", description[:600])

    step("Phase 5 — prompt_builder → manim brief")
    manim_prompt = PromptBuilderService().build(
        transcript=transcript.text,
        frame_paths=extracted.frame_paths,
        description=description,
        duration=extracted.duration_seconds or 0.0,
    )
    log.info("manim_prompt chars: %d", len(manim_prompt))
    log.info("manim_prompt head:\n%s", manim_prompt[:500])

    step("Phase 6 — Generate Manim script (Claude streaming, prompt-cached system)")
    log.info("model=%s  voiceover=%s  source_frames=6 (sampled)",
             settings.script_model, voiceover)
    t0 = time.time()
    script = await generate_episode_script(
        transcript=transcript.text,
        description=description,
        duration=extracted.duration_seconds or 30.0,
        title=f"Smoke {project_id}",
        video_id=project_id,
        voiceover=voiceover,
        source_frames=extracted.frame_paths[:6],
        manin_prompt=manim_prompt,
        orientation="portrait",
    )
    log.info("generate_episode_script returned in %.1fs", time.time() - t0)
    script = sanitize_script(script)
    script_path = save_script(project_id, script)
    log.info("script chars: %d  saved to: %s", len(script), script_path)
    log.info("script head:\n%s", script[:600])
    log.info("script tail:\n%s", script[-400:])

    step("Phase 7 — Manim render (4-attempt fallback + eval loop)")
    brief = ClipBrief(
        clip_id=project_id,
        transcript=transcript.text,
        description=description,
        duration=extracted.duration_seconds or 30.0,
        title=f"Smoke {project_id}",
        orientation="portrait",
        quality="ql",  # low quality for speed during smoke
        voiceover=voiceover,
        voice_id="",
        source_frames=extracted.frame_paths[:6],
        manim_prompt=manim_prompt,
    )
    log.info("ClipBrief: clip_id=%s orient=%s quality=%s voiceover=%s frames=%d",
             brief.clip_id, brief.orientation, brief.quality, brief.voiceover,
             len(brief.source_frames))
    log.info("passing prebuilt script from Phase 6 (%d chars) — render_clip will skip its own step1", len(script))
    log.warning("manim render starts now — expect 2-15 min depending on scene complexity")
    t0 = time.time()
    result = await ManimRenderService().render_clip(brief, prebuilt_script=script)
    log.info("render_clip returned in %.1fs", time.time() - t0)

    step("Result")
    log.info("render_method:  %s", result.render_method.value)
    log.info("scene_file:     %s", result.scene_file)
    log.info("video_file:     %s  size=%s",
             result.video_file, _human_size(result.video_file.stat().st_size))
    log.info("script_chars:   %d", len(result.script_code))
    log.info("eval_score:     %s", result.eval_score)
    if result.eval_feedback:
        log.info("eval_feedback:  %s", result.eval_feedback[:400])
    log.info("output_frames:  %s", result.output_frames_dir)
    log.info("TOTAL TIME: %.1fs", time.time() - t_start)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="YouTube / Medium / Substack URL")
    parser.add_argument("--voice", action="store_true", help="Enable voiceover (slow, needs ELEVEN_API_KEY)")
    args = parser.parse_args()

    sys.exit(asyncio.run(main(args.url, voiceover=args.voice)))
