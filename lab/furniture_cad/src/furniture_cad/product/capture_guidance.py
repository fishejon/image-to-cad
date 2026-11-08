"""Capture guidance (D3) — straight-on + scale / known dimension."""

from __future__ import annotations

from typing import Any


def capture_checklist(*, piece_class: str = "casegood") -> dict[str, Any]:
    views = [
        {"role": "front", "required": True, "hint": "Straight-on, lens near eye height of piece center"},
        {"role": "three_quarter", "required": False, "hint": "45° for depth / legs"},
        {"role": "side", "required": False, "hint": "If depth is ambiguous"},
    ]
    if piece_class.startswith("chair"):
        views.append({"role": "detail", "required": False, "hint": "Joinery / curved back detail"})
    return {
        "schema": "capture_guidance.v1",
        "piece_class": piece_class,
        "require_known_dim": True,
        "known_dim_prompt": "Enter one overall dimension in inches or mm (width preferred).",
        "views": views,
        "tips": [
            "Avoid extreme wide-angle distortion",
            "Include a clear floor line under the piece",
            "Prefer even lighting; no heavy backlight silhouette only",
        ],
    }
