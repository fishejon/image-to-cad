"""Metric scale from ArUco marker or known overall dimension vs mask extent."""

from __future__ import annotations

from typing import Any

import numpy as np


def _mask_extent_px(mask: np.ndarray, axis: str) -> tuple[float, float]:
    """Return (extent_px, boundary_uncertainty_px) along width (w) or height (h)."""
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return 0.0, 1.0
    if axis == "h":
        lo, hi = float(ys.min()), float(ys.max())
    else:
        lo, hi = float(xs.min()), float(xs.max())
    extent = max(1.0, hi - lo + 1.0)
    # Boundary uncertainty ~1–2 px per side for crisp masks
    unc = 2.0
    return extent, unc


def _aruco_side_px(corners: list[list[float]] | np.ndarray) -> float:
    pts = np.asarray(corners, dtype=np.float64).reshape(4, 2)
    # Average of the four side lengths
    lens = [float(np.linalg.norm(pts[(i + 1) % 4] - pts[i])) for i in range(4)]
    return float(sum(lens) / 4.0)


def compute_scale(
    *,
    mask: np.ndarray | None,
    known_mm: dict[str, float] | None = None,
    aruco: dict[str, Any] | None = None,
    image_size: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Scale priority: ArUco → user known dim on mask extent → ask.

    Never invents a fill-fraction guess as a trusted source (tagged ``guessed`` only
    as a last-ditch diagnostic, with an ask).
    """
    known_mm = known_mm or {}
    asks: list[dict[str, str]] = []

    # 1) ArUco
    if aruco and aruco.get("found") and aruco.get("corners_px") and aruco.get("size_mm"):
        side_px = _aruco_side_px(aruco["corners_px"])
        size_mm = float(aruco["size_mm"])
        if side_px > 1.0 and size_mm > 0:
            ppm = side_px / size_mm
            rel = 2.0 / side_px  # ~2 px corner uncertainty
            return {
                "px_per_mm": round(ppm, 6),
                "scale_source": "aruco",
                "source_tag": "cv",
                "confidence": round(float(max(0.5, min(0.99, 1.0 - rel * 5))), 3),
                "rel_error_est": round(rel, 4),
                "axis": "marker",
                "extent_px": round(side_px, 2),
                "known_mm": size_mm,
                "note": f"ArUco id={aruco.get('id')} {size_mm} mm",
                "asks": asks,
            }

    # 2) Known overall dimension vs mask extent
    axis = None
    known_v = None
    for key in ("w", "d", "h"):
        if known_mm.get(key):
            axis = key
            known_v = float(known_mm[key])
            break
    if axis and known_v and mask is not None and mask.any():
        # Prefer width for front-on; height if only H known
        use_axis = "h" if axis == "h" else "w"
        extent, unc = _mask_extent_px(mask, use_axis)
        if extent > 1.0:
            ppm = extent / known_v
            rel = unc / extent
            return {
                "px_per_mm": round(ppm, 6),
                "scale_source": "user",
                "source_tag": "user",
                "confidence": round(float(max(0.4, min(0.95, 1.0 - rel * 8))), 3),
                "rel_error_est": round(rel, 4),
                "axis": use_axis,
                "extent_px": round(extent, 2),
                "known_mm": known_v,
                "note": f"mask {use_axis}-extent / known {axis}={known_v} mm",
                "asks": asks,
            }

    # 3) Ask — do not invent fill-fraction as trusted scale
    asks.append(
        {
            "key": "w",
            "prompt": "Enter one overall dimension (width preferred) in mm so we can scale the photo.",
        }
    )
    # Diagnostic fill-fraction only if we have image size — tagged guessed, low conf
    if image_size and known_v:
        ppm = (image_size[0] * 0.70) / known_v
        return {
            "px_per_mm": round(ppm, 6),
            "scale_source": "guessed",
            "source_tag": "guessed",
            "confidence": 0.2,
            "rel_error_est": 0.3,
            "axis": "w",
            "extent_px": None,
            "known_mm": known_v,
            "note": "fill-fraction fallback — not trusted; answer the ask",
            "asks": asks,
        }

    return {
        "px_per_mm": None,
        "scale_source": "ask",
        "source_tag": "guessed",
        "confidence": 0.0,
        "rel_error_est": None,
        "axis": "w",
        "extent_px": None,
        "known_mm": None,
        "note": "no scale available",
        "asks": asks,
    }
