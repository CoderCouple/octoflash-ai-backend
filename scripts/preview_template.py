#!/usr/bin/env python
"""
preview_template.py — local template preview, bypassing API + Temporal + DB.

Renders one template directly with Manim and opens the resulting MP4 in your
default video player. Use this when iterating on primitive `build()` code —
edit a primitive, re-run, watch the result in seconds.

Examples
--------
Render title_reveal with default params:
    poetry run python scripts/preview_template.py title_reveal

Override params (values are JSON-parsed when possible):
    poetry run python scripts/preview_template.py text_pop \\
        --param text='"Hello!"' --param color='"#00FFAA"' --param shake_intensity=0.7

Pick a style preset, bump quality:
    poetry run python scripts/preview_template.py glitch_text \\
        --param text='"GLITCH"' --style manic --quality medium_quality

Use Manim's OpenGL renderer (live render window during the render):
    poetry run python scripts/preview_template.py title_reveal --renderer opengl

Watch mode — re-runs on every app/templates/ save:
    poetry run python scripts/preview_template.py glitch_text --watch
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Make `app.*` imports resolve when running from the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _parse_param(raw: str) -> tuple[str, object]:
    """Parse a `key=value` arg. Value is JSON-decoded; falls back to plain string."""
    if "=" not in raw:
        raise argparse.ArgumentTypeError(
            f"--param expects key=value (got {raw!r})"
        )
    key, value = raw.split("=", 1)
    try:
        parsed: object = json.loads(value)
    except json.JSONDecodeError:
        parsed = value
    return key, parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render one template locally and open the MP4.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("template_id", help="Template id, e.g. title_reveal")
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        type=_parse_param,
        metavar="KEY=VALUE",
        help="Override a template param. Repeat for multiple. "
             'Values are JSON-parsed: strings need quotes (--param text=\'"Hi"\').',
    )
    parser.add_argument(
        "--style", default=None,
        help="Style preset (e.g. manic). Optional.",
    )
    parser.add_argument(
        "--quality", default="low_quality",
        choices=["low_quality", "medium_quality", "high_quality", "production_quality"],
        help="Manim render quality preset.",
    )
    parser.add_argument(
        "--renderer", default="cairo",
        choices=["cairo", "opengl"],
        help="cairo = render to MP4 (default). "
             "opengl = live window during render (still writes MP4 too).",
    )
    parser.add_argument(
        "--no-open", action="store_true",
        help="Render but don't auto-open the MP4 in the system player.",
    )
    parser.add_argument(
        "--watch", action="store_true",
        help="Stay running; re-render whenever app/templates/ files change. "
             "Each re-render runs in a fresh subprocess for clean Python state.",
    )
    return parser


# ─── one-shot render ───────────────────────────────────────────────────────────


def _render_once(args: argparse.Namespace) -> None:
    """Render a single MP4 with the current code. Heavy imports stay here."""
    from manim import tempconfig

    from app.service.manim_scene import OctoflashScene
    from app.templates.loader import TemplateNotImplementedError, load
    from app.templates.renderer import TemplateRenderer

    try:
        load(args.template_id)
    except TemplateNotImplementedError:
        print(
            f"ERROR: template {args.template_id!r} has no app/templates/defs/<id>.py.",
            file=sys.stderr,
        )
        sys.exit(2)

    params = dict(args.param)
    renderer = TemplateRenderer(
        template_id=args.template_id,
        params=params,
        style=args.style,
    )

    media_dir = os.path.abspath("./media")
    os.makedirs(media_dir, exist_ok=True)
    output_filename = f"preview_{args.template_id}"
    snapshot_sink: dict[str, object] = {}

    print(
        f"→ template={args.template_id}  style={args.style}  "
        f"quality={args.quality}  renderer={args.renderer}"
    )
    print(f"→ params={params}")

    config = {
        "quality": args.quality,
        "output_file": output_filename,
        "media_dir": media_dir,
        "verbosity": "WARNING",
        "preview": not args.no_open,
        "disable_caching": True,
        "write_to_movie": True,
        "renderer": args.renderer,
    }

    with tempconfig(config):
        scene = OctoflashScene(renderer=renderer, snapshot_sink=snapshot_sink)
        scene.render()

    print(f"\n✓ Done. MP4 under {media_dir}/videos/{type(scene).__name__}/")
    if args.no_open:
        print("  (--no-open set; player was not launched)")


# ─── watch mode (parent process — respawns subprocess on file change) ──────────


def _max_mtime(root: Path) -> float:
    """Highest mtime across .py files under `root`. Used as the change marker."""
    latest = 0.0
    for p in root.rglob("*.py"):
        try:
            m = p.stat().st_mtime
            if m > latest:
                latest = m
        except OSError:
            continue
    return latest


def _run_watch_mode() -> None:
    """Watch app/templates/ for changes; respawn this script (sans --watch) on each."""
    watch_path = PROJECT_ROOT / "app" / "templates"
    if not watch_path.exists():
        print(f"ERROR: watch path {watch_path} not found", file=sys.stderr)
        sys.exit(2)

    # Re-spawn with the same argv, dropping --watch so the child does one render.
    child_argv = [a for a in sys.argv[1:] if a != "--watch"]
    cmd = [sys.executable, sys.argv[0]] + child_argv

    print(f"▶ Watch mode. Polling {watch_path} every 500ms. Ctrl+C to exit.\n")

    print("── initial render ──")
    subprocess.run(cmd)

    last = _max_mtime(watch_path)
    try:
        while True:
            time.sleep(0.5)
            current = _max_mtime(watch_path)
            if current > last:
                last = current
                print("\n ── change detected ──")
                subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n ▶ Watch mode stopped.")


def main() -> None:
    args = _build_parser().parse_args()
    if args.watch:
        _run_watch_mode()
    else:
        _render_once(args)


if __name__ == "__main__":
    main()
