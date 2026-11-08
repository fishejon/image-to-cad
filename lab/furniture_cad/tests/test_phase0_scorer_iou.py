"""Phase 0: fixed-scale IoU + part scorer."""

from __future__ import annotations

import numpy as np

from furniture_cad.eval.scorer import feature_recall, score_parts, score_run
from furniture_cad.silhouette import _fixed_scale_iou, _aligned_iou_legacy_scale_search


def test_fixed_scale_no_scale_search() -> None:
    ref = np.zeros((100, 100), dtype=bool)
    ref[20:80, 30:70] = True
    model = np.zeros((100, 100), dtype=bool)
    model[22:82, 32:72] = True  # small shift
    iou, meta = _fixed_scale_iou(ref, model, scale=1.0, max_shift_frac=0.05)
    assert meta["scale"] == 1.0
    assert iou > 0.7


def test_legacy_scale_search_still_available() -> None:
    ref = np.zeros((80, 80), dtype=bool)
    ref[10:70, 20:60] = True
    model = np.zeros((80, 80), dtype=bool)
    model[20:50, 25:55] = True  # smaller blob
    iou_leg, meta_leg = _aligned_iou_legacy_scale_search(ref, model)
    iou_fix, meta_fix = _fixed_scale_iou(ref, model, scale=1.0)
    assert "scale" in meta_leg
    assert meta_fix["scale"] == 1.0
    # Legacy may invent a better score via scale — that is why we retired it for product
    assert iou_leg >= iou_fix - 1e-9


def test_score_parts_exact_qty_and_size() -> None:
    truth = [
        {"id": "post", "type": "post", "qty": 4, "thickness_mm": 40, "width_mm": 40, "length_mm": 1700},
        {"id": "shelf", "type": "shelf", "qty": 5, "thickness_mm": 18, "width_mm": 300, "length_mm": 1200},
    ]
    pred = [
        {"id": "post", "type": "post", "qty": 4, "thickness_mm": 40, "width_mm": 40, "length_mm": 1700},
        {"id": "shelf", "type": "shelf", "qty": 5, "thickness_mm": 18, "width_mm": 300, "length_mm": 1200},
    ]
    s = score_parts(pred, truth)
    assert s["precision"] == 1.0 and s["recall"] == 1.0
    assert s["cut_list_match_share"] == 1.0


def test_feature_recall_and_score_run() -> None:
    fr = feature_recall({"drawer": 2, "shelf": 1}, {"drawer": 2, "shelf": 1, "leg": 4})
    assert fr["per_feature"]["drawer"]["ok"] is True
    assert fr["per_feature"]["leg"]["ok"] is False
    run = score_run(
        predicted_parts=[{"id": "a", "qty": 1, "thickness_mm": 19, "width_mm": 300, "length_mm": 900}],
        truth_parts=[{"id": "a", "qty": 1, "thickness_mm": 19, "width_mm": 300, "length_mm": 900}],
        overall_pred_mm={"w": 1194, "d": 305, "h": 762},
        overall_truth_mm={"w": 1194, "d": 305, "h": 762},
    )
    assert run["overall_dims_within_3pct"] is True
