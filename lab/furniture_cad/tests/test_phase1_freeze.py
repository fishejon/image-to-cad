"""Phase 1 gate: freeze-set solids + lists + curved blanks."""

from __future__ import annotations

from pathlib import Path

from furniture_cad.lists import material_plan
from furniture_cad.parts import load_parts
from furniture_cad.tools.freeze_set import FREEZE_PIECES, freeze_tool_calls
from furniture_cad.tools.handlers import ToolContext
from furniture_cad.tools.loop import run_tool_script

ROOT = Path(__file__).resolve().parents[1]


def test_freeze_set_all_three_export_solids_and_lists(tmp_path: Path) -> None:
    for pid, meta in FREEZE_PIECES.items():
        ctx = ToolContext(work_dir=tmp_path / pid)
        results = run_tool_script(ctx, freeze_tool_calls(pid))
        assert results[0]["result"]["ok"], results[0]
        assert results[1]["result"]["ok"], results[1]
        assert ctx.last_build and ctx.last_build.get("exported") is True
        assert (tmp_path / pid / f"{pid}.stl").is_file()
        assert (tmp_path / pid / f"{pid}.step").is_file()
        assert len(ctx.parts) == meta["expect_types"]
        assert sum(p.qty for p in ctx.parts) == meta["expect_pieces"]
        totals = results[1]["result"]["totals"]
        assert totals["piece_count"] == meta["expect_pieces"]
        assert totals["part_types"] == meta["expect_types"]


def test_case_01_hand_check_qty_matches_photo_inventory() -> None:
    parts = load_parts(ROOT / "examples" / "parts" / "case_01_mcm.json")
    by_id = {p.id: p.qty for p in parts}
    assert by_id["post"] == 4
    assert by_id["shelf"] == 5
    assert by_id["sled_foot"] == 2
    assert sum(by_id.values()) == 31
    plan = material_plan(parts)
    assert plan["totals"]["piece_count"] == 31


def test_chair_02_curved_blanks_larger_than_finished() -> None:
    parts = load_parts(ROOT / "examples" / "parts" / "chair_02_curved.json")
    curved = [p for p in parts if p.curved]
    assert len(curved) >= 2
    for p in curved:
        ft, fw, fl = p.finished_twl()
        bt, bw, bl = p.blank_twl()
        assert bt >= ft and bw >= fw and bl >= fl
        assert (bt, bw, bl) != (ft, fw, fl)
    from furniture_cad.lists import board_feet

    plan = material_plan(parts)
    finished_bf = sum(board_feet(p.thickness_mm, p.width_mm, p.length_mm, p.qty) for p in parts)
    assert plan["totals"]["blank_board_feet"] > finished_bf
