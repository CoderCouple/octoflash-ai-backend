"""
Audit / lineage helpers — every render carries the snapshot built here.

Two ideas:

1. **Content hash** (auto). SHA-256 of the resolved TemplateDefinition payload.
   Any behavior-affecting change to the def changes the hash. This is the
   ground truth for "did the render actually change?"

2. **Manual semver** (`TemplateDefinition.version`). The author bumps this on
   intentional behavior changes — gives you the *breaking change* signal that
   a hash alone can't provide.

Both are recorded on every Variation via `build_render_snapshot()`. Given just
that snapshot, any future worker can replay the exact render: the full
definition is embedded, so even after the file changes upstream, the audit
record is self-contained.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.templates.schema import TemplateDefinition


def template_content_hash(template: TemplateDefinition) -> str:
    """SHA-256 of the canonical JSON of the resolved definition."""
    payload = template.model_dump_json(exclude_none=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_render_snapshot(
    template: TemplateDefinition,
    params: dict[str, Any],
    style: str | None,
    primitive_versions: dict[str, str],
    extra_steps: list[Any] | None = None,
) -> dict[str, Any]:
    """Construct the audit record stored on Variation.params_snapshot.

    Embeds the *entire* definition (not just an id+version pointer) so the
    record is self-contained — replays don't depend on the file still existing.
    `extra_steps` captures per-scene NL divergence so replay reproduces it too.
    """
    return {
        "template": {
            "id": template.id,
            "version": template.version,
            "content_hash": template_content_hash(template),
            # Full definition for replay
            "definition": json.loads(template.model_dump_json(exclude_none=True)),
        },
        "params": params,
        "style": style,
        "primitive_versions": primitive_versions,
        "extra_steps": [
            json.loads(s.model_dump_json(exclude_none=True))
            if hasattr(s, "model_dump_json")
            else s
            for s in (extra_steps or [])
        ],
    }
