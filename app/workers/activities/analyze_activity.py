"""
Analyze activity — source URL → transcript + frames + description + manim brief.

Single activity (vs. one per substep) because they're all sequentially
dependent on the same downloaded file and there's no useful retry boundary
between them. If Whisper falls back, that's transparent here.

Heavy: downloads up to ~50MB video, runs ffmpeg, may run Whisper (CPU minutes).
Set generous activity timeouts in the workflow.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from temporalio import activity

import app.model  # noqa: F401
from app.service.describer_service import DescriberService
from app.service.frame_extractor_service import extract_frames
from app.service.prompt_builder_service import PromptBuilderService
from app.service.source_fetcher_service import SourceType, classify_source_url
from app.service.transcript_service import TranscriptService
from app.settings import settings


@dataclass
class AnalyzeSourceInput:
    project_id: str
    source_url: str
    # Owner — used to look up per-user YouTube cookies (stored via the
    # browser extension as credential `youtube_cookies`) and feed them to
    # yt-dlp. Without cookies, YouTube IP-blocks data-center scrapers.
    user_id: str | None = None


@dataclass
class AnalyzeSourceOutput:
    source_type: str
    source_duration: float
    transcript: str
    transcript_source: str  # "captions" | "whisper"
    description: str
    manim_prompt: str
    frames_dir: str
    frame_count: int
    title_hint: str  # first non-empty line of description, capped at 80 chars
    extra: dict[str, str] = field(default_factory=dict)


def _user_youtube_cookies_file(user_id: str | None, target_dir: Path) -> Path | None:
    """Write the caller's stored YouTube cookies to a temp file and return
    its path, or None if the user has no cookies on file.

    The browser extension uploads cookies via `PUT /credentials/youtube_cookies`
    — the credential vault encrypts at rest via Fernet. Here we open a
    short-lived sync psycopg connection, decrypt, and write a 0600
    cookies.txt that yt-dlp can consume with `--cookies`.

    Sync — called from inside `asyncio.to_thread(_download_video, ...)`.
    """
    if not user_id:
        return None
    try:
        import psycopg

        from app.common.security.secret_crypto import decrypt
    except Exception:
        activity.logger.warning("psycopg / secret_crypto import failed; skipping cookies")
        return None

    dsn = settings.sync_database_url.replace("postgresql+psycopg://", "postgresql://")
    try:
        with psycopg.connect(dsn, connect_timeout=10) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT value FROM credential "
                "WHERE user_id = %s AND name = %s AND is_deleted = false",
                (user_id, "youtube_cookies"),
            )
            row = cur.fetchone()
    except Exception as exc:  # noqa: BLE001
        activity.logger.warning("cookies lookup failed for user=%s: %s", user_id, exc)
        return None
    if not row or not row[0]:
        return None

    try:
        cookies_text = decrypt(row[0])
    except Exception as exc:  # noqa: BLE001
        activity.logger.warning("cookies decrypt failed for user=%s: %s", user_id, exc)
        return None
    if not cookies_text.strip():
        return None

    cookies_path = target_dir / "yt_cookies.txt"
    cookies_path.write_text(cookies_text)
    try:
        cookies_path.chmod(0o600)
    except OSError:
        pass
    activity.logger.info("yt-dlp cookies loaded for user=%s (%d bytes)", user_id, len(cookies_text))
    return cookies_path


def _bgutil_server_home() -> str:
    return os.environ.get("BGUTIL_POT_PROVIDER_SERVER_HOME") or "/opt/bgutil-pot-provider/server"


def _warn_if_bgutil_unavailable() -> None:
    server_home = Path(_bgutil_server_home())
    script = server_home / "build" / "generate_once.js"
    if not script.exists():
        activity.logger.warning(
            "bgutil PO-token script not found at %s. YouTube may return bot checks/403s. "
            "Build the provider server or set BGUTIL_POT_PROVIDER_SERVER_HOME.",
            script,
        )


def _download_video(url: str, project_id: str, user_id: str | None = None) -> Path:
    """yt-dlp the source video into storage/projects/<project_id>/source.<ext>.

    YouTube aggressively blocks data-center IPs (Railway, Render, etc.)
    as scrapers, so the `web` extractor frequently 403s. The `android`
    + `ios` player clients use a different cert path that's been more
    reliable in practice.

    If the project owner has uploaded YouTube cookies via the browser
    extension (stored as credential `youtube_cookies`), feed them to
    yt-dlp via `--cookies` — that's the real fix for the IP block;
    requests go out with a real signed-in session.

    Captures stderr explicitly so any yt-dlp failure surfaces as a real
    error message (the previous `--quiet` swallowed everything,
    making Temporal show only `returned non-zero exit status 1`).
    """
    storage_root = Path(settings.local_storage_path or "storage").resolve()
    target_dir = storage_root / "projects" / project_id
    target_dir.mkdir(parents=True, exist_ok=True)

    cookies_path = _user_youtube_cookies_file(user_id, target_dir)
    _warn_if_bgutil_unavailable()

    outtmpl = str(target_dir / "source.%(ext)s")
    max_height = max(144, int(settings.youtube_analysis_max_height or 360))
    concurrent_fragments = max(1, int(settings.youtube_download_concurrent_fragments or 1))
    cmd = [
        "yt-dlp",
        "--no-playlist",
        # Verbose so the bgutil plugin's discovery/POT-generation log
        # lines actually surface. `--no-warnings` swallows them. The
        # full extractor debug output is noisy but cheap (one analyze
        # per project) and load-bearing for diagnosing the 2025 PO
        # Token gating.
        "-v",
        "--geo-bypass",
        "--concurrent-fragments",
        str(concurrent_fragments),
        # PO Token provider — YouTube rolled out the "proof-of-origin"
        # token requirement in 2025 and now gates every non-storyboard
        # format behind it. Without a PO Token, even valid cookies get
        # back only audio-only tracks. The bgutil plugin generates the
        # token via a Node script bundled in the Docker image (see
        # Dockerfile). On dev machines without the script, the plugin
        # is silently absent and yt-dlp falls back to its default
        # (which only works for some videos).
        "--extractor-args",
        "youtubepot-bgutilscript:server_home=" + _bgutil_server_home(),
        # Player-client selection:
        #   * With cookies → `web,mweb,default`. These honor cookie-based
        #     auth. yt-dlp 2025.x's tv_simply default expects a smart-TV
        #     linked-account login that browser cookies don't satisfy
        #     and surfaces the "Sign in to confirm you're not a bot"
        #     challenge.
        #   * Without cookies → `android,ios,web,tv,mweb`. Legacy
        #     ladder; less reliable, but better than nothing.
        "--extractor-args",
        (
            "youtube:player_client=web,mweb,default"
            if cookies_path
            else "youtube:player_client=android,ios,web,tv,mweb"
        ),
        # Format ladder — first match wins:
        #   1. mp4-only <= configured analysis height (cheap, no ffmpeg merge)
        #   2. any <= configured analysis height (mp4 / webm / mkv is fine)
        #   3. bestvideo + bestaudio merge (Shorts often only ship DASH /
        #      separate streams; this catches them)
        #   4. `best` / `worst` as last-ditch fallbacks so we don't 404
        #      on weird format manifests
        "-f",
        (
            f"best[ext=mp4][height<={max_height}]/"
            f"best[height<={max_height}]/"
            f"worst[height<={max_height}]/"
            "worst"
        ),
        "-o", outtmpl,
        url,
    ]
    if cookies_path:
        cmd[1:1] = ["--cookies", str(cookies_path)]
    activity.logger.info("yt-dlp: %s", " ".join(cmd))
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=300, check=False,
    )
    if proc.returncode != 0:
        stderr_full = proc.stderr or ""
        # Plugin discovery (bgutil) + extractor handler selection happen
        # at the START of stderr; the actual error message is at the END.
        # Log both halves so we can diagnose whether bgutil even ran.
        stderr_head = stderr_full[:4000]
        stderr_tail = stderr_full[-2000:]
        activity.logger.error(
            "yt-dlp FAILED (rc=%d) for url=%s\n--- stderr head ---\n%s\n--- stderr tail ---\n%s",
            proc.returncode, url, stderr_head, stderr_tail,
        )
        raise RuntimeError(
            f"yt-dlp failed (rc={proc.returncode}). Last stderr: {stderr_tail[-400:]}"
        )

    found = next(target_dir.glob("source.*"), None)
    if not found:
        raise FileNotFoundError(f"yt-dlp ran but no source.* in {target_dir}")
    return found


def _title_hint(description: str) -> str:
    """First non-empty content line of the description (skip the markdown header)."""
    for line in description.splitlines():
        stripped = line.strip(" #\t").strip()
        if stripped and not stripped.lower().startswith("visual analysis"):
            return stripped[:80]
    return ""


@activity.defn(name="analyze_source")
async def analyze_source_activity(payload: AnalyzeSourceInput) -> AnalyzeSourceOutput:
    """Full analyze pipeline. Sync subprocess work wrapped in asyncio.to_thread.

    Heartbeats between substeps so Temporal sees us alive even on slow
    Whisper fallback runs.
    """
    activity.logger.info(
        "analyze_source: project=%s url=%s", payload.project_id, payload.source_url,
    )

    source_type = classify_source_url(payload.source_url)

    # For now, only YouTube is implemented in the activity. Articles use the sync path
    # in ProjectService.create_from_source. Add Medium/Substack here when the workflow
    # is ready to dispatch articles through Temporal too.
    if source_type not in (SourceType.YOUTUBE_LONG, SourceType.YOUTUBE_SHORT):
        raise NotImplementedError(
            f"analyze_source activity currently handles YouTube only; got {source_type.value}"
        )

    # 1. Download
    video_path = await asyncio.to_thread(
        _download_video, payload.source_url, payload.project_id, payload.user_id,
    )
    activity.heartbeat("downloaded")

    # 2. Sparse, evenly-sampled frames. The vision describer samples only 6
    # frames, so extracting thousands of 1-fps frames just creates avoidable
    # ffmpeg, disk, and upload pressure for long source videos.
    extracted = await asyncio.to_thread(
        extract_frames,
        payload.project_id,
        video_path,
        1.0,
        2,
        settings.youtube_analysis_frame_count,
    )
    activity.heartbeat("frames_extracted")
    activity.logger.info(
        "frames=%d duration=%.1fs", len(extracted.frame_paths), extracted.duration_seconds or 0.0,
    )

    # 3. Transcript. Reuse the same cookies/PO-token path as the video
    # download; subtitle and audio endpoints are protected by the same
    # YouTube bot checks.
    cookies_path = video_path.parent / "yt_cookies.txt"
    transcript = await asyncio.to_thread(
        TranscriptService().fetch,
        payload.source_url,
        cookies_path if cookies_path.exists() else None,
    )
    activity.heartbeat("transcript_fetched")

    # 4. Describer (Claude vision)
    storage_root = Path(settings.local_storage_path or "storage").resolve()
    rel_frames = [str(p.relative_to(storage_root)) for p in extracted.frame_paths]
    description = await DescriberService().describe(
        rel_frames, transcript.text, extracted.duration_seconds or 0.0,
    )
    activity.heartbeat("described")

    # 5. Prompt builder (pure)
    manim_prompt = PromptBuilderService().build(
        transcript=transcript.text,
        frame_paths=extracted.frame_paths,
        description=description,
        duration=extracted.duration_seconds or 0.0,
    )

    return AnalyzeSourceOutput(
        source_type=source_type.value,
        source_duration=extracted.duration_seconds or 0.0,
        transcript=transcript.text,
        transcript_source=transcript.source,
        description=description,
        manim_prompt=manim_prompt,
        frames_dir=str(extracted.frames_dir),
        frame_count=len(extracted.frame_paths),
        title_hint=_title_hint(description),
        extra={"language": transcript.language or ""},
    )
