"""Shared publish-payload dataclasses + result type."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PublishMetadata:
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    # Platform-specific privacy flags. Values that pass straight through to
    # the platform API: 'public' / 'unlisted' / 'private' on YT (default
    # 'private' so a half-set publish never goes live).
    privacy: str = "private"
    # Bag for platform-specific extras (e.g. YT categoryId, IG caption,
    # LinkedIn visibility code). Keeps the shared dataclass cheap.
    extra: dict[str, object] = field(default_factory=dict)


@dataclass
class PublishResult:
    """What a publisher returns after the platform confirms the upload."""

    platform_video_id: str
    platform_url: str
    raw: dict[str, object] | None = None


class PublishError(Exception):
    """Per-platform publish failure — caller wraps into the execution log."""
