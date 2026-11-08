"""Phase 2: Tier-2 blocks, hardware, shop exports, sandbox policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from furniture_cad.construct import compile_ir
from furniture_cad.construct.blocks.tier2 import TIER2_BLOCKS, bench, table
from furniture_cad.construct.hardware import REGISTRY, hardware_list_from_ir
from furniture_cad.construct.sandbox import assert_no_freeform, sandbox_status
from furniture_cad.export_shop import export_cutlist_csv, export_dxf_stub, export_pdf_stub
from furniture_cad.geom_check import bbox_mm_from_solid, within_pct


CAD = Path(__file__).resolve().parents[1]
IR = CAD / "examples" / "ir" / "console_stub.ir.json"


def test_tier2_table_and_bench() -> None:
    assert {"table", "bench", "stool", "angled_leg"} <= set(TIER2_BLOCKS)
    t = table(W=1400, D=800, H=750)
    bb = bbox_mm_from_solid(t["assembly"])
    assert within_pct(bb["w"], 1400, 0.05)
    assert within_pct(bb["h"], 750, 0.05)
    b = bench(W=1200)
    assert sum(p.qty for p in b["parts"]) >= 6


def test_hardware_and_shop_exports(tmp_path: Path) -> None:
    assert "side_mount_250" in REGISTRY
    ir = {
        "schema": "furniture_ir.v1",
        "root": {
            "type": "casegood",
            "bays": [{"kind": "drawer_bank", "n": 2, "slide": "side_mount_250", "front": {"pull": "pull_128"}}],
        },
    }
    hw = hardware_list_from_ir(ir)
    assert hw["count"] == 2
    assert hw["items"][0]["qty"] == 4  # 2 drawers × pair
    result = compile_ir(IR)
    csv_p = export_cutlist_csv(result["cut_list_v2"], tmp_path / "cut.csv")
    dxf_p = export_dxf_stub(result["cut_list_v2"], tmp_path / "cut.dxf")
    pdf_p = export_pdf_stub(result["cut_list_v2"], tmp_path / "cut.pdf", title="Console")
    assert csv_p.is_file() and "id,qty" in csv_p.read_text()
    assert "LWPOLYLINE" in dxf_p.read_text()
    assert pdf_p.stat().st_size > 100


def test_sandbox_blocks_freeform() -> None:
    assert sandbox_status()["freeform_script"] == "disabled"
    with pytest.raises(RuntimeError, match="build_ir"):
        assert_no_freeform("build")
