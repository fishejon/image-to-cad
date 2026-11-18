"""High-resolution detail crops for Perceive v2 attribute labeling."""

from __future__ import annotations

from typing import Any

import numpy as np

# Max crops per run (spec WP3)
MAX_CROPS = 8

CROP_ROLES = (
    "drawer_corner",
    "pull",
    "leg_foot",
    "leg_apron",
    "top_edge",
    "end_block",
    "joint",
    "overview",
)


def _clip_box(x0: float, y0: float, x1: float, y1: float, w: int, h: int) -> tuple[int, int, int, int]:
    return (
        max(0, int(x0)),
        max(0, int(y0)),
        min(w, int(x1)),
        min(h, int(y1)),
    )


def generate_detail_crops(
    image: Any,
    *,
    regions: list[dict[str, Any]] | None = None,
    mask: np.ndarray | None = None,
    max_crops: int = MAX_CROPS,
) -> list[dict[str, Any]]:
    """Return up to ``max_crops`` detail crops with role + bbox_px + PIL image."""
    from PIL import Image

    if hasattr(image, "convert"):
        img = image.convert("RGB")
    else:
        img = Image.fromarray(np.asarray(image)).convert("RGB")
    w, h = img.size
    crops: list[dict[str, Any]] = []

    def add(role: str, box: tuple[int, int, int, int], conf: float = 0.6) -> None:
        if len(crops) >= max_crops:
            return
        x0, y0, x1, y1 = box
        if x1 - x0 < 16 or y1 - y0 < 16:
            return
        crops.append(
            {
                "role": role,
                "bbox_px": [x0, y0, x1, y1],
                "conf": conf,
                "image": img.crop((x0, y0, x1, y1)),
            }
        )

    regions = regions or []
    # Region-driven crops
    for r in regions:
        lab = str(r.get("label") or "")
        x0, y0, x1, y1 = r.get("bbox_px") or [0, 0, 0, 0]
        if lab == "drawer_front":
            # Corner of drawer
            add("drawer_corner", _clip_box(x0, y0, x0 + (x1 - x0) * 0.35, y0 + (y1 - y0) * 0.55, w, h))
        elif lab == "pull":
            add("pull", _clip_box(x0 - 10, y0 - 10, x1 + 10, y1 + 10, w, h))
        elif lab == "leg":
            add("leg_foot", _clip_box(x0, y1 - (y1 - y0) * 0.35, x1, y1, w, h))
            add("leg_apron", _clip_box(x0, y0, x1, y0 + (y1 - y0) * 0.4, w, h))
        elif lab == "end_block":
            add("end_block", _clip_box(x0, y0, x1, y1, w, h))
        elif lab == "top":
            add("top_edge", _clip_box(x0, y0, x1, min(h, y0 + max(20, (y1 - y0))), w, h))

    # Mask-driven fallbacks when regions are sparse
    if mask is not None and len(crops) < max_crops:
        ys, xs = np.where(mask)
        if len(xs):
            x_lo, x_hi = int(xs.min()), int(xs.max())
            y_lo, y_hi = int(ys.min()), int(ys.max())
            add("top_edge", _clip_box(x_lo, y_lo, x_hi, y_lo + max(24, (y_hi - y_lo) * 0.08), w, h), 0.5)
            add("leg_foot", _clip_box(x_lo, y_hi - max(40, (y_hi - y_lo) * 0.2), x_lo + (x_hi - x_lo) * 0.25, y_hi, w, h), 0.5)
            add("end_block", _clip_box(x_lo, y_lo + (y_hi - y_lo) * 0.2, x_lo + (x_hi - x_lo) * 0.18, y_hi - (y_hi - y_lo) * 0.2, w, h), 0.45)
            add("overview", _clip_box(x_lo, y_lo, x_hi, y_hi, w, h), 0.4)

    if not crops:
        add("overview", (0, 0, w, h), 0.3)
    return crops[:max_crops]
