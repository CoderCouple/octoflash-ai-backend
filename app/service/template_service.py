"""
TemplateService — read-only catalog + def access for the API layer.

`list_templates()` is cheap (no defs are loaded). `get_template_detail()`
loads and validates the def via the loader; raises EntityNotFoundError if
the id isn't in the catalog and a NotImplementedError-shaped 404 if it's
in the catalog but no defs file exists yet.
"""

from __future__ import annotations

import json

from app.api.v1.response.template_response import (
    TemplateDetailResponse,
    TemplateSummaryResponse,
)
from app.common.exceptions import EntityNotFoundError
from app.templates.audit import template_content_hash
from app.templates.loader import TemplateNotImplementedError, is_implemented, load
from app.templates.registry import CATALOG, catalog_lookup


class TemplateService:
    def list_templates(self) -> list[TemplateSummaryResponse]:
        return [
            TemplateSummaryResponse(
                id=c.id,
                name=c.name,
                category=c.category,
                glyph=c.glyph,
                manic_compatible=c.manic_compatible,
                implemented=is_implemented(c.id),
            )
            for c in CATALOG
        ]

    def get_template_detail(self, template_id: str) -> TemplateDetailResponse:
        entry = catalog_lookup(template_id)
        if entry is None:
            raise EntityNotFoundError("Template", template_id)
        try:
            tpl = load(template_id)
        except TemplateNotImplementedError as e:
            # 404 with a precise message — the catalog knows about it, the def doesn't exist.
            raise EntityNotFoundError("TemplateDefinition", template_id) from e

        dumped = json.loads(tpl.model_dump_json(exclude_none=True))
        return TemplateDetailResponse(
            id=tpl.id,
            version=tpl.version,
            name=tpl.name,
            category=tpl.category,
            glyph=tpl.glyph,
            manic_compatible=tpl.manic_compatible,
            description=tpl.description,
            params=dumped.get("params", []),
            steps=dumped.get("steps", []),
            style_modifiers=dumped.get("style_modifiers", {}),
            default_duration=tpl.default_duration,
            default_size=tpl.default_size,
            content_hash=template_content_hash(tpl),
        )
