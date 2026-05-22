"""PlaygroundService — sandboxed ManimGL renders for the /playground page.

This is the **one** place in the app where user-supplied Python is executed.
Everywhere else, Manim code is Claude-generated. Two execution modes,
selected by `settings.playground_sandbox_mode`:

* ``docker`` (default, production): every render runs inside a transient
  container built from ``infra/playground-runner/Dockerfile``:

    • ``--network=none``                — no outbound network
    • non-root user (uid 1000)          — matches ``runner`` in the image
    • ``--memory`` / ``--cpus``         — RAM + CPU caps
    • ``--pids-limit``                  — fork-bomb defence
    • ``--security-opt=no-new-privileges`` — block setuid escalation
    • only the per-render dir is bind-mounted RW
    • wall-clock timeout from the host (``playground_timeout_seconds``)
    • container is ``--rm``             — disk + memory reclaimed on exit

  If the Docker binary is missing or the daemon is down, the endpoint
  returns 503. Treat the container as the security boundary — the AST
  tripwire below is defence-in-depth only.

* ``local`` (DEV ONLY): invokes ``manimgl`` directly on the host. No
  isolation — submitted code runs as the server user with full network
  access. Useful for laptop iteration. **Never enable in production.**

ManimGL (3Blue1Brown) is what the frontend presets target (``from manimlib
import *``). ManimCommunity has a different API and is not interchangeable.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.settings import settings

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(settings.local_storage_path or "storage").resolve()
PLAYGROUND_DIR = STORAGE_DIR / "playground"

# Frontend label → ManimGL CLI flag list. ManimGL doesn't ship a 1440p
# preset; we route it to --hd (1080p) — closest stable preset without going
# to 4K.
_QUALITY_FLAGS: dict[str, list[str]] = {
    "480p":  ["-l"],
    "720p":  ["-m"],
    "1080p": ["--hd"],
    "1440p": ["--hd"],
    "2160p": ["--uhd"],
}

_FORBIDDEN_NAMES: frozenset[str] = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
        "input",
        "breakpoint",
    }
)
_FORBIDDEN_MODULES: frozenset[str] = frozenset(
    {
        "os",
        "subprocess",
        "shutil",
        "socket",
        "urllib",
        "urllib2",
        "urllib3",
        "requests",
        "http",
        "ftplib",
        "ctypes",
        "multiprocessing",
        "pty",
        "pickle",
        "marshal",
    }
)


class PlaygroundValidationError(ValueError):
    """User-supplied code failed AST validation. Maps to HTTP 400."""


class PlaygroundRenderError(RuntimeError):
    """manimgl exited non-zero, timed out, or produced no MP4."""


class PlaygroundRuntimeUnavailable(RuntimeError):
    """Selected runtime (docker daemon or local manimgl) isn't reachable. Maps to 503."""


@dataclass
class Preset:
    id: str
    label: str
    duration: str
    preview: str
    code: str


