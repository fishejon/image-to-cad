"""Candidate panel rectangles from clustered H/V lines."""

from __future__ import annotations

from typing import Any


def candidate_regions(
    lines: list[dict[str, Any]],
    *,
    image_size: tuple[int, int],
    min_area_frac: float = 0.005,
) -> list[dict[str, Any]]:
    """Build closed rectangles from horizontal and vertical line clusters.

    ``image_size`` is (width, height). Area must exceed ``min_area_frac`` of the image.
    """
    w, h = image_size
    img_area = max(1.0, float(w * h))
    horiz = sorted([ln for ln in lines if ln.get("orient") == "h"], key=lambda L: L["y"])
    vert = sorted([ln for ln in lines if ln.get("orient") == "v"], key=lambda L: L["x"])
    # Always include image/mask bounds as rails
    ys = [0.0] + [float(L["y"]) for L in horiz] + [float(h - 1)]
    xs = [0.0] + [float(L["x"]) for L in vert] + [float(w - 1)]
    # Dedup close lines
    ys = _dedup_sorted(ys, 4.0)
    xs = _dedup_sorted(xs, 4.0)

    regions: list[dict[str, Any]] = []
    rid = 1
    for i in range(len(ys) - 1):
        for j in range(len(xs) - 1):
            y0, y1 = ys[i], ys[i + 1]
            x0, x1 = xs[j], xs[j + 1]
            bw, bh = x1 - x0, y1 - y0
            if bw < 8 or bh < 8:
                continue
            area = bw * bh
            if area / img_area < min_area_frac:
                continue
            regions.append(
                {
                    "id": rid,
                    "bbox_px": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                    "area_px": round(area, 1),
                    "cx": round((x0 + x1) / 2, 1),
                    "cy": round((y0 + y1) / 2, 1),
                }
            )
            rid += 1
    # Cap to keep set-of-marks readable
    regions.sort(key=lambda r: -r["area_px"])
    return regions[:24]


def _dedup_sorted(vals: list[float], tol: float) -> list[float]:
    out: list[float] = []
    for v in vals:
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out
