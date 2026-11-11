"""P1: console IR v2 compiles; golden checks vs STEP bbox + hand cut list."""

from __future__ import annotations

from pathlib import Path

from furniture_cad.construct import compile_ir, load_ir
from furniture_cad.construct.validate_ir import validate_ir
from furniture_cad.eval.console_gt import load_hand_cut_list, score_prediction, step_bbox_mm
from furniture_cad.geom_check import bbox_mm_from_solid


CAD = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[3]
IR = CAD / "examples" / "ir" / "console_01.ir.json"
STEP = REPO / "evals" / "photos" / "cases" / "console_01" / "console_01.step"


def test_validate_console_ir_v2() -> None:
    ir = load_ir(IR)
    assert ir["schema"] == "furniture_ir.v2"
    v = validate_ir(ir)
    assert v["ok"] is True, v


def test_compile_console_ir_bbox_near_step() -> None:
    result = compile_ir(IR)
    assert result["report"]["ok"] is True
    bb = bbox_mm_from_solid(result["assembly"])
    # Prefer STEP bbox when present
    if STEP.is_file():
        gt = step_bbox_mm(STEP)
        assert abs(bb["w"] - gt["w"]) <= 25.0  # P1 approximation; tighten as form improves
        assert abs(bb["d"] - gt["d"]) <= 15.0
        assert abs(bb["h"] - gt["h"]) <= 15.0
    else:
        assert abs(bb["w"] - 1193.8) <= 25.0
        assert abs(bb["h"] - 762.0) <= 15.0


def test_compile_console_part_recall_vs_hand() -> None:
    result = compile_ir(IR)
    parts = [p.to_dict() if hasattr(p, "to_dict") else dict(p) for p in result["parts"]]
    bb = bbox_mm_from_solid(result["assembly"])
    report = score_prediction(
        predicted_parts=parts,
        predicted_features=result.get("features") or {},
        overall_pred_mm={"w": bb["w"], "d": bb["d"], "h": bb["h"]},
    )
    # P1 gate target ≥0.85 on ids; sizes still approximate
    assert report["parts"]["recall"] >= 0.85, report["parts"]
    assert result["features"].get("drawer", 0) == 2
    assert result["features"].get("leg", 0) == 4
    hand = load_hand_cut_list()
    assert hand["id"] == "console_01"
    if STEP.is_file():
        gt = step_bbox_mm(STEP)
        assert abs(bb["w"] - gt["w"]) <= 5.0
        assert abs(bb["h"] - gt["h"]) <= 2.0



def test_compile_deterministic() -> None:
    a = compile_ir(IR)
    b = compile_ir(IR)
    assert a["report"]["ir_hash"] == b["report"]["ir_hash"]
    bba = bbox_mm_from_solid(a["assembly"])
    bbb = bbox_mm_from_solid(b["assembly"])
    assert bba == bbb
