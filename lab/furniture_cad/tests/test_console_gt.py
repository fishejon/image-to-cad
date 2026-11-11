"""console_01 GT scoring: STEP dims + hand cut list wiring."""

from __future__ import annotations

from furniture_cad.eval.console_gt import (
    load_hand_cut_list,
    score_gt_ceiling,
    score_ir_stub,
    step_bbox_mm,
    truth_parts_from_hand,
)


def test_hand_list_and_step_bbox() -> None:
    hand = load_hand_cut_list()
    assert hand["id"] == "console_01"
    parts = truth_parts_from_hand(hand)
    assert len(parts) >= 12
    assert sum(p["qty"] for p in parts) >= 30
    bb = step_bbox_mm()
    assert abs(bb["h"] - 762.0) < 1.0
    assert abs(bb["d"] - 304.8) < 1.0
    assert abs(bb["w"] - 1193.8) < 5.0  # STEP ~1191.7


def test_ceiling_and_ir_stub_score() -> None:
    ceiling = score_gt_ceiling(measure_iou=False)
    assert ceiling["overall_dims_within_3pct"] is True
    stub = score_ir_stub()
    assert stub["schema"] == "furniture_cad.score_run.v1"
    # Box IR will not match carved cut list — recall should be incomplete
    assert stub["parts"]["recall"] < 1.0
