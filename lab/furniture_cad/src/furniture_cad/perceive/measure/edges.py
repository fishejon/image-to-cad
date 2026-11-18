"""Edge and line extraction on a rectified masked image."""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def _auto_canny(gray: np.ndarray) -> np.ndarray:
    import cv2

    v = float(np.median(gray))
    lo = int(max(0, 0.66 * v))
    hi = int(min(255, 1.33 * v))
    return cv2.Canny(gray, lo, hi)


def extract_segments(
    image: Any,
    mask: np.ndarray | None = None,
    *,
    snap_deg: float = 3.0,
) -> dict[str, Any]:
    """Canny + LSD (or Hough), snap near-H/V, cluster collinear segments."""
    import cv2
    from PIL import Image

    if hasattr(image, "convert"):
        arr = np.asarray(image.convert("RGB"))
    else:
        arr = np.asarray(image)
        if arr.ndim == 2:
            arr = np.stack([arr] * 3, axis=-1)
    # Downsample large studio photos for LSD speed (coords stay in this working space)
    max_side = 900
    h0, w0 = arr.shape[:2]
    scale = 1.0
    if max(h0, w0) > max_side:
        scale = max_side / float(max(h0, w0))
        arr = cv2.resize(arr, (int(w0 * scale), int(h0 * scale)), interpolation=cv2.INTER_AREA)
        if mask is not None:
            mask = cv2.resize(
                mask.astype(np.uint8),
                (arr.shape[1], arr.shape[0]),
                interpolation=cv2.INTER_NEAREST,
            ).astype(bool)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    if mask is not None:
        gray = cv2.bitwise_and(gray, gray, mask=(mask.astype(np.uint8) * 255))
    edges = _auto_canny(gray)

    raw: list[tuple[float, float, float, float]] = []
    try:
        lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
        lines, *_ = lsd.detect(gray)
        if lines is not None:
            for ln in lines:
                x0, y0, x1, y1 = map(float, ln.reshape(-1)[:4])
                raw.append((x0, y0, x1, y1))
    except Exception:
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 50, minLineLength=30, maxLineGap=8)
        if lines is not None:
            for ln in lines:
                x0, y0, x1, y1 = map(float, ln.reshape(-1)[:4])
                raw.append((x0, y0, x1, y1))

    snapped: list[dict[str, Any]] = []
    for x0, y0, x1, y1 in raw:
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180.0
        length = math.hypot(x1 - x0, y1 - y0)
        if length < 15:
            continue
        orient = "diag"
        if min(abs(ang - 0), abs(ang - 180)) <= snap_deg:
            orient = "h"
            # Snap to horizontal
            y = (y0 + y1) / 2
            y0 = y1 = y
        elif abs(ang - 90) <= snap_deg:
            orient = "v"
            x = (x0 + x1) / 2
            x0 = x1 = x
        # Map back to original image coordinates when downsampled
        if scale != 1.0:
            x0, y0, x1, y1 = x0 / scale, y0 / scale, x1 / scale, y1 / scale
            length = length / scale
        snapped.append(
            {
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1,
                "orient": orient,
                "length": length,
                "angle_deg": ang,
            }
        )

    # Cluster collinear within 2 px
    clusters = _cluster_collinear(snapped, tol_px=2.0)
    return {
        "segments": snapped,
        "lines": clusters,
        "edge_map": edges,
        "n_raw": len(raw),
        "n_snapped": len(snapped),
    }


def _cluster_collinear(segs: list[dict[str, Any]], *, tol_px: float) -> list[dict[str, Any]]:
    used = [False] * len(segs)
    lines: list[dict[str, Any]] = []
    for i, s in enumerate(segs):
        if used[i] or s["orient"] == "diag":
            continue
        group = [s]
        used[i] = True
        for j in range(i + 1, len(segs)):
            if used[j] or segs[j]["orient"] != s["orient"]:
                continue
            if s["orient"] == "h":
                if abs(segs[j]["y0"] - s["y0"]) <= tol_px:
                    used[j] = True
                    group.append(segs[j])
            else:
                if abs(segs[j]["x0"] - s["x0"]) <= tol_px:
                    used[j] = True
                    group.append(segs[j])
        if s["orient"] == "h":
            xs = [g["x0"] for g in group] + [g["x1"] for g in group]
            y = float(np.mean([g["y0"] for g in group]))
            lines.append(
                {
                    "orient": "h",
                    "y": y,
                    "x0": float(min(xs)),
                    "x1": float(max(xs)),
                    "n": len(group),
                }
            )
        else:
            ys = [g["y0"] for g in group] + [g["y1"] for g in group]
            x = float(np.mean([g["x0"] for g in group]))
            lines.append(
                {
                    "orient": "v",
                    "x": x,
                    "y0": float(min(ys)),
                    "y1": float(max(ys)),
                    "n": len(group),
                }
            )
    return lines
