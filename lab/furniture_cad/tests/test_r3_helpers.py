"""R3 helpers: panel, shelf, open_etagere, carcass."""

from __future__ import annotations

from furniture_cad.blocks import BLOCK_FNS, open_etagere, carcass, panel, shelf_board
from furniture_cad.geom_check import bbox_mm_from_solid, within_pct
from furniture_cad.tools.handlers import ToolContext, dispatch


def test_helpers_registered() -> None:
    for name in ("panel", "shelf_board", "open_etagere", "carcass"):
        assert name in BLOCK_FNS


def test_open_etagere_matches_known_size() -> None:
    result = open_etagere(W=1219, D=305, H=1803, shelves=5, material="walnut")
    bb = bbox_mm_from_solid(result["assembly"])
    assert within_pct(bb["w"], 1219, 0.02)
    assert within_pct(bb["d"], 305, 0.02)
    assert within_pct(bb["h"], 1803, 0.02)
    assert sum(p.qty for p in result["parts"]) == 4 + 5 + 2


def test_carcass_builds() -> None:
    result = carcass(W=900, D=300, H=1800, shelves=6)
    assert result["assembly"] is not None
    assert len(result["parts"]) == 3


def test_build_via_open_etagere(tmp_path) -> None:
    ctx = ToolContext(work_dir=tmp_path)
    script = """
result = open_etagere(W=1219, D=305, H=1803, shelves=5)
assembly = result['assembly']
parts = result['parts']
"""
    out = dispatch(ctx, "build", {"name": "etagere", "script": script})
    assert out["ok"], out
    assert out["build"]["exported"] is True
    lists = dispatch(ctx, "lists", {})
    assert lists["ok"]
    assert lists["totals"]["piece_count"] == 11


def test_panel_and_shelf_smoke() -> None:
    p = panel(width=400, height=800, thickness=18)
    s = shelf_board(length=800, depth=280, thickness=18)
    assert bbox_mm_from_solid(p)["h"] > 0
    assert bbox_mm_from_solid(s)["w"] > 0
