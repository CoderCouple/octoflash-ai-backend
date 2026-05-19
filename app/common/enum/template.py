from enum import Enum


class TemplateCategory(str, Enum):
    TEXT_TITLES = "text_titles"
    MATH_EQUATIONS = "math_equations"
    DATA_CHARTS = "data_charts"
    DIAGRAMS = "diagrams"
    COMPARE_CONTRAST = "compare_contrast"
    EMPHASIS_REVEALS = "emphasis_reveals"
    MOTION_GEOMETRY = "motion_geometry"
    CAMERA_TRANSITIONS = "camera_transitions"
    OUTROS_CTAS = "outros_ctas"
    MEDIA = "media"
    REACTIONS_SHORTS = "reactions_shorts"


# Human-readable labels for UI
CATEGORY_LABELS: dict[str, str] = {
    "text_titles": "Text & titles",
    "math_equations": "Math & equations",
    "data_charts": "Data & charts",
    "diagrams": "Diagrams",
    "compare_contrast": "Compare & contrast",
    "emphasis_reveals": "Emphasis & reveals",
    "motion_geometry": "Motion & geometry",
    "camera_transitions": "Camera & transitions",
    "outros_ctas": "Outros & CTAs",
    "media": "Media",
    "reactions_shorts": "Reactions / shorts vernacular",
}
