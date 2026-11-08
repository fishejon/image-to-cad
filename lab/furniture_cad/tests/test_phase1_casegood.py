"""Phase 1: Tier-1 blocks, perceive/dimension, compiler, critic, allowances."""

from __future__ import annotations

from pathlib import Path

from furniture_cad.construct import compile_ir, load_ir
from furniture_cad.construct.blocks import TIER1_BLOCKS, drawer_box, leg_set
from furniture_cad.derive_allowance import lists_with_allowances, part_record_v2
from furniture_cad.dimension import apply_dims, snap_stock
from furniture_cad.geom_check import bbox_mm_from_solid, within_pct
from furniture_cad.intake import intake_photo
from furniture_cad.perceive import perceive_casegood
from furniture_cad.verify import verify_against_dims


REPO = Path(__file__).resolve().parents[3]
CAD = Path(__file__).resolve().parents[1]
IR = CAD / "examples" / "ir" / "console_stub.ir.json"


def test_tier1_block_catalog() -> None:
    required = {
        "divider",
        "top",
        "drawer_box",
        "drawer_front",
        "door",
        "face_frame",
        "leg_set",
        "apron",
        "stretcher",
    }
    assert required <= set(TIER1_BLOCKS)
    box = drawer_box(W=400, D=250, H=120)
    assert box["assembly"] is not None
    assert sum(p.qty for p in box["parts"]) >= 5
    legs = leg_set(count=4, height=165, top=[38, 38], foot=[24, 24])
    assert legs["parts"][0].qty == 4


def test_compile_console_with_drawers_and_allowances() -> None:
    result = compile_ir(load_ir(IR))
    bb = bbox_mm_from_solid(result["assembly"])
    assert within_pct(bb["w"], 1194, 0.05)
    assert within_pct(bb["h"], 762, 0.05)
    assert result["features"]["drawer"] == 2
    assert result["features"]["leg"] == 4
    assert result["cut_list_v2"]["schema"] == "cut_list.v2"
    assert result["cut_list_v2"]["count"] >= 6
    v2 = part_record_v2(result["parts"][0])
    assert "finished_mm" in v2 and "blank_mm" in v2 and "allowance" in v2


def test_perceive_dimension_verify_pipeline() -> None:
    photo = REPO / "evals" / "photos" / "cases" / "case_01.jpg"
    known = {"w": 1194.0, "d": 305.0, "h": 762.0}
    if photo.is_file():
        intake = intake_photo(photo, known_mm=known)
    else:
        intake = {
            "schema": "intake.v1",
            "path": "stub",
            "segmentation": {"score": 0.5, "quality": "ok"},
            "rectify": {"rectified": False},
            "scale": {"px_per_mm": 1.0, "scale_source": "user:W=1194"},
        }
    obs = perceive_casegood(intake, class_hint="casegood.console", known_mm=known)
    assert obs["schema"] == "observation.v1"
    assert obs["dims_mm"]["W"]["src"] == "user"
    dims = apply_dims(obs, known_mm=known)
    assert dims["ready"] is True
    assert snap_stock(18.7) == 19.0
    result = compile_ir(IR)
    report = verify_against_dims(
        result["assembly"],
        {"w": 1194, "d": 305, "h": 762},
        features_expected={"drawer": 2, "leg": 4},
        features_found=result["features"],
    )
    assert report["schema"] == "verify.v1"
    assert report["ok"] is True
    assert lists_with_allowances(result["parts"])["count"] == len(result["parts"])
