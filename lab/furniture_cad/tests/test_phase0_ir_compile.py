"""Phase 0: IR compiler expresses the console stub."""

from __future__ import annotations

from pathlib import Path

from furniture_cad.construct import compile_ir, load_ir
from furniture_cad.export import export_solid
from furniture_cad.geom_check import bbox_mm_from_solid, within_pct
from furniture_cad.intake import intake_photo


REPO = Path(__file__).resolve().parents[3]
CAD = Path(__file__).resolve().parents[1]
IR = CAD / "examples" / "ir" / "console_stub.ir.json"


def test_load_and_compile_console_ir(tmp_path: Path) -> None:
    ir = load_ir(IR)
    assert ir["schema"] == "furniture_ir.v1"
    result = compile_ir(ir)
    bb = bbox_mm_from_solid(result["assembly"])
    assert within_pct(bb["w"], 1194, 0.05)
    assert within_pct(bb["h"], 762, 0.05)
    assert within_pct(bb["d"], 305, 0.08)
    assert sum(p.qty for p in result["parts"]) >= 9  # 2+1+1+1+4 (+divider)
    export_solid(result["assembly"], tmp_path / "console", formats=("stl",))
    assert (tmp_path / "console.stl").is_file()


def test_intake_on_case_photo() -> None:
    photo = REPO / "evals" / "photos" / "cases" / "case_01.jpg"
    if not photo.is_file():
        return
    out = intake_photo(photo, known_mm={"w": 1219, "d": 305, "h": 1803})
    assert out["schema"] == "intake.v1"
    assert out["segmentation"]["score"] > 0
    assert "mask" in out
