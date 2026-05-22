from enum import Enum


class ProjectStatus(str, Enum):
    """Top-level project lifecycle. Mirrors the MVP video status machine."""

    QUEUED = "queued"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    GENERATING = "generating"
    GENERATED = "generated"
    PUBLISHED = "published"
    FAILED = "failed"


class SceneStatus(str, Enum):
    """Per-clip render lifecycle."""

    DRAFT = "draft"
    SCRIPTING = "scripting"
    RENDERING = "rendering"
    READY = "ready"
    FAILED = "failed"


class Orientation(str, Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class Quality(str, Enum):
    LOW = "480p"
    MEDIUM = "720p"
    HIGH = "1080p"


class RenderMethod(str, Enum):
    """Which path of the 5-attempt fallback chain produced the MP4. Logged for lineage."""

    CLAUDE_VOICE = "claude_voice"
    CLAUDE_VOICE_RETRY = "claude_voice_retry"
    CLAUDE_NOVOICE = "claude_novoice"
    CLAUDE_NOVOICE_FRESH = "claude_novoice_fresh"
    SIMPLE_FALLBACK = "simple_fallback"
