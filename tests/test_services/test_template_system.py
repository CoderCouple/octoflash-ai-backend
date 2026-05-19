"""Unit tests for the template system internals (no DB, no HTTP)."""

import pytest

from app.templates.audit import build_render_snapshot, template_content_hash
from app.templates.loader import (
    TemplateNotImplementedError,
    is_implemented,
    load,
)
from app.templates.renderer import (
    ParamValidationError,
    TemplateRenderer,
    _resolve,
    validate_params,
)


class TestLoader:
    def test_load_implemented_template(self):
        tpl = load("title_reveal")
        assert tpl.id == "title_reveal"
        assert tpl.version == "1.0.0"

    def test_load_unimplemented_template_raises(self):
        with pytest.raises(TemplateNotImplementedError):
            load("text_pop")

    def test_is_implemented(self):
        assert is_implemented("title_reveal") is True
        assert is_implemented("text_pop") is False
        assert is_implemented("not_a_template") is False


class TestParamValidation:
    def test_defaults_applied(self):
        tpl = load("title_reveal")
        resolved = validate_params(tpl, {"title": "Hello"})
        assert resolved["title"] == "Hello"
        assert resolved["color"] == "#FFFFFF"  # from default
        assert resolved["hold_seconds"] == 2.0

    def test_missing_required_raises(self):
        tpl = load("title_reveal")
        with pytest.raises(ParamValidationError, match="title"):
            validate_params(tpl, {})

    def test_unknown_param_rejected(self):
        tpl = load("title_reveal")
        with pytest.raises(ParamValidationError, match="bogus"):
            validate_params(tpl, {"title": "x", "bogus": 1})


class TestInterpolation:
    def test_whole_string_preserves_type(self):
        out = _resolve("${params.count}", {"count": 42})
        assert out == 42 and isinstance(out, int)

    def test_embedded_coerces_to_string(self):
        out = _resolve("Title is ${params.title}", {"title": "Hello"})
        assert out == "Title is Hello"

    def test_unknown_reference_raises(self):
        with pytest.raises(ParamValidationError):
            _resolve("${params.missing}", {})

    def test_dict_recursion(self):
        out = _resolve(
            {"text": "${params.t}", "size": 12, "nested": {"k": "${params.t}"}},
            {"t": "Hi"},
        )
        assert out == {"text": "Hi", "size": 12, "nested": {"k": "Hi"}}


class TestAudit:
    def test_content_hash_is_deterministic(self):
        tpl = load("title_reveal")
        h1 = template_content_hash(tpl)
        h2 = template_content_hash(tpl)
        assert h1 == h2
        assert len(h1) == 64  # sha256 hex

    def test_snapshot_embeds_full_definition(self):
        tpl = load("title_reveal")
        snap = build_render_snapshot(tpl, {"title": "Hi"}, "manic", {"text_reveal": "1.0.0"})
        assert snap["template"]["id"] == "title_reveal"
        assert snap["template"]["version"] == "1.0.0"
        assert snap["template"]["content_hash"] == template_content_hash(tpl)
        # Full definition embedded so the snapshot is self-contained for replay
        assert snap["template"]["definition"]["id"] == "title_reveal"
        assert snap["params"] == {"title": "Hi"}
        assert snap["style"] == "manic"
        assert snap["primitive_versions"] == {"text_reveal": "1.0.0"}


class TestRendererConstruction:
    def test_construct_with_valid_params(self):
        renderer = TemplateRenderer("title_reveal", {"title": "Hello"})
        assert renderer.template.id == "title_reveal"
        assert renderer.params["title"] == "Hello"
        assert renderer.params["color"] == "#FFFFFF"  # default

    def test_construct_with_unknown_template_raises(self):
        with pytest.raises(TemplateNotImplementedError):
            TemplateRenderer("text_pop", {})

    def test_style_modifier_scales_durations(self):
        renderer = TemplateRenderer("title_reveal", {"title": "Hi"}, style="manic")
        scaled = renderer._apply_style_modifier(renderer.template.steps)
        # title_reveal's manic modifier has duration_scale=0.6 → first step 1.0 → 0.6
        first = scaled[0]
        assert first.duration == pytest.approx(0.6)


class TestPrimitivesRegistered:
    def test_text_reveal_registered(self):
        from app.templates.primitives.registry import PRIMITIVES

        assert "text_reveal" in PRIMITIVES
        assert "hold" in PRIMITIVES

    def test_primitive_versions_snapshot(self):
        from app.templates.primitives.registry import primitive_versions

        versions = primitive_versions()
        assert versions["text_reveal"] == "1.0.0"
        assert versions["hold"] == "1.0.0"
