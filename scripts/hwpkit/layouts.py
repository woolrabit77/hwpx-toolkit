from __future__ import annotations

from typing import Any


# Hancom Hangul's standard A4 initial page margins, expressed in millimetres.
# Templates may override individual values when their document family requires
# a compact or publication-specific layout.
PAGE_LAYOUT_PROFILES: dict[str, dict[str, float | int]] = {
    "standard-a4": {
        "page_width_mm": 210,
        "page_height_mm": 297,
        "left_mm": 30,
        "right_mm": 30,
        "top_mm": 20,
        "bottom_mm": 15,
        "header_mm": 15,
        "footer_mm": 15,
        "columns": 1,
        "column_gap_mm": 8,
    },
    "compact-a4": {
        "page_width_mm": 210,
        "page_height_mm": 297,
        "left_mm": 12,
        "right_mm": 12,
        "top_mm": 10,
        "bottom_mm": 10,
        "header_mm": 6,
        "footer_mm": 6,
        "columns": 1,
        "column_gap_mm": 8,
    },
}
DEFAULT_LAYOUT_PROFILE = "standard-a4"


def resolve_layout(metadata: dict[str, object]) -> dict[str, float | int]:
    raw = metadata.get("layout")
    layout = raw if isinstance(raw, dict) else {}
    profile_name = str(layout.get("profile", DEFAULT_LAYOUT_PROFILE))
    if profile_name not in PAGE_LAYOUT_PROFILES:
        available = ", ".join(sorted(PAGE_LAYOUT_PROFILES))
        raise ValueError(f"Unknown layout profile '{profile_name}'. Available profiles: {available}")
    resolved = dict(PAGE_LAYOUT_PROFILES[profile_name])
    resolved.update({key: value for key, value in layout.items() if key != "profile"})
    return resolved


def layout_profile_names() -> tuple[str, ...]:
    return tuple(sorted(PAGE_LAYOUT_PROFILES))
