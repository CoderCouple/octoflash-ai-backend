"""
Dummy portrait render — verifies the 9x16 logical frame puts content edge-to-edge.

NO Claude calls. NO eval loop. Calls `_render_scene_sync` directly so the
exact dummy scene below is what lands in the MP4 (the `render_clip` wrapper
would otherwise see a low vision-eval score and replace the test with
Claude-regenerated code).

Usage:
    poetry run python scripts/portrait_smoke.py
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.service.manim_render_service import _render_scene_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("app.service.manim_render_service").setLevel(logging.INFO)

DUMMY_SCENE = '''\
from manim import *
from app.manim_pipeline.styles import (
    OctoflashSceneNoVoice,
    Title, BodyText, Caption,
    BG_COLOR, TEXT_PRIMARY, ACCENT_CYAN, ACCENT_YELLOW,
)

class PortraitFrameTest(OctoflashSceneNoVoice):
    def construct(self):
        # Outline of the logical frame. With portrait config (9 wide x 16 tall),
        # this rectangle should touch all four edges of the MP4. If you see
        # black bands above/below the cyan border, the config didn't take.
        border = Rectangle(
            width=8.9, height=15.9,
            color=ACCENT_CYAN, stroke_width=4,
        )

        title = Title("TOP edge")
        title.to_edge(UP, buff=0.7)

        body = BodyText("center")
        body.move_to(ORIGIN)

        caption = Caption("BOTTOM edge")
        caption.to_edge(DOWN, buff=0.4)

        # Markers at y=+4 and y=-4 (the old landscape extents). If the frame
        # is genuinely 9x16, these should sit in the MIDDLE area, not at the
        # edges — proving the logical frame really is taller than landscape.
        y_plus_4 = BodyText("y = +4", color=ACCENT_YELLOW).scale(0.6)
        y_plus_4.shift(UP * 4 + LEFT * 1.5)
        y_minus_4 = BodyText("y = -4", color=ACCENT_YELLOW).scale(0.6)
        y_minus_4.shift(DOWN * 4 + LEFT * 1.5)

        self.play(FadeIn(border), run_time=0.5)
        self.play(FadeIn(title), FadeIn(body), FadeIn(caption), run_time=0.6)
        self.play(FadeIn(y_plus_4), FadeIn(y_minus_4), run_time=0.4)
        self.wait(2)
'''


def main() -> int:
    clip_id = f"portrait_smoke_{int(time.time())}"
    print(f"\n── portrait dummy render: clip_id={clip_id} (NO eval loop, NO Claude) ──\n")

    t0 = time.time()
    result = _render_scene_sync(
        clip_id=clip_id,
        scene_code=DUMMY_SCENE,
        quality="ql",
        portrait=True,
        voice_id="",
    )
    elapsed = time.time() - t0

    video_file = Path(result["video_file"]) if result["video_file"] else None
    print(f"\n── result (took {elapsed:.1f}s) ──")
    print(f"  scene_file: {result['scene_file']}")
    print(f"  video_file: {video_file}")
    if video_file and video_file.exists():
        print(f"  size:       {video_file.stat().st_size:,} bytes")
        print(f"\n  Open:\n    open {video_file}\n")
        return 0
    print(f"\n  ✗ no video file produced\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