# Mirrors the catalog in
# octoflash-ai-frontend/packages/web/src/pages/playground.tsx — update both
# sides together. All snippets target ManimGL (``from manimlib import *``).
PRESETS: list[Preset] = [
    Preset(
        id="hello-manim",
        label="Hello Manim",
        duration="0:08",
        preview="/examples/TrigonometryAnimation_ManimCE_v0.17.3.gif",
        code=(
            "from manimlib import *\n"
            "\n"
            "class HelloManim(Scene):\n"
            "    def construct(self):\n"
            "        circle = Circle(color=BLUE)\n"
            "        square = Square(color=YELLOW)\n"
            "\n"
            "        self.play(ShowCreation(circle))\n"
            "        self.wait(0.5)\n"
            "        self.play(Transform(circle, square))\n"
            "        self.wait(2)\n"
        ),
    ),
    Preset(
        id="unit-circle",
        label="Unit circle · sine",
        duration="0:48",
        preview="/examples/TrigonometryAnimation_ManimCE_v0.17.3.gif",
        code=(
            "from manimlib import *\n"
            "import numpy as np\n"
            "\n"
            "class UnitCircleSine(Scene):\n"
            "    def construct(self):\n"
            "        axes = Axes(\n"
            "            x_range=[-1, 7, 1],\n"
            "            y_range=[-1.5, 1.5, 0.5],\n"
            "            axis_config={\"include_tip\": True},\n"
            "        )\n"
            "        circle = Circle(radius=1, color=BLUE).shift(LEFT * 3)\n"
            "        dot = Dot(color=YELLOW)\n"
            "        theta = ValueTracker(0)\n"
            "\n"
            "        def get_dot():\n"
            "            t = theta.get_value()\n"
            "            return Dot(np.array([np.cos(t) - 3, np.sin(t), 0]), color=YELLOW)\n"
            "\n"
            "        dot.add_updater(lambda m: m.become(get_dot()))\n"
            "        self.play(ShowCreation(axes), ShowCreation(circle))\n"
            "        self.add(dot)\n"
            "        self.play(theta.animate.set_value(TAU), run_time=6, rate_func=linear)\n"
            "        self.wait()\n"
        ),
    ),
    Preset(
        id="complex-rotation",
        label="Complex rotation",
        duration="0:36",
        preview="/examples/ComplexNumbersAnimation_ManimCE_v0.17.3.gif",
        code=(
            "from manimlib import *\n"
            "\n"
            "class ComplexRotation(Scene):\n"
            "    def construct(self):\n"
            "        plane = ComplexPlane().add_coordinate_labels()\n"
            "        z = Dot(plane.n2p(2 + 1j), color=YELLOW)\n"
            "        label = Tex(\"z = 2 + i\").to_corner(UL)\n"
            "\n"
            "        self.play(ShowCreation(plane), Write(label))\n"
            "        self.play(FadeIn(z, scale=2))\n"
            "\n"
            "        for k in range(1, 5):\n"
            "            target = plane.n2p((2 + 1j) * (1j ** k))\n"
            "            self.play(z.animate.move_to(target), run_time=1.2)\n"
            "            self.wait(0.3)\n"
        ),
    ),
    Preset(
        id="surface-3d",
        label="3D parametric surface",
        duration="0:48",
        preview="/examples/3d_calculus.gif",
        code=(
            "from manimlib import *\n"
            "import numpy as np\n"
            "\n"
            "class Paraboloid(ThreeDScene):\n"
            "    def construct(self):\n"
            "        axes = ThreeDAxes()\n"
            "        surface = ParametricSurface(\n"
            "            lambda u, v: np.array([u, v, 0.4 * (u**2 + v**2)]),\n"
            "            u_range=[-2, 2], v_range=[-2, 2],\n"
            "            color=BLUE_D,\n"
            "        )\n"
            "        # ManimGL camera is `self.frame`; ManimCommunity's\n"
            "        # set_camera_orientation / begin_ambient_camera_rotation\n"
            "        # don't exist here. Tilt up via Euler angles, then spin\n"
            "        # via an updater on the frame.\n"
            "        self.frame.set_euler_angles(theta=30 * DEGREES, phi=70 * DEGREES)\n"
            "        self.play(ShowCreation(axes))\n"
            "        self.play(ShowCreation(surface), run_time=3)\n"
            "        self.frame.add_updater(\n"
            "            lambda m, dt: m.set_theta(m.get_theta() + 0.2 * dt)\n"
            "        )\n"
            "        self.wait(4)\n"
        ),
    ),
    Preset(
        id="phase-portrait",
        label="Phase portrait",
        duration="0:30",
        preview="/examples/differential_equations.gif",
        code=(
            "from manimlib import *\n"
            "import numpy as np\n"
            "\n"
            "class PhasePortrait(Scene):\n"
            "    def construct(self):\n"
            "        plane = NumberPlane(x_range=[-4, 4], y_range=[-3, 3])\n"
            "\n"
            "        # ManimGL's VectorField is vectorised: it calls the\n"
            "        # function once with an (N, 3) array of sample points and\n"
            "        # expects an (N, 3) array of vectors back.\n"
            "        def rotation_field(p):\n"
            "            out = np.zeros_like(p)\n"
            "            out[..., 0] = -p[..., 1]\n"
            "            out[..., 1] = p[..., 0]\n"
            "            return out\n"
            "\n"
            "        field = VectorField(rotation_field, coordinate_system=plane)\n"
            "        traj = ParametricCurve(\n"
            "            lambda t: np.array([2 * np.cos(t), 2 * np.sin(t), 0]),\n"
            "            t_range=[0, TAU, 0.05], color=YELLOW,\n"
            "        )\n"
            "        self.play(ShowCreation(plane))\n"
            "        self.play(ShowCreation(field), run_time=2)\n"
            "        self.play(ShowCreation(traj), run_time=3)\n"
            "        self.wait()\n"
        ),
    ),
]


