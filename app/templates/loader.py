"""
Template loader — imports `app/templates/defs/<id>.py` and returns its TEMPLATE export.

A template "exists" (appears in the catalog and `GET /templates` lists it) the
moment it's added to `app/templates/registry.CATALOG`. But it isn't *implemented*
until both:
  1. A matching defs/<id>.py file exports a valid `TEMPLATE: TemplateDefinition`.
  2. Every primitive referenced by the template's steps (and its style modifiers)
     has its Manim `build()` wired (i.e. `Primitive.IMPLEMENTED == True`).

The planner's catalog block uses `is_implemented` to filter, so Claude can't
propose templates that would crash at render time.
"""

from __future__ import annotations

import importlib
from functools import lru_cache

from app.templates.schema import StepSpec, TemplateDefinition


class TemplateNotImplementedError(LookupError):
    """Listed in the catalog but no app/templates/defs/<id>.py module yet."""


class TemplateDefinitionInvalidError(ValueError):
    """defs/<id>.py exists but doesn't export `TEMPLATE: TemplateDefinition`."""


@lru_cache(maxsize=256)
def load(template_id: str) -> TemplateDefinition:
    """Resolve a template id to its full TemplateDefinition."""
    try:
        mod = importlib.import_module(f"app.templates.defs.{template_id}")
    except ModuleNotFoundError as e:
        raise TemplateNotImplementedError(template_id) from e

    template = getattr(mod, "TEMPLATE", None)
    if not isinstance(template, TemplateDefinition):
        raise TemplateDefinitionInvalidError(
            f"app/templates/defs/{template_id}.py must export TEMPLATE: TemplateDefinition"
        )
    if template.id != template_id:
        raise TemplateDefinitionInvalidError(
            f"app/templates/defs/{template_id}.py exports TEMPLATE.id={template.id!r}; "
            f"file name and TEMPLATE.id must match."
        )
    return template


def has_definition(template_id: str) -> bool:
    """True if a valid `defs/<id>.py` exists (regardless of primitive wiring)."""
    try:
        load(template_id)
        return True
    except (TemplateNotImplementedError, TemplateDefinitionInvalidError):
        return False


def _referenced_primitives(template: TemplateDefinition) -> set[str]:
    """Every primitive id referenced by the template's steps + style modifier steps."""
    seen: set[str] = set()

    def _collect(steps: list[StepSpec]) -> None:
        for s in steps:
            seen.add(s.primitive)

    _collect(template.steps)
    for mod in template.style_modifiers.values():
        _collect(mod.extra_steps)
    return seen


def all_primitives_wired(template: TemplateDefinition) -> bool:
    """True iff every referenced primitive has Primitive.IMPLEMENTED=True.

    Returns False if any referenced primitive is missing from the registry —
    that's a template authoring bug, but we report it the same as unwired
    (planner will skip it; explicit rendering will fail loudly with a helpful
    `PrimitiveNotRegisteredError` from the renderer).
    """
    # Triggers all primitives to register if they haven't already.
    from app.templates.primitives.registry import PRIMITIVES

    for pid in _referenced_primitives(template):
        cls = PRIMITIVES.get(pid)
        if cls is None or not getattr(cls, "IMPLEMENTED", False):
            return False
    return True


def is_implemented(template_id: str) -> bool:
    """True iff defs file exists AND all referenced primitives are wired.

    This is what `GET /templates` reports as `implemented`, and what the
    planner's catalog block filters by. It's the safe "this template will
    actually render end-to-end" signal.
    """
    if not has_definition(template_id):
        return False
    template = load(template_id)
    return all_primitives_wired(template)


def clear_cache() -> None:
    """Drop the LRU cache (for tests or hot-reload scenarios)."""
    load.cache_clear()
