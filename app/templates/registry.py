"""
Template catalog — the single source of truth for every template Octoflash supports.

`CATALOG` below enumerates every template id + category + manic flag. This is
what `GET /templates` returns. Each entry is *exposed* in the catalog even if
its `app/templates/defs/<id>.py` hasn't been written yet — `loader.load(id)`
raises `TemplateNotImplementedError` until the def exists. The frontend can
grey-out unimplemented entries in the library UI.

This split lets the system claim its full surface area (127 templates across 11
categories) without forcing all 127 defs to land before the API ships.

Counts mirror the design spec:
  - 127 templates total
  - 16 manic-compatible (9 original + all 7 in Reactions/shorts vernacular)
  - 11 categories
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogEntry:
    id: str
    category: str
    manic_compatible: bool

    @property
    def name(self) -> str:
        """Default human label — id with underscores → words, title-cased."""
        return self.id.replace("_", " ").title()

    @property
    def glyph(self) -> str:
        """Frontend icon id — one-to-one with template id by convention."""
        return self.id


# fmt: off
CATALOG: list[CatalogEntry] = [
    # ─── Text & titles (18) ──────────────────────────────────────────────────
    CatalogEntry("title_reveal",          "text_titles", True),
    CatalogEntry("text_pop",              "text_titles", True),
    CatalogEntry("subtitle_stack",        "text_titles", False),
    CatalogEntry("typewriter",            "text_titles", False),
    CatalogEntry("big_quote",             "text_titles", False),
    CatalogEntry("glitch_text",           "text_titles", True),
    CatalogEntry("kinetic_typography",    "text_titles", False),
    CatalogEntry("word_swap",             "text_titles", False),
    CatalogEntry("text_explode",          "text_titles", False),
    CatalogEntry("text_implode",          "text_titles", False),
    CatalogEntry("text_reveal_mask",      "text_titles", False),
    CatalogEntry("lower_third",           "text_titles", False),
    CatalogEntry("chapter_card",          "text_titles", False),
    CatalogEntry("tagline_split",         "text_titles", False),
    CatalogEntry("acronym_expand",        "text_titles", False),
    CatalogEntry("handwritten_signature", "text_titles", False),
    CatalogEntry("redacted_reveal",       "text_titles", False),
    CatalogEntry("highlight_marker",      "text_titles", False),

    # ─── Math & equations (14) ───────────────────────────────────────────────
    CatalogEntry("equation_morph",   "math_equations", False),
    CatalogEntry("equation_derive",  "math_equations", False),
    CatalogEntry("formula_explain",  "math_equations", False),
    CatalogEntry("proof_steps",      "math_equations", False),
    CatalogEntry("factor_tree",      "math_equations", False),
    CatalogEntry("substitute_in",    "math_equations", False),
    CatalogEntry("equation_balance", "math_equations", False),
    CatalogEntry("integral_area",    "math_equations", False),
    CatalogEntry("limit_zoom",       "math_equations", False),
    CatalogEntry("summation_unroll", "math_equations", False),
    CatalogEntry("matrix_transform", "math_equations", False),
    CatalogEntry("complex_plane",    "math_equations", False),
    CatalogEntry("vector_field",     "math_equations", False),
    CatalogEntry("derivative_slope", "math_equations", False),

    # ─── Data & charts (15) ──────────────────────────────────────────────────
    CatalogEntry("chart_growth",         "data_charts", False),
    CatalogEntry("chart_compare",        "data_charts", False),
    CatalogEntry("line_reveal",          "data_charts", False),
    CatalogEntry("pie_breakdown",        "data_charts", False),
    CatalogEntry("stat_punch",           "data_charts", True),
    CatalogEntry("timeline_horizontal",  "data_charts", False),
    CatalogEntry("bar_race",             "data_charts", False),
    CatalogEntry("scatter_cluster",      "data_charts", False),
    CatalogEntry("histogram_build",      "data_charts", False),
    CatalogEntry("stacked_area",         "data_charts", False),
    CatalogEntry("donut_progress",       "data_charts", False),
    CatalogEntry("gauge_dial",           "data_charts", False),
    CatalogEntry("funnel_drop",          "data_charts", False),
    CatalogEntry("heatmap_reveal",       "data_charts", False),
    CatalogEntry("sparkline_pop",        "data_charts", False),

    # ─── Diagrams (14) ───────────────────────────────────────────────────────
    CatalogEntry("diagram_build",     "diagrams", False),
    CatalogEntry("flow_diagram",      "diagrams", False),
    CatalogEntry("venn_diagram",      "diagrams", False),
    CatalogEntry("tree_diagram",      "diagrams", False),
    CatalogEntry("state_machine",     "diagrams", False),
    CatalogEntry("mind_map",          "diagrams", False),
    CatalogEntry("org_chart",         "diagrams", False),
    CatalogEntry("swimlane",          "diagrams", False),
    CatalogEntry("circuit_diagram",   "diagrams", False),
    CatalogEntry("process_loop",      "diagrams", False),
    CatalogEntry("iceberg",           "diagrams", False),
    CatalogEntry("pyramid_levels",    "diagrams", False),
    CatalogEntry("knot_diagram",      "diagrams", False),
    CatalogEntry("dependency_graph",  "diagrams", False),

    # ─── Compare & contrast (9) ──────────────────────────────────────────────
    CatalogEntry("split_comparison",     "compare_contrast", False),
    CatalogEntry("before_after",         "compare_contrast", False),
    CatalogEntry("this_vs_that",         "compare_contrast", True),
    CatalogEntry("pros_cons",            "compare_contrast", False),
    CatalogEntry("four_quadrants",       "compare_contrast", False),
    CatalogEntry("slider_compare",       "compare_contrast", False),
    CatalogEntry("expectation_reality",  "compare_contrast", False),
    CatalogEntry("scale_compare",        "compare_contrast", False),
    CatalogEntry("trio_compare",         "compare_contrast", False),

    # ─── Emphasis & reveals (13) ─────────────────────────────────────────────
    CatalogEntry("callout_zoom",      "emphasis_reveals", True),
    CatalogEntry("bullet_burst",      "emphasis_reveals", True),
    CatalogEntry("numbered_steps",    "emphasis_reveals", False),
    CatalogEntry("spotlight",         "emphasis_reveals", False),
    CatalogEntry("circle_underline",  "emphasis_reveals", False),
    CatalogEntry("arrow_label",       "emphasis_reveals", False),
    CatalogEntry("margin_note",       "emphasis_reveals", False),
    CatalogEntry("strike_through",    "emphasis_reveals", False),
    CatalogEntry("blur_focus",        "emphasis_reveals", False),
    CatalogEntry("pixelate_reveal",   "emphasis_reveals", False),
    CatalogEntry("vignette_pull",     "emphasis_reveals", False),
    CatalogEntry("highlight_box",     "emphasis_reveals", False),
    CatalogEntry("flash_white",       "emphasis_reveals", False),

    # ─── Motion & geometry (11) ──────────────────────────────────────────────
    CatalogEntry("shape_morph",         "motion_geometry", False),
    CatalogEntry("wave_animation",      "motion_geometry", False),
    CatalogEntry("rotate_3d",           "motion_geometry", False),
    CatalogEntry("orbit_path",          "motion_geometry", False),
    CatalogEntry("bounce_in",           "motion_geometry", False),
    CatalogEntry("spring_settle",       "motion_geometry", False),
    CatalogEntry("path_trace",          "motion_geometry", False),
    CatalogEntry("morph_polygon",       "motion_geometry", False),
    CatalogEntry("fractal_zoom",        "motion_geometry", False),
    CatalogEntry("explode_particles",   "motion_geometry", False),
    CatalogEntry("gravity_drop",        "motion_geometry", False),

    # ─── Camera & transitions (9) ────────────────────────────────────────────
    CatalogEntry("camera_pan",         "camera_transitions", False),
    CatalogEntry("camera_zoom",        "camera_transitions", False),
    CatalogEntry("camera_tilt",        "camera_transitions", False),
    CatalogEntry("cross_dissolve",     "camera_transitions", False),
    CatalogEntry("wipe_transition",    "camera_transitions", False),
    CatalogEntry("iris_transition",    "camera_transitions", False),
    CatalogEntry("whip_pan",           "camera_transitions", False),
    CatalogEntry("page_curl",          "camera_transitions", False),
    CatalogEntry("glitch_transition",  "camera_transitions", False),

    # ─── Outros & CTAs (9) ───────────────────────────────────────────────────
    CatalogEntry("countdown",           "outros_ctas", True),
    CatalogEntry("cta_card",            "outros_ctas", False),
    CatalogEntry("subscribe_smash",     "outros_ctas", True),
    CatalogEntry("thanks_outro",        "outros_ctas", False),
    CatalogEntry("next_video_card",     "outros_ctas", False),
    CatalogEntry("patreon_thanks",      "outros_ctas", False),
    CatalogEntry("share_prompt",        "outros_ctas", False),
    CatalogEntry("logo_lockup",         "outros_ctas", False),
    CatalogEntry("outro_loop",          "outros_ctas", False),

    # ─── Media (8) ───────────────────────────────────────────────────────────
    CatalogEntry("image_annotated",          "media", False),
    CatalogEntry("image_kenburns",           "media", False),
    CatalogEntry("image_polaroid_stack",     "media", False),
    CatalogEntry("image_split_reveal",       "media", False),
    CatalogEntry("video_picture_in_picture", "media", False),
    CatalogEntry("code_block_reveal",        "media", False),
    CatalogEntry("map_pin_drop",             "media", False),
    CatalogEntry("map_path_animate",         "media", False),

    # ─── Reactions / shorts vernacular (7 — all manic-friendly) ──────────────
    CatalogEntry("screen_shake",         "reactions_shorts", True),
    CatalogEntry("freeze_frame",         "reactions_shorts", True),
    CatalogEntry("record_scratch",       "reactions_shorts", True),
    CatalogEntry("caption_pop",          "reactions_shorts", True),
    CatalogEntry("emoji_burst",          "reactions_shorts", True),
    CatalogEntry("meme_arrow",           "reactions_shorts", True),
    CatalogEntry("bottom_caption_stack", "reactions_shorts", True),
]
# fmt: on


# Sanity guard at import time — fails fast if a duplicate id slips in.
_ids: set[str] = set()
for _entry in CATALOG:
    if _entry.id in _ids:
        raise ValueError(f"Duplicate template id in CATALOG: {_entry.id!r}")
    _ids.add(_entry.id)


def list_catalog() -> list[CatalogEntry]:
    return list(CATALOG)


def all_template_ids() -> list[str]:
    return [c.id for c in CATALOG]


def catalog_lookup(template_id: str) -> CatalogEntry | None:
    for c in CATALOG:
        if c.id == template_id:
            return c
    return None
