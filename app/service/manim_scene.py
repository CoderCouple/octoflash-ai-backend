"""
OctoflashScene — the Manim Scene class our renderer plugs into.

When Manim invokes `construct()`, we hand the scene to TemplateRenderer.render(),
which walks the template's steps and lets each primitive add animations via the
scene reference. The audit snapshot is captured into `snapshot_sink` (a dict
passed in by ManimRunnerService) so the runner can return it alongside the MP4.
"""

from __future__ import annotations

from typing import Any

from manim import Scene

from app.templates.renderer import TemplateRenderer


class OctoflashScene(Scene):
    """Generic scene; behavior fully driven by the injected TemplateRenderer."""

    def __init__(
        self,
        renderer: TemplateRenderer,
        snapshot_sink: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        # Manim's Scene.__init__ accepts arbitrary kwargs (renderer/camera config).
        super().__init__(**kwargs)
        self._oct_renderer = renderer
        self._oct_snapshot_sink = snapshot_sink

    def construct(self) -> None:
        snapshot = self._oct_renderer.render(self)
        self._oct_snapshot_sink["snapshot"] = snapshot
