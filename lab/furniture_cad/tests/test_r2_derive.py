"""R2: PartRecords derived from solids; lists match typed sizes within 5%."""

from __future__ import annotations

from build123d import Box, Pos

from furniture_cad.derive import FLAG_MEASURED, consistency_report, dims_from_solid, part
from furniture_cad.lists import material_plan, within_size_pct
from furniture_cad.parts import PartRecord
from furniture_cad.tools.handlers import ToolContext, dispatch


def test_dims_from_solid_sorts_thickness_width_length() -> None:
    d = dims_from_solid(Box(18, 288, 876))  # shelf-like
    assert abs(d["thickness_mm"] - 18) < 1e-6
    assert d["length_mm"] >= d["width_mm"] >= d["thickness_mm"]
    assert d["grain"] in ("x", "y", "z")


def test_part_registers_measured_flag() -> None:
    solid = Box(40, 40, 1720)
    p = part("post", solid, material="walnut", qty=4)
    assert p.estimate_flag == FLAG_MEASURED
    assert within_size_pct(p.thickness_mm, 40)
    assert within_size_pct(p.width_mm, 40)
    assert within_size_pct(p.length_mm, 1720)
    assert p.qty == 4


def test_derived_case_fixture_matches_typed_oracle_within_5pct() -> None:
    """Drawer bookshelf fixture: derived sizes vs historical typed PartRecords."""
    W, D, H, t = 900.0, 300.0, 1800.0, 18.0
    side = Box(t, D, H)
    board = Box(W - 2 * t, D - 12, t)
    back = Box(W - 2 * t, 6, H - 2 * t)
    derived = [
        part("side_L", side, material="oak", qty=1),
        part("side_R", side, material="oak", qty=1),
        part("board", board, material="oak", qty=6),
        part("back", back, material="ply", qty=1, make="sheet"),
    ]
    typed = [
        PartRecord(id="side_L", name="Left side", qty=1, material="oak", thickness_mm=18, width_mm=300, length_mm=1800, grain="z"),
        PartRecord(id="side_R", name="Right side", qty=1, material="oak", thickness_mm=18, width_mm=300, length_mm=1800, grain="z"),
        PartRecord(id="board", name="board", qty=6, material="oak", thickness_mm=18, width_mm=288, length_mm=876, grain="x"),
        PartRecord(id="back", name="back", qty=1, material="ply", thickness_mm=6, width_mm=880, length_mm=1740, grain="x"),
    ]
    by_d = {p.id: p for p in derived}
    for trow in typed:
        drow = by_d[trow.id]
        assert drow.qty == trow.qty
        # Compare sorted finished dims (axis assignment may swap width/length labels)
        got = sorted(drow.finished_twl())
        want = sorted(trow.finished_twl())
        for a, b in zip(got, want):
            assert within_size_pct(a, b, 5.0), (trow.id, got, want)


def test_consistency_flags_aabb_overlap() -> None:
    a = part("a", Box(100, 50, 25), material="oak")
    b = part("b", Pos(10, 0, 0) * Box(100, 50, 25), material="oak")
    rep = consistency_report([a, b])
    assert rep["overlaps"]


def test_build_script_part_api(tmp_path) -> None:
    ctx = ToolContext(work_dir=tmp_path)
    script = """
side = Box(18, 300, 1800)
shelf = Box(864, 288, 18)
parts = [
  part('side', side, material='oak', qty=2),
  part('shelf', shelf, material='oak', qty=5),
]
assembly = Compound(children=[Pos(-441, 0, 900) * side, Pos(441, 0, 900) * side] + [Pos(0, 0, 200 + i * 300) * shelf for i in range(5)])
"""
    out = dispatch(ctx, "build", {"name": "derived", "script": script})
    assert out["ok"], out
    assert all(p.get("estimate_flag") == FLAG_MEASURED for p in out["parts"])
    lists = dispatch(ctx, "lists", {})
    assert lists["ok"]
    assert lists["cut_list"][0]["estimate_flag"] == FLAG_MEASURED
    assert "consistency" in lists
