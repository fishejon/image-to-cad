"""Mask width profile → leg band, case bottom, top thickness cues."""

from __future__ import annotations

from typing import Any

import numpy as np


def width_profile(mask: np.ndarray) -> dict[str, Any]:
    """Per-row subject width and derived structural rows."""
    h, w = mask.shape
    widths = mask.sum(axis=1).astype(np.float64)
    # Smooth lightly
    if h >= 5:
        kernel = np.ones(5) / 5.0
        widths = np.convolve(widths, kernel, mode="same")

    # Case body: rows where width is near the max (above 70% of peak)
    peak = float(widths.max()) if widths.max() > 0 else 1.0
    body = widths >= 0.70 * peak
    body_idx = np.where(body)[0]
    if len(body_idx) == 0:
        return {
            "widths": widths.tolist(),
            "case_bottom_row": None,
            "case_top_row": None,
            "leg_top_width_px": None,
            "leg_foot_width_px": None,
            "top_band_px": None,
            "overhang_px": None,
        }

    case_top = int(body_idx.min())
    case_bottom = int(body_idx.max())

    # Largest jump in width looking upward from the foot → case underside
    jump_row = case_bottom
    best_jump = 0.0
    for r in range(h - 2, max(0, int(h * 0.2)), -1):
        jump = float(widths[r] - widths[min(h - 1, r + 3)])
        if jump > best_jump:
            best_jump = jump
            jump_row = r

    # Legs: rows below case bottom
    leg_rows = list(range(min(h - 1, case_bottom + 1), h))
    foot_w = float(np.median(widths[leg_rows[-max(1, len(leg_rows) // 5) :]])) if leg_rows else None
    top_leg_w = float(np.median(widths[leg_rows[: max(1, len(leg_rows) // 5)]])) if leg_rows else None

    # Top thickness: topmost band wider than body by overhang
    body_w = float(np.median(widths[body_idx])) if len(body_idx) else peak
    top_band = 0
    for r in range(0, max(1, case_top + 1)):
        if widths[r] >= body_w * 0.95:
            top_band += 1
        elif top_band > 0:
            break
    overhang = float(max(0.0, peak - body_w) / 2.0)

    return {
        "widths": [round(float(x), 2) for x in widths.tolist()],
        "case_bottom_row": int(jump_row),
        "case_top_row": case_top,
        "leg_top_width_px": None if top_leg_w is None else round(top_leg_w, 2),
        "leg_foot_width_px": None if foot_w is None else round(foot_w, 2),
        "top_band_px": top_band,
        "overhang_px": round(overhang, 2),
        "body_width_px": round(body_w, 2),
    }
