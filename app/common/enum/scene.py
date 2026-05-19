from enum import Enum


class SceneStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    RENDERING = "rendering"
    FAILED = "failed"


class StylePreset(str, Enum):
    EDITORIAL = "editorial"
    MANIC = "manic"
    CLASSIC_3B1B = "classic_3b1b"
    KURZGESAGT = "kurzgesagt"
    WHITEBOARD = "whiteboard"
    NEON = "neon"
    MONO = "mono"


class VariationStatus(str, Enum):
    QUEUED = "queued"
    RENDERING = "rendering"
    READY = "ready"
    FAILED = "failed"
