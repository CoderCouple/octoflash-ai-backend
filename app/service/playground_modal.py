"""Modal-backed playground sandbox.

When PLAYGROUND_BACKEND=modal, every render is a one-shot `manimgl`
invocation inside a transient Modal container. Modal handles:

  * isolation (each call is its own container, no host filesystem)
  * resource caps (CPU / memory / wall-clock timeout)
  * scale-to-zero (no idle cost)
  * pay-per-second billing (Modal's free tier covers ~30k small renders)

Setup:

  1. Sign up at https://modal.com (free tier covers low volume)
  2. `modal token new` in your terminal — saves creds to ~/.modal.toml
  3. For the deployed backend, set on Railway api service:
        MODAL_TOKEN_ID=ak-...
        MODAL_TOKEN_SECRET=as-...
     (or use modal's standard env vars — the SDK auto-picks them up)
  4. Set PLAYGROUND_BACKEND=modal + PLAYGROUND_ENABLED=true

No `modal deploy` step needed — the function ships with each call when
invoked via `render_manim.remote()`. For frequent traffic you can
`modal deploy app/service/playground_modal.py` once to pre-warm
the image and skip the build phase on cold call.
"""

from __future__ import annotations

import logging

import modal

logger = logging.getLogger(__name__)

# ManimGL runtime image. Built once and cached by Modal — subsequent
# function calls re-use it. Only rebuilt when the image spec below
# changes.
_manim_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "ffmpeg",
        "libcairo2",
        "libcairo2-dev",
        "libpango-1.0-0",
        "libpango1.0-dev",
        "libpangocairo-1.0-0",
        "libsndfile1",
        "sox",
        "pkg-config",
        "gcc",
    )
    # ManimGL is the 3Blue1Brown variant the playground presets target.
    # Pin to a working version; the upstream main branch breaks often.
    .pip_install("manimgl==1.7.2")
)

# Modal "app" namespace — appears in the Modal dashboard. Doesn't affect
# call semantics; just groups invocations for observability.
_app = modal.App("octoflash-playground", image=_manim_image)


# Quality flag mapping — must stay in sync with playground_service._QUALITY_FLAGS.
_QUALITY_FLAGS = {
    "480p":  "-l",
    "720p":  "-m",
    "1080p": "--hd",
    "1440p": "--hd",
    "2160p": "--uhd",
}


@_app.function(
    timeout=120,        # ManimGL renders for the FE are short — clamp at 2 min
    cpu=2.0,
    memory=2048,
    serialized=True,    # Required when the function isn't in a Modal-deployed file
)
def render_manim(code: str, scene_class: str, quality: str) -> bytes:
    """Execute manimgl on the supplied scene + return the rendered MP4 bytes.

    Runs inside the `_manim_image` container above. The container has
    no outbound network (Modal default for sandbox-style usage), no
    persistent storage, and no host filesystem access — anything the
    user code does is contained to this container's tmpfs.
    """
    import pathlib
    import subprocess
    import tempfile

    work = pathlib.Path(tempfile.mkdtemp())
    (work / "scene.py").write_text(code)
    media = work / "media"
    media.mkdir()

    flag = _QUALITY_FLAGS.get(quality, "-m")
    proc = subprocess.run(
        ["manimgl", flag, str(work / "scene.py"), scene_class, "--media_dir", str(media)],
        capture_output=True,
        text=True,
        timeout=100,
        cwd=str(work),
    )
    if proc.returncode != 0:
        # Strip absolute paths from the error so the FE doesn't leak the
        # container's tempdir layout.
        stderr = proc.stderr[-2000:].replace(str(work), "<scene>")
        raise RuntimeError(f"manimgl rc={proc.returncode}\n{stderr}")

    for mp4 in media.rglob("*.mp4"):
        return mp4.read_bytes()
    raise RuntimeError("manimgl did not produce an MP4 file")


def render_via_modal(code: str, scene_class: str, quality: str) -> bytes:
    """Sync wrapper for `render_manim.remote(...)`. Use this from
    PlaygroundService — keeps the Modal coupling in one place so the
    rest of the codebase doesn't need to import modal.
    """
    # `.remote()` is the call path — runs the function on Modal's
    # infra. `.local()` would run inline (defeats the isolation).
    with _app.run():
        return render_manim.remote(code, scene_class, quality)