def _validate_code(code: str) -> None:
    """Reject obvious egress / sandbox-escape patterns. Best-effort only.

    The container (or the user's choice to run local) is the real boundary;
    this is a cheap tripwire that catches mistakes before paying for
    ``docker run`` cold-start.
    """
    if len(code) > 32_000:
        raise PlaygroundValidationError("code too large (max 32k chars)")

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise PlaygroundValidationError(f"syntax error: {exc.msg}") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in _FORBIDDEN_MODULES:
                    raise PlaygroundValidationError(
                        f"import of '{alias.name}' is not allowed in the playground"
                    )
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in _FORBIDDEN_MODULES:
                raise PlaygroundValidationError(
                    f"import from '{node.module}' is not allowed in the playground"
                )
        elif isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
            raise PlaygroundValidationError(
                f"use of '{node.id}' is not allowed in the playground"
            )
        elif isinstance(node, ast.Attribute):
            if node.attr in {"system", "popen", "spawn", "fork"}:
                raise PlaygroundValidationError(
                    f"attribute '.{node.attr}' is not allowed in the playground"
                )


def _detect_scene_class(code: str, fallback: str) -> str:
    m = re.search(r"class\s+(\w+)\s*\(", code)
    return m.group(1) if m else fallback


def _find_video(job_dir: Path) -> Path | None:
    """Find the MP4 ManimGL produced. ManimGL writes under
    ``<video_dir>/<scene_file_stem>/<quality>/<SceneClass>.mp4`` — we just
    grab the first MP4 anywhere under the per-render dir.
    """
    if not job_dir.exists():
        return None
    for p in job_dir.rglob("*.mp4"):
        return p
    return None


