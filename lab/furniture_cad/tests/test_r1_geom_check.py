"""R1: independent checks on known solids (bbox + AABB overlap)."""

from __future__ import annotations

from pathlib import Path

from build123d import Box, Pos

from furniture_cad.export import export_solid
from furniture_cad.geom_check import (
    bbox_mm_from_solid,
    bbox_mm_from_stl,
    boxes_overlap,
    compare_targets,
    solids_bbox_overlap,
    within_pct,
)
from furniture_cad.render_views import render_stl_views
from furniture_cad.tools.handlers import ToolContext, dispatch


def test_100mm_cube_bbox_from_solid() -> None:
    solid = Box(100, 100, 100)
    bb = bbox_mm_from_solid(solid)
    assert within_pct(bb["w"], 100)
    assert within_pct(bb["d"], 100)
    assert within_pct(bb["h"], 100)


def test_overlapping_boxes_detected() -> None:
    a = Box(100, 50, 25)
    b = Pos(40, 0, 0) * Box(100, 50, 25)  # overlaps in X
    c = Pos(200, 0, 0) * Box(100, 50, 25)  # separated
    assert solids_bbox_overlap(a, b) is True
    assert solids_bbox_overlap(a, c) is False
    assert boxes_overlap((-50, -25, -12.5), (50, 25, 12.5), (150, -25, -12.5), (250, 25, 12.5)) is False


def test_check_tool_uses_solid_bbox(tmp_path: Path) -> None:
    ctx = ToolContext(work_dir=tmp_path)
    ctx.targets_mm = {"w": 100, "d": 50, "h": 25}
    script = (
        "assembly = Box(100, 50, 25)\n"
        "parts = [PartRecord(id='box', name='Box', qty=1, material='oak', "
        "thickness_mm=25, width_mm=50, length_mm=100, grain='x', how_made='solid')]\n"
    )
    built = dispatch(ctx, "build", {"name": "cube", "script": script})
    assert built["ok"] is True
    assert built["build"]["exported"] is True
    checked = dispatch(ctx, "check", {"targets_mm": {"w": 100, "d": 50, "h": 25}})
    assert checked["ok"] is True
    assert checked["bbox_source"] in ("solid", "stl")
    assert checked["within_5pct"] is True
    assert checked["pass"] is True


def test_check_fails_when_size_wrong(tmp_path: Path) -> None:
    ctx = ToolContext(work_dir=tmp_path)
    script = (
        "assembly = Box(100, 50, 25)\n"
        "parts = [PartRecord(id='box', name='Box', qty=1, material='oak', "
        "thickness_mm=25, width_mm=50, length_mm=100, grain='x', how_made='solid')]\n"
    )
    assert dispatch(ctx, "build", {"name": "cube", "script": script})["ok"]
    checked = dispatch(ctx, "check", {"targets_mm": {"w": 200, "d": 50, "h": 25}})
    assert checked["ok"] is True
    assert checked["within_5pct"] is False
    assert checked["pass"] is False


def test_render_writes_pngs(tmp_path: Path) -> None:
    solid = Box(100, 50, 25)
    stl = export_solid(solid, tmp_path / "box", formats=("stl",))["stl"]
    meta = render_stl_views(stl, tmp_path / "renders", ["front", "side", "iso"])
    assert set(meta["views"]) >= {"front", "side", "iso"}
    for p in meta["views"].values():
        assert Path(p).is_file() and Path(p).stat().st_size > 0
    # STL bbox agrees with solid
    bb_s = bbox_mm_from_solid(solid)
    bb_m = bbox_mm_from_stl(stl)
    for k in ("w", "d", "h"):
        assert within_pct(bb_m[k], bb_s[k], 0.02)


def test_compare_targets_helper() -> None:
    out = compare_targets({"w": 100, "d": 50, "h": 25}, {"w": 100, "d": 50, "h": 25})
    assert out["within_5pct"] is True
    out2 = compare_targets({"w": 120, "d": 50, "h": 25}, {"w": 100, "d": 50, "h": 25})
    assert out2["within_5pct"] is False
