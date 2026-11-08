"""Solid-backed geometry checks for R1 (bbox, overlaps, IoU helpers)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def bbox_mm_from_solid(solid: object) -> dict[str, float]:
    """Axis-aligned size in mm from a build123d solid / compound."""
    bb = solid.bounding_box()  # type: ignore[attr-defined]
    # build123d BoundingBox: .size is Vector
    size = bb.size
    dims = sorted([float(size.X), float(size.Y), float(size.Z)], reverse=True)
    # Map largest→h for furniture convention when ambiguous; prefer explicit axes
    return {
        "w": float(size.X),
        "d": float(size.Y),
        "h": float(size.Z),
        "sorted_desc": dims,
        "min": [float(bb.min.X), float(bb.min.Y), float(bb.min.Z)],
        "max": [float(bb.max.X), float(bb.max.Y), float(bb.max.Z)],
    }


def bbox_mm_from_stl(stl_path: Path | str) -> dict[str, float]:
    import trimesh

    mesh = trimesh.load_mesh(str(stl_path), force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(g for g in mesh.geometry.values()))
    bounds = mesh.bounds  # (2, 3)
    extents = bounds[1] - bounds[0]
    return {
        "w": float(extents[0]),
        "d": float(extents[1]),
        "h": float(extents[2]),
        "sorted_desc": sorted(map(float, extents), reverse=True),
        "min": [float(x) for x in bounds[0]],
        "max": [float(x) for x in bounds[1]],
    }


def boxes_overlap(
    a_min: tuple[float, float, float],
    a_max: tuple[float, float, float],
    b_min: tuple[float, float, float],
    b_max: tuple[float, float, float],
) -> bool:
    """True if two AABBs overlap (inclusive faces count as overlap)."""
    for i in range(3):
        if a_max[i] < b_min[i] or b_max[i] < a_min[i]:
            return False
    return True


def solids_bbox_overlap(a: object, b: object) -> bool:
    ba = bbox_mm_from_solid(a)
    bb = bbox_mm_from_solid(b)
    return boxes_overlap(
        (ba["min"][0], ba["min"][1], ba["min"][2]),
        (ba["max"][0], ba["max"][1], ba["max"][2]),
        (bb["min"][0], bb["min"][1], bb["min"][2]),
        (bb["max"][0], bb["max"][1], bb["max"][2]),
    )


def within_pct(got: float, want: float, pct: float = 0.05) -> bool:
    if want <= 0:
        return True
    return abs(got - want) / want <= pct


def compare_targets(bbox: dict[str, float], targets: dict[str, float], *, tol: float = 0.05) -> dict[str, Any]:
    issues: list[str] = []
    detail: dict[str, Any] = {}
    for key in ("w", "d", "h"):
        if key not in targets or not targets[key]:
            continue
        got = float(bbox.get(key) or 0)
        want = float(targets[key])
        err = abs(got - want) / want if want else 0.0
        detail[key] = {"got": round(got, 2), "want": want, "err": round(err, 4)}
        if err > tol:
            issues.append(f"{key}: got {got:.1f} want {want:.1f} ({err:.1%} > {tol:.0%})")
    return {"within_5pct": len(issues) == 0 if targets else None, "issues": issues, "detail": detail}