def _check_docker_available() -> None:
    bin_path = shutil.which(settings.playground_docker_bin)
    if not bin_path:
        raise PlaygroundRuntimeUnavailable(
            f"docker binary '{settings.playground_docker_bin}' not on PATH"
        )
    try:
        proc = subprocess.run(
            [bin_path, "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired as exc:
        raise PlaygroundRuntimeUnavailable("docker daemon unreachable (timeout)") from exc
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:]
        raise PlaygroundRuntimeUnavailable(
            f"docker daemon unreachable: {' '.join(msg) or 'unknown error'}"
        )


def _check_local_manimgl() -> None:
    if not shutil.which(settings.playground_local_bin):
        raise PlaygroundRuntimeUnavailable(
            f"'{settings.playground_local_bin}' not on PATH. "
            "Install with `pip install manimgl` or set "
            "playground_sandbox_mode=docker."
        )


@dataclass
class PlaygroundRenderResult:
    render_id: str
    video_url: str
    scene_class: str
    quality: str
    took_ms: int
    log_lines: list[str]
    sandbox_mode: str


class PlaygroundService:
    def list_presets(self) -> list[Preset]:
        return list(PRESETS)

    def get_preset(self, preset_id: str) -> Preset | None:
        return next((p for p in PRESETS if p.id == preset_id), None)

    async def render(
        self,
        code: str,
        scene_name: str | None = None,
        quality: str = "720p",
    ) -> PlaygroundRenderResult:
        _validate_code(code)

        quality_args = _QUALITY_FLAGS.get(quality)
        if quality_args is None:
            raise PlaygroundValidationError(
                f"unsupported quality {quality!r}; expected one of {list(_QUALITY_FLAGS)}"
            )

        scene_class = _detect_scene_class(code, scene_name or "Scene")
        render_id = f"play_{uuid.uuid4().hex[:12]}"
        job_dir = PLAYGROUND_DIR / render_id
        job_dir.mkdir(parents=True, exist_ok=True)

        scene_file = job_dir / "scene.py"
        scene_file.write_text(code)
        media_dir = job_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)

        mode = settings.playground_sandbox_mode.lower()
        if mode == "docker":
            cmd = self._build_docker_cmd(job_dir, scene_class, quality_args)
        elif mode == "local":
            cmd = self._build_local_cmd(job_dir, scene_class, quality_args)
        else:
            raise PlaygroundValidationError(
                f"unknown playground_sandbox_mode {mode!r}; expected 'docker' or 'local'"
            )

        logger.info(
            "playground render: id=%s class=%s q=%s mode=%s",
            render_id, scene_class, quality, mode,
        )

        t0 = time.time()
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.playground_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise PlaygroundRenderError(
                f"render exceeded {settings.playground_timeout_seconds}s timeout"
            ) from exc

        took_ms = int((time.time() - t0) * 1000)

        if proc.returncode != 0:
            tail = (proc.stderr or "")[-2000:]
            raise PlaygroundRenderError(f"manimgl exited {proc.returncode}: {tail}")

        video = _find_video(job_dir)
        if not video:
            raise PlaygroundRenderError("manimgl completed but no .mp4 was produced")

        log_lines = [
            line
            for line in (proc.stdout or "").splitlines() + (proc.stderr or "").splitlines()
            if line.strip()
        ][-80:]

        return PlaygroundRenderResult(
            render_id=render_id,
            video_url=f"/api/v1/playground/renders/{render_id}/output",
            scene_class=scene_class,
            quality=quality,
            took_ms=took_ms,
            log_lines=log_lines,
            sandbox_mode=mode,
        )

    # ── command builders ────────────────────────────────────────────

    def _build_docker_cmd(
        self, job_dir: Path, scene_class: str, quality_args: list[str]
    ) -> list[str]:
        # Container layout:
        #   /work/scene.py        ← user code (mounted in)
        #   /work/media/...       ← manimgl output (read out after run)
        _check_docker_available()
        return [
            settings.playground_docker_bin,
            "run",
            "--rm",
            "--network", "none",
            "--user", "1000:1000",
            "--memory", settings.playground_memory_limit,
            "--cpus", settings.playground_cpu_limit,
            "--pids-limit", str(settings.playground_pids_limit),
            "--security-opt", "no-new-privileges",
            "--workdir", "/work",
            "-v", f"{job_dir}:/work",
            # The image's `run-manimgl` wrapper invokes `xvfb-run -a manimgl …`
            # so pyglet finds a display to open its shadow GL context against.
            # See infra/playground-runner/Dockerfile.
            "--entrypoint", "/usr/local/bin/run-manimgl",
            settings.playground_docker_image,
            "/work/scene.py",
            scene_class,
            "-w",                     # write file, don't open preview window
            *quality_args,
            "--video_dir", "/work/media",
        ]

    def _build_local_cmd(
        self, job_dir: Path, scene_class: str, quality_args: list[str]
    ) -> list[str]:
        # DEV-ONLY path. No isolation. Submitted code runs with the same
        # privileges as the API process — anything it can do, the code can.
        _check_local_manimgl()
        return [
            settings.playground_local_bin,
            str(job_dir / "scene.py"),
            scene_class,
            "-w",
            *quality_args,
            "--video_dir", str(job_dir / "media"),
        ]

    def output_path(self, render_id: str) -> Path | None:
        if not re.fullmatch(r"play_[A-Za-z0-9]+", render_id):
            return None
        return _find_video(PLAYGROUND_DIR / render_id)
