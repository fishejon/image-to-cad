"""Left/right mask boundary → ordered line/arc segments (≤24)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def _boundary_polyline(mask: np.ndarray, *, side: str) -> np.ndarray:
    """Return Nx2 (x,y) polyline of the left or right mask silhouette over case height."""
    h, w = mask.shape
    pts: list[list[float]] = []
    rows = np.where(mask.any(axis=1))[0]
    if len(rows) == 0:
        return np.zeros((0, 2), dtype=np.float64)
    y0, y1 = int(rows.min()), int(rows.max())
    # Focus on case-height band (upper 65% of subject)
    split = y0 + int(0.65 * (y1 - y0))
    for y in range(y0, split + 1):
        xs = np.where(mask[y])[0]
        if len(xs) == 0:
            continue
        x = float(xs.min() if side == "left" else xs.max())
        pts.append([x, float(y)])
    return np.asarray(pts, dtype=np.float64)


def _douglas_peucker_px(pts: np.ndarray, epsilon_px: float) -> np.ndarray:
    import cv2

    if len(pts) < 3:
        return pts
    approx = cv2.approxPolyDP(pts.astype(np.float32).reshape(-1, 1, 2), epsilon_px, False)
    return approx.reshape(-1, 2).astype(np.float64)


def _fit_arc(pts: np.ndarray) -> dict[str, Any] | None:
    """RANSAC-ish circle fit; return arc if residual is better than a line."""
    if len(pts) < 5:
        return None
    best = None
    rng = np.random.default_rng(0)
    for _ in range(40):
        idx = rng.choice(len(pts), size=3, replace=False)
        a, b, c = pts[idx]
        circle = _circle_from_3(a, b, c)
        if circle is None:
            continue
        cx, cy, r = circle
        if r < 5 or r > 5000:
            continue
        d = np.abs(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) - r)
        inliers = d < 2.0
        n = int(inliers.sum())
        if best is None or n > best["n"]:
            best = {"cx": cx, "cy": cy, "r": r, "n": n, "rmse": float(d[inliers].mean()) if n else 999.0}
    if best is None or best["n"] < max(5, len(pts) // 3):
        return None
    return best


def _circle_from_3(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> tuple[float, float, float] | None:
    ax, ay = a
    bx, by = b
    cx, cy = c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-6:
        return None
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
    r = math.hypot(ax - ux, ay - uy)
    return float(ux), float(uy), float(r)


def end_outline_segments(
    mask: np.ndarray,
    *,
    px_per_mm: float,
    epsilon_mm: float = 1.5,
    max_segments: int = 24,
) -> dict[str, Any]:
    """Simplify left and right boundaries into ≤24 line/arc segments in mm."""
    eps_px = max(1.0, epsilon_mm * px_per_mm)
    sides: dict[str, Any] = {}
    all_segs: list[dict[str, Any]] = []
    for side in ("left", "right"):
        poly = _boundary_polyline(mask, side=side)
        if len(poly) < 2:
            continue
        simp = _douglas_peucker_px(poly, eps_px)
        # Try one arc on the middle third; otherwise emit polyline as lines
        mid = simp[len(simp) // 4 : 3 * len(simp) // 4] if len(simp) >= 6 else simp
        arc = _fit_arc(mid)
        segs: list[dict[str, Any]] = []
        if arc and arc["rmse"] < 2.0:
            segs.append(
                {
                    "type": "arc",
                    "side": side,
                    "points_mm": [
                        [round(float(simp[0, 0] / px_per_mm), 2), round(float(simp[0, 1] / px_per_mm), 2)],
                        [round(float(simp[-1, 0] / px_per_mm), 2), round(float(simp[-1, 1] / px_per_mm), 2)],
                    ],
                    "r_mm": round(arc["r"] / px_per_mm, 2),
                    "center_mm": [round(arc["cx"] / px_per_mm, 2), round(arc["cy"] / px_per_mm, 2)],
                }
            )
        else:
            for i in range(len(simp) - 1):
                segs.append(
                    {
                        "type": "line",
                        "side": side,
                        "points_mm": [
                            [round(float(simp[i, 0] / px_per_mm), 2), round(float(simp[i, 1] / px_per_mm), 2)],
                            [
                                round(float(simp[i + 1, 0] / px_per_mm), 2),
                                round(float(simp[i + 1, 1] / px_per_mm), 2),
                            ],
                        ],
                        "r_mm": None,
                    }
                )
        sides[side] = segs
        all_segs.extend(segs)

    # Cap total segments
    if len(all_segs) > max_segments:
        all_segs = all_segs[:max_segments]
    return {
        "side": "both" if len(sides) == 2 else next(iter(sides), "left"),
        "segments": all_segs,
        "source": "cv",
        "n": len(all_segs),
    }
