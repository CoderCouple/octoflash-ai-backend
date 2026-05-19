"""
TemplateRenderer — walks a TemplateDefinition's steps and dispatches to primitives.

Owned by ManimRunnerService — it instantiates a renderer per scene render and
hands it a Manim Scene. The renderer returns the audit snapshot, which the
worker writes onto the Variation row.

Two responsibilities, kept narrow:
  1. Param validation + ${params.foo} interpolation.
  2. Step-by-step primitive dispatch, with style modifier applied.

It deliberately does *not* know anything about Manim, S3, jobs, or the DB —
those are the worker's job. This keeps the render logic unit-testable with
a mock scene object.
"""

from __future__ import annotations

import re
from typing import Any

# Side-effect import: registers all primitives in PRIMITIVES.
from app.templates import primitives as _primitives  # noqa: F401
from app.templates.audit import build_render_snapshot
from app.templates.loader import load
from app.templates.primitives.registry import get_primitive, primitive_versions
from app.templates.schema import StepSpec, TemplateDefinition


class ParamValidationError(ValueError):
    pass


class PrimitiveNotRegisteredError(LookupError):
    pass


# Matches a whole-string interp like "${params.title}" — preserves type.
_FULL_INTERP = re.compile(r"^\$\{params\.([a-zA-Z_][a-zA-Z0-9_]*)\}$")
# Matches embedded interp inside a longer string — coerces to str.
_INLINE_INTERP = re.compile(r"\$\{params\.([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _resolve(value: Any, params: dict[str, Any]) -> Any:
    """Recursively replace ${params.foo} references in a config value."""
    if isinstance(value, str):
        match = _FULL_INTERP.match(value.strip())
        if match:
            key = match.group(1)
            if key not in params:
                raise ParamValidationError(f"Interpolation references unknown param: {key!r}")
            return params[key]

        def _sub(m: re.Match[str]) -> str:
            key = m.group(1)
            if key not in params:
                raise ParamValidationError(f"Interpolation references unknown param: {key!r}")
            return str(params[key])

        return _INLINE_INTERP.sub(_sub, value)
    if isinstance(value, dict):
        return {k: _resolve(v, params) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(v, params) for v in value]
    return value


def validate_params(template: TemplateDefinition, params: dict[str, Any]) -> dict[str, Any]:
    """Apply defaults, enforce required, reject unknown."""
    known = {s.name for s in template.params}
    unknown = set(params) - known
    if unknown:
        raise ParamValidationError(
            f"Unknown params for {template.id!r}: {sorted(unknown)}"
        )

    resolved: dict[str, Any] = {}
    for spec in template.params:
        if spec.name in params:
            resolved[spec.name] = params[spec.name]
        elif getattr(spec, "default", None) is not None:
            resolved[spec.name] = spec.default
        elif spec.required:
            raise ParamValidationError(
                f"Missing required param for {template.id!r}: {spec.name}"
            )
    return resolved


class TemplateRenderer:
    """Render a template definition against a Manim Scene.

    `extra_steps` are per-scene divergence from the template baseline, produced
    by NL editing (POST /scenes/{id}/instruct). They're appended *after* the
    template's steps, then style-modifier scaling applies to the combined list
    so a Manic preset speeds up divergent steps too.
    """

    def __init__(
        self,
        template_id: str,
        params: dict[str, Any],
        style: str | None = None,
        extra_steps: list[StepSpec] | None = None,
    ) -> None:
        self.template = load(template_id)
        self.params = validate_params(self.template, params)
        self.style = style
        self.extra_steps: list[StepSpec] = list(extra_steps or [])

    def _base_steps(self) -> list[StepSpec]:
        """Template steps followed by per-scene extra_steps."""
        return list(self.template.steps) + self.extra_steps

    def _apply_style_modifier(self, steps: list[StepSpec]) -> list[StepSpec]:
        """Return a new steps list with the active style modifier applied."""
        if not self.style or self.style not in self.template.style_modifiers:
            return list(steps)

        mod = self.template.style_modifiers[self.style]
        scale = mod.duration_scale or 1.0
        scaled: list[StepSpec] = []
        for s in steps:
            new_duration: float | str | None = s.duration
            if isinstance(s.duration, (int, float)):
                new_duration = float(s.duration) * scale
            scaled.append(
                s.model_copy(
                    update={"duration": new_duration, "at": s.at * scale}
                )
            )
        return scaled + list(mod.extra_steps)

    def render(self, scene: Any) -> dict[str, Any]:
        """Execute all steps against `scene`. Return the audit snapshot."""
        from app.templates.primitives.base import PrimitiveContext

        steps = self._apply_style_modifier(self._base_steps())
        used_versions: dict[str, str] = {}

        for step in steps:
            primitive_cls = get_primitive(step.primitive)
            if primitive_cls is None:
                raise PrimitiveNotRegisteredError(
                    f"Template {self.template.id!r} step references unknown "
                    f"primitive {step.primitive!r}. Registered: {sorted(primitive_versions())}"
                )
            config_raw = _resolve(step.bind, self.params)
            duration = _resolve(step.duration, self.params) if step.duration is not None else None
            config = primitive_cls.parse_config(config_raw)
            ctx = PrimitiveContext(
                scene=scene,
                t=step.at,
                duration=duration,  # type: ignore[arg-type]
                style=self.style,
            )
            primitive_cls().build(config, ctx)
            used_versions[step.primitive] = primitive_cls.PRIMITIVE_VERSION

        return build_render_snapshot(
            self.template, self.params, self.style, used_versions, self.extra_steps
        )
