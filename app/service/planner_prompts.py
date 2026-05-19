"""
Prompts + tool schemas for PlannerService.

Two LLM call shapes:

  instruct_scene  — surgical, scene-level. Input is one template's spec + the
                    user's NL instruction; output is a new `extra_steps` list.

  plan_from_prompt — broad, project-level. Input is a freeform prompt + the
                    catalog of implemented templates; output is an ordered
                    list of scenes shaped like CreateSceneRequest payloads.

Both use Anthropic's *tool use* for structured output (more reliable than
prompt-engineered JSON). Both lean on *prompt caching* for the catalog blocks
which are large but identical across calls — the per-call cost is dominated
by the small user prompt + the scene state, both uncached.
"""

from __future__ import annotations

import json
from typing import Any

from app.templates.loader import is_implemented, load
from app.templates.primitives.registry import PRIMITIVES, primitive_versions
from app.templates.registry import CATALOG
from app.templates.schema import TemplateDefinition


# ─── Tool schemas (mirror StepSpec / scene-create shapes) ──────────────────────

# Minimal subset of StepSpec for the LLM to emit. The renderer will Pydantic-
# validate the full thing, so missing optional fields default sanely.
_STEP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["primitive", "at"],
    "properties": {
        "primitive": {
            "type": "string",
            "description": "Primitive id; must be one of the registered primitives listed in the system prompt.",
        },
        "bind": {
            "type": "object",
            "description": "Config passed to the primitive. May contain '${params.foo}' interpolation strings.",
            "additionalProperties": True,
            "default": {},
        },
        "at": {
            "type": "number",
            "description": "Start time within the scene, in seconds.",
        },
        "duration": {
            "type": ["number", "string", "null"],
            "description": "Step duration (seconds) or a '${params.foo}' interp string. Null = primitive's natural duration.",
        },
        "label": {
            "type": ["string", "null"],
            "description": "Optional human-readable label for this step (shown in audit logs).",
        },
    },
}


INSTRUCT_TOOL: dict[str, Any] = {
    "name": "apply_scene_edit",
    "description": (
        "Apply a user's natural-language edit to a scene by emitting the NEW "
        "full extra_steps list that should replace the scene's current divergence. "
        "Returning an empty list means 'revert to template baseline'."
    ),
    "input_schema": {
        "type": "object",
        "required": ["extra_steps", "reasoning"],
        "properties": {
            "extra_steps": {
                "type": "array",
                "description": "The new full extra_steps for the scene (replaces whatever was there).",
                "items": _STEP_SCHEMA,
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of what you changed and why (surfaced in the audit log).",
            },
            "warnings": {
                "type": "array",
                "description": "Any caveats the user should know about (guessed values, ambiguity, etc.).",
                "items": {"type": "string"},
                "default": [],
            },
        },
    },
}


_PLAN_SCENE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["template", "params"],
    "properties": {
        "template": {
            "type": "string",
            "description": "Template id; must be one of the IMPLEMENTED templates listed in the system prompt.",
        },
        "title": {
            "type": ["string", "null"],
            "description": "Optional scene title shown in the editor's left panel.",
        },
        "params": {
            "type": "object",
            "description": "Filled-in template params. Must satisfy the template's declared param schema.",
            "additionalProperties": True,
        },
        "prompt": {
            "type": ["string", "null"],
            "description": "Optional brief notes describing the scene's intent.",
        },
        "duration": {
            "type": ["number", "null"],
            "description": "Override the template's default duration (seconds).",
        },
        "style": {
            "type": ["string", "null"],
            "description": "One of: editorial, manic, classic_3b1b, kurzgesagt, whiteboard, neon, mono.",
        },
    },
}


PLAN_TOOL: dict[str, Any] = {
    "name": "propose_scene_plan",
    "description": (
        "Propose an ordered list of scenes for the project, derived from the "
        "user's freeform prompt. Use ONLY implemented templates listed in the "
        "system prompt."
    ),
    "input_schema": {
        "type": "object",
        "required": ["scenes", "reasoning"],
        "properties": {
            "scenes": {
                "type": "array",
                "description": "Ordered list of scenes (rendered in array order).",
                "items": _PLAN_SCENE_SCHEMA,
                "minItems": 1,
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of the structure (what the video accomplishes).",
            },
        },
    },
}


# ─── Catalog serialization (cached block content) ──────────────────────────────


def _template_brief(t: TemplateDefinition) -> dict[str, Any]:
    return {
        "id": t.id,
        "name": t.name,
        "category": t.category,
        "manic_compatible": t.manic_compatible,
        "description": t.description or "",
        "params": [
            {
                "name": p.name,
                "label": p.label,
                "type": p.type,
                "required": p.required,
                "default": getattr(p, "default", None),
            }
            for p in t.params
        ],
        "default_duration": t.default_duration,
    }


def implemented_templates_block() -> str:
    """JSON listing of every implemented template, with param shapes.

    Designed to live in a cached system block — large but stable. Plan and
    instruct prompts both reference it so Claude knows what's available.
    """
    items = []
    for entry in CATALOG:
        if not is_implemented(entry.id):
            continue
        try:
            items.append(_template_brief(load(entry.id)))
        except Exception:
            continue
    return json.dumps({"implemented_templates": items}, indent=2)


