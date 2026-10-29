"""Machine-readable registry of blocks and templates."""

from __future__ import annotations

from typing import Any, Callable

from furniture_cad.blocks import BLOCK_FNS

BLOCK_CATALOG: dict[str, dict[str, Any]] = {
    "tapered_leg": {
        "id": "tapered_leg",
        "tags": ["rectilinear", "chair", "stool"],
        "args": {
            "height": {"type": "number", "min": 1, "max": 2000, "unit": "mm"},
            "top_size": {"type": "number", "min": 1, "max": 200, "unit": "mm"},
            "bot_size": {"type": "number", "min": 1, "max": 200, "unit": "mm"},
            "section": {"type": "string", "enum": ["square", "round"], "default": "square"},
        },
    },
    "seat_panel": {
        "id": "seat_panel",
        "tags": ["rectilinear", "chair", "stool"],
        "args": {
            "width": {"type": "number", "min": 10, "max": 3000, "unit": "mm"},
            "depth": {"type": "number", "min": 10, "max": 3000, "unit": "mm"},
            "thickness": {"type": "number", "min": 1, "max": 200, "unit": "mm"},
        },
    },
    "rail": {
        "id": "rail",
        "tags": ["rectilinear", "chair", "stool"],
        "args": {
            "length": {"type": "number", "min": 1, "max": 5000, "unit": "mm"},
            "section_w": {"type": "number", "min": 1, "max": 200, "unit": "mm"},
            "section_h": {"type": "number", "min": 1, "max": 200, "unit": "mm"},
        },
    },
    "back_panel": {
        "id": "back_panel",
        "tags": ["rectilinear", "chair"],
        "args": {
            "width": {"type": "number", "min": 50, "max": 1200, "unit": "mm"},
            "height": {"type": "number", "min": 50, "max": 1200, "unit": "mm"},
            "thickness": {"type": "number", "min": 2, "max": 80, "unit": "mm"},
        },
    },
    "back_mid_slat": {
        "id": "back_mid_slat",
        "tags": ["rectilinear", "chair"],
        "args": {
            "width": {"type": "number", "min": 50, "max": 1200, "unit": "mm"},
            "height": {"type": "number", "min": 8, "max": 200, "unit": "mm"},
            "thickness": {"type": "number", "min": 4, "max": 80, "unit": "mm"},
        },
    },
    "winged_top_rail": {
        "id": "winged_top_rail",
        "tags": ["chair", "mcm"],
        "args": {
            "width": {"type": "number", "min": 80, "max": 1200, "unit": "mm"},
            "end_height": {"type": "number", "min": 20, "max": 250, "unit": "mm"},
            "mid_height": {"type": "number", "min": 10, "max": 250, "unit": "mm"},
            "thickness": {"type": "number", "min": 4, "max": 80, "unit": "mm"},
        },
    },
    "rounded_cushion": {
        "id": "rounded_cushion",
        "tags": ["soft", "chair"],
        "args": {
            "width": {"type": "number", "min": 50, "max": 1200, "unit": "mm"},
            "depth": {"type": "number", "min": 50, "max": 1200, "unit": "mm"},
            "height": {"type": "number", "min": 5, "max": 200, "unit": "mm"},
            "corner_radius": {"type": "number", "min": 0, "max": 200, "unit": "mm", "default": 25},
        },
    },
    "curved_stile": {
        "id": "curved_stile",
        "tags": ["chair", "mcm"],
        "args": {
            "height": {"type": "number", "min": 50, "max": 2000, "unit": "mm"},
            "section": {"type": "number", "min": 8, "max": 80, "unit": "mm"},
            "rake_y": {"type": "number", "min": -200, "max": 400, "unit": "mm"},
            "curve_y": {"type": "number", "min": -100, "max": 200, "unit": "mm", "default": 0},
        },
    },
}

TEMPLATE_CATALOG: dict[str, dict[str, Any]] = {
    "four_leg_chair": {
        "id": "four_leg_chair",
        "category": "chairs",
        "blocks": [
            "tapered_leg",
            "seat_panel",
            "rail",
            "back_panel",
            "back_mid_slat",
            "winged_top_rail",
            "rounded_cushion",
            "curved_stile",
        ],
        "description": "Four legs, one-piece or cushioned seat, flush side rails, panel or curved MCM back",
    },
    "stool": {
        "id": "stool",
        "category": "stools",
        "blocks": ["tapered_leg", "seat_panel", "rail"],
        "description": "Three- or four-leg stool with flat seat",
    },
}


def get_block(name: str) -> Callable[..., object]:
    if name not in BLOCK_FNS:
        raise KeyError(f"Unknown block {name!r}. Known: {sorted(BLOCK_FNS)}")
    return BLOCK_FNS[name]


def list_blocks() -> list[str]:
    return sorted(BLOCK_CATALOG)


def list_templates() -> list[str]:
    return sorted(TEMPLATE_CATALOG)
