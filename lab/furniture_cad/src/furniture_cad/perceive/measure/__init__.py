"""Measure stage — geometry from rectified intake (no model lengths)."""

from __future__ import annotations

from typing import Any

import numpy as np

from furniture_cad.perceive.measure.edges import extract_segments
from furniture_cad.perceive.measure.end_outline import end_outline_segments
from furniture_cad.perceive.measure.labels import (
    heuristic_labels,
    label_regions_with_model,
    render_set_of_marks,
)
from furniture_cad.perceive.measure.profile import width_profile
from furniture_cad.perceive.measure.regions import candidate_regions

MAX_ASKS = 3


def measure_from_intake(
    intake: dict[str, Any],
    *,
    class_hint: str = "casegood",
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Run Measure on an intake.v2 result → observation.v2."""
    image = intake.get("image")
    mask = intake.get("mask")
    if image is None or mask is None:
        raise ValueError("measure_requires_intake_image_and_mask")
    mask_arr = np.asarray(mask, dtype=bool)
    scale = intake.get("scale") or {}
    ppm = scale.get("px_per_mm")
    if not ppm or float(ppm) <= 0:
        return {
            "schema": "observation.v2",
            "class": class_hint,
            "counts": {},
            "regions": [],
            "measurements": [],
            "asks": [
                {
                    "key": "w",
                    "prompt": "Need a known overall width (or ArUco marker) before measuring the photo.",
                    "choices": [],
                }
            ],
            "meta": {"measure": "blocked_no_scale", "intake_schema": intake.get("schema")},
        }
    ppm = float(ppm)
    size = tuple(getattr(image, "size", (mask_arr.shape[1], mask_arr.shape[0])))

    edges = extract_segments(image, mask_arr)
    regions = candidate_regions(edges["lines"], image_size=size)
    profile = width_profile(mask_arr)
    marked = render_set_of_marks(image, regions)

    labeled = None
    if api_key:
        labeled = label_regions_with_model(
            marked, regions, api_key=api_key, model=model or "claude-haiku-4-5-20251001"
        )
    if labeled is None:
        labeled = heuristic_labels(regions, image_size=size, profile=profile)

    measurements, asks = _measurements_from_geometry(
        labeled, profile=profile, ppm=ppm, size=size
    )
    outline = end_outline_segments(mask_arr, px_per_mm=ppm)

    counts: dict[str, int] = {}
    for r in labeled:
        lab = r.get("label") or "none"
        if lab == "none":
            continue
        key = {
            "drawer_front": "drawer",
            "door": "door",
            "open_bay": "open_cubby",
            "shelf": "shelf",
            "leg": "leg",
            "pull": "pull",
            "end_block": "end_block_carved",
        }.get(lab)
        if key:
            counts[key] = counts.get(key, 0) + 1

    return {
        "schema": "observation.v2",
        "class": class_hint,
        "counts": counts,
        "regions": [
            {
                "id": int(r["id"]),
                "label": r["label"],
                "bbox_px": r["bbox_px"],
                "conf": float(r.get("conf") or 0),
                "label_source": r.get("label_source") or "heuristic",
            }
            for r in labeled
        ],
        "measurements": measurements,
        "end_outline": outline,
        "asks": asks[:MAX_ASKS],
        "meta": {
            "measure": "cv",
            "px_per_mm": ppm,
            "scale_source": scale.get("scale_source"),
            "n_lines": len(edges["lines"]),
            "n_regions": len(labeled),
            "label_mode": "model" if api_key and any(r.get("label_source") == "model" for r in labeled) else "heuristic",
            "intake_schema": intake.get("schema"),
        },
    }


def _measurements_from_geometry(
    regions: list[dict[str, Any]],
    *,
    profile: dict[str, Any],
    ppm: float,
    size: tuple[int, int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    measurements: list[dict[str, Any]] = []
    asks: list[dict[str, Any]] = []
    err_base = max(0.5, 2.0 / ppm)  # ~2 px

    def add(mid: str, kind: str, value_px: float, *, conf: float, region_id: int | None = None) -> None:
        measurements.append(
            {
                "id": mid,
                "kind": kind,
                "value_mm": round(value_px / ppm, 3),
                "err_mm": round(err_base, 3),
                "source": "cv",
                "conf": round(conf, 3),
                "region_id": region_id,
            }
        )

    # Profile-derived
    if profile.get("case_bottom_row") is not None:
        add("case_bottom_row", "case_bottom_y", float(profile["case_bottom_row"]), conf=0.75)
    if profile.get("top_band_px"):
        add("top_t", "top_thickness", float(profile["top_band_px"]), conf=0.55)
    if profile.get("leg_top_width_px"):
        add("leg_w_top", "leg_width_top", float(profile["leg_top_width_px"]), conf=0.6)
    if profile.get("leg_foot_width_px"):
        add("leg_w_foot", "leg_width_foot", float(profile["leg_foot_width_px"]), conf=0.6)
    if profile.get("overhang_px"):
        add("overhang", "top_overhang", float(profile["overhang_px"]), conf=0.5)
    if profile.get("body_width_px"):
        add("body_w", "body_width", float(profile["body_width_px"]), conf=0.7)

    # Region-derived drawer / door sizes
    drawers = [r for r in regions if r.get("label") == "drawer_front"]
    for i, r in enumerate(drawers):
        x0, y0, x1, y1 = r["bbox_px"]
        conf = float(r.get("conf") or 0.5)
        add(f"df{i}_w", "drawer_front_w", x1 - x0, conf=conf, region_id=int(r["id"]))
        add(f"df{i}_h", "drawer_front_h", y1 - y0, conf=conf, region_id=int(r["id"]))
        if conf < 0.6 and len(asks) < MAX_ASKS:
            asks.append(
                {
                    "key": f"region_{r['id']}_label",
                    "prompt": f"Is overlay #{r['id']} a drawer front or something else?",
                    "choices": ["drawer_front", "none"],
                }
            )

    doors = [r for r in regions if r.get("label") == "door"]
    for i, r in enumerate(doors):
        x0, y0, x1, y1 = r["bbox_px"]
        add(f"dr{i}_w", "door_w", x1 - x0, conf=float(r.get("conf") or 0.5), region_id=int(r["id"]))
        add(f"dr{i}_h", "door_h", y1 - y0, conf=float(r.get("conf") or 0.5), region_id=int(r["id"]))

    return measurements, asks
