"""Phase 3 decision gate — chairs only if Phase 2 metrics hold."""

from __future__ import annotations

from typing import Any

# Locked policy from product plan
CHAIR_IOU_SHIP_THRESHOLD = 0.55
APPROXIMATE_LABEL = "approximate"


def chair_ship_decision(*, phase2_blind_passed: bool, chair_mean_iou: float | None) -> dict[str, Any]:
    """
    Returns ship mode for chairs.

    - defer: Phase 2 bar not met
    - approximate: Phase 2 ok but chair IoU < threshold — label explicitly
    - full: Phase 2 ok and chair IoU >= threshold
    """
    if not phase2_blind_passed:
        return {
            "mode": "defer",
            "reason": "Phase 2 blind bar not met — do not expand chairs",
            "label": None,
        }
    if chair_mean_iou is None:
        return {
            "mode": "approximate",
            "reason": "No chair IoU yet — ship as approximate when exposed",
            "label": APPROXIMATE_LABEL,
        }
    if chair_mean_iou < CHAIR_IOU_SHIP_THRESHOLD:
        return {
            "mode": "approximate",
            "reason": f"chair mean IoU {chair_mean_iou:.3f} < {CHAIR_IOU_SHIP_THRESHOLD}",
            "label": APPROXIMATE_LABEL,
        }
    return {"mode": "full", "reason": "chair IoU meets threshold", "label": None}
