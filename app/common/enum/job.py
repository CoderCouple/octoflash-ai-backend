from enum import Enum


class JobKind(str, Enum):
    """What kind of work a job represents."""

    VARIATIONS = "variations"        # generate N variations for a scene
    RERENDER = "rerender"            # re-render an existing variation
    PREVIEW = "preview"              # low-quality stitch of a path
    EXPORT = "export"                # full-quality stitch + encode
    TRANSCRIBE = "transcribe"        # whisper transcription
    PLAN = "plan"                    # prompt -> scene plan via Claude


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
