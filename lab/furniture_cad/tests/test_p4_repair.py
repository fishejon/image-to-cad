"""P4: IR patch + repair loop."""

from __future__ import annotations

from pathlib import Path

from furniture_cad.construct import apply_ir_patches, compile_ir, load_ir, patches_from_discrepancies
from furniture_cad.geom_check import bbox_mm_from_solid
from furniture_cad.pipeline import run_pipeline
from furniture_cad.verify import repair_loop

CAD = Path(__file__).resolve().parents[1]
IR = CAD / "examples" / "ir" / "console_01.ir.json"
REPO = Path(__file__).resolve().parents[3]
PHOTO = REPO / "evals" / "photos" / "cases" / "console_01" / "console_01_front_clean.jpg"


def test_patches_from_dim_miss() -> None:
    patches = patches_from_discrepancies(
        [{"code": "dim_miss", "axis": "w", "want": 1193.8, "severity": "error"}],
        targets_mm={"w": 1193.8},
    )
    assert patches == [{"op": "set_param", "key": "W", "value": 1193.8}]


def test_apply_set_drawer_cols() -> None:
    ir = load_ir(IR)
    patched = apply_ir_patches(ir, [{"op": "set_drawer_cols", "value": 3}])
    bank = next(c for c in patched["layout"]["children"] if c["kind"] == "drawer_bank")
    assert bank["cols"] == 3


def test_repair_loop_fixes_wrong_params() -> None:
    ir = load_ir(IR)
    ir = {**ir, "params": {**(ir.get("params") or {}), "W": 800.0, "H": 500.0, "D": 200.0}}
    targets = {"w": 1193.8, "d": 304.8, "h": 762.0}
    result = repair_loop(ir, targets_mm=targets, features_expected={"drawer": 2, "leg": 4}, max_rounds=4)
    assert result["ok"] is True
    assert result["rounds"] >= 2
    bb = bbox_mm_from_solid(result["compiled"]["assembly"])
    assert abs(bb["w"] - 1193.8) < 5.0
    assert abs(bb["h"] - 762.0) < 5.0


def test_pipeline_with_repair_still_ok(tmp_path: Path) -> None:
    known = {"w": 1193.8, "d": 304.8, "h": 762.0}
    photo = PHOTO if PHOTO.is_file() else None
    summary = run_pipeline(work_dir=tmp_path, photo=photo, known_mm=known, use_vision=False)
    assert summary["ok"] is True
    assert (tmp_path / "repair.json").is_file()
    assert summary["rounds"] >= 1
