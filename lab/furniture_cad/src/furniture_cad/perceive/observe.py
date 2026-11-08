"""Heuristic Perceive for casegoods (Phase 1) — LLM/vision wiring later."""

from __future__ import annotations

from typing import Any


def perceive_casegood(
    intake: dict[str, Any],
    *,
    class_hint: str = "casegood.console",
    known_mm: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Build a minimal observation.v1 from intake + known dims.

    Does not invent drawers/legs without evidence — marks unknowns for ask_user.
    """
    known_mm = known_mm or {}
    scale = intake.get("scale") or {}
    seg = intake.get("segmentation") or {}
    conf = float(seg.get("score") or 0.4)

    dims: dict[str, Any] = {}
    for key, label in (("w", "W"), ("d", "D"), ("h", "H")):
        if known_mm.get(key):
            dims[label] = {"v": float(known_mm[key]), "src": "user", "conf": 1.0}

    components = [
        {
            "id": "c_carcass",
            "type": "carcass",
            "count": 1,
            "conf": conf,
            "evidence": ["intake_mask"],
        }
    ]
    unknowns = [
        {"q": "Does this piece have drawers? How many?", "default": 0, "ask": True},
        {"q": "Leg style (square / tapered / none)?", "default": "unknown", "ask": True},
    ]

    views = [
        {
            "photo_id": intake.get("path") or "photo",
            "role": "front",
            "rectified": bool((intake.get("rectify") or {}).get("rectified")),
            "px_per_mm": (scale or {}).get("px_per_mm"),
            "scale_source": (scale or {}).get("scale_source") or "none",
        }
    ]

    return {
        "schema": "observation.v1",
        "class": class_hint,
        "views": views,
        "components": components,
        "dims_mm": dims,
        "unknowns": unknowns,
        "meta": {"perceive": "heuristic_v1", "seg_quality": seg.get("quality")},
    }