def primitives_block() -> str:
    """JSON listing of every registered primitive + its CONFIG_SCHEMA.

    Used by `instruct_scene` so Claude can compose step specs with the right
    config shape. Cached.
    """
    items = []
    for pid, cls in sorted(PRIMITIVES.items()):
        try:
            schema = cls.CONFIG_SCHEMA.model_json_schema()
        except Exception:
            schema = {"type": "object"}
        items.append(
            {
                "id": pid,
                "version": cls.PRIMITIVE_VERSION,
                "config_schema": schema,
            }
        )
    return json.dumps(
        {"primitives": items, "primitive_versions": primitive_versions()},
        indent=2,
    )


# ─── Per-call assembly ─────────────────────────────────────────────────────────


_INSTRUCT_SYSTEM = """\
You are an editing assistant for Octoflash, a scene-first AI video editor for Manim animations.

A user is editing ONE scene of a video. They've given you a natural-language instruction.
Your job: produce a NEW `extra_steps` list that, when rendered on top of the scene's template
baseline, satisfies the instruction.

Critical rules:
- Use ONLY primitive ids from the primitives catalog below.
- Each step's `bind` must conform to that primitive's `config_schema`.
- You may reference scene params with the interpolation syntax: "${params.<param_name>}".
- `extra_steps` replaces (not appends to) whatever the scene had — emit the full intended list.
- Returning an empty `extra_steps` means "revert to template baseline".
- Be conservative: if the instruction is ambiguous, emit a small change and flag the ambiguity
  in `warnings`.

Call the `apply_scene_edit` tool with your response.
"""


_PLAN_SYSTEM = """\
You are a video planner for Octoflash, a scene-first AI video editor for Manim animations.

The user has given you a freeform prompt describing a video they want. Your job: produce an
ordered list of scenes that, stitched together, make that video.

Critical rules:
- Use ONLY templates from the implemented_templates catalog below. (Other templates exist in
  the catalog but aren't renderable yet — do not propose them.)
- For each scene, fill in `params` matching the template's param schema. Defaults are listed
  for guidance — override them with content that actually fits the user's prompt.
- Choose `style` carefully — pick `manic` only for templates flagged `manic_compatible: true`.
- Pick a reasonable scene count (3-8 scenes for a short video, more for longer content).
- Don't pad — each scene should earn its place.

Call the `propose_scene_plan` tool with your response.
"""


def build_instruct_messages(
    template: TemplateDefinition,
    params: dict[str, Any],
    current_extra_steps: list[dict[str, Any]],
    instruction: str,
    prior_instructions: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (system_blocks, messages) for the instruct call."""
    system_blocks = [
        # Stable, cached: the primitive catalog.
        {
            "type": "text",
            "text": "# Primitives catalog\n```json\n" + primitives_block() + "\n```",
            "cache_control": {"type": "ephemeral"},
        },
        # Per-call: the instructions for what to do.
        {"type": "text", "text": _INSTRUCT_SYSTEM},
    ]

    user_payload = {
        "scene_template": _template_brief(template),
        "current_params": params,
        "current_extra_steps": current_extra_steps,
        "prior_instructions": prior_instructions,
        "new_instruction": instruction,
    }
    messages = [
        {
            "role": "user",
            "content": (
                "Edit this scene per the new_instruction. Respond by calling "
                "`apply_scene_edit`.\n\n"
                "```json\n" + json.dumps(user_payload, indent=2) + "\n```"
            ),
        }
    ]
    return system_blocks, messages


def build_plan_messages(
    prompt: str,
    style_preference: str | None = None,
    max_scenes: int | None = None,
    target_duration: float | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (system_blocks, messages) for the plan_from_prompt call.

    Optional knobs are surfaced as soft hints in the user message — Claude can
    deviate if the prompt genuinely calls for it.
    """
    system_blocks = [
        {
            "type": "text",
            "text": "# Implemented templates\n```json\n"
            + implemented_templates_block()
            + "\n```",
            "cache_control": {"type": "ephemeral"},
        },
        {"type": "text", "text": _PLAN_SYSTEM},
    ]

    constraints: list[str] = []
    if style_preference:
        constraints.append(f"- Prefer style: `{style_preference}` across scenes when sensible.")
    if max_scenes:
        constraints.append(f"- Aim for at most {max_scenes} scenes.")
    if target_duration:
        constraints.append(
            f"- Target total duration roughly {target_duration:.1f} seconds "
            "(sum of per-scene durations)."
        )
    constraints_block = (
        "\n\n## Constraints\n" + "\n".join(constraints) if constraints else ""
    )

    messages = [
        {
            "role": "user",
            "content": (
                "Plan a video for this prompt. Respond by calling "
                "`propose_scene_plan`.\n\n"
                f"## Prompt\n{prompt}"
                f"{constraints_block}"
            ),
        }
    ]
    return system_blocks, messages
