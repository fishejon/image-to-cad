"""Phase 3: curve blocks, laminate blanks, chair assembly, ship gate."""

from __future__ import annotations

from furniture_cad.construct.blocks.curves import CURVE_BLOCKS, chair_side_assembly, laminate_blank
from furniture_cad.construct.phase3_gate import chair_ship_decision
from furniture_cad.geom_check import bbox_mm_from_solid


def test_curve_blocks_and_laminate() -> None:
    assert {"sweep_rail", "laminate_blank", "spline_stile", "chair_side_assembly"} <= set(CURVE_BLOCKS)
    lam = laminate_blank(finished_t=20, finished_w=80, finished_l=600, plies=5)
    assert lam["meta"]["plies"] == 5
    assert lam["parts"][0].blank_length_mm > 600
    chair = chair_side_assembly()
    bb = bbox_mm_from_solid(chair["assembly"])
    assert bb["h"] > 450
    assert chair["meta"]["label"] == "approximate"
    assert sum(p.qty for p in chair["parts"]) >= 7


def test_phase3_gate() -> None:
    assert chair_ship_decision(phase2_blind_passed=False, chair_mean_iou=0.7)["mode"] == "defer"
    assert chair_ship_decision(phase2_blind_passed=True, chair_mean_iou=0.4)["mode"] == "approximate"
    assert chair_ship_decision(phase2_blind_passed=True, chair_mean_iou=0.6)["mode"] == "full"
