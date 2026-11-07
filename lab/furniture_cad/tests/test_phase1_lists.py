"""Phase 1: parts schema, allowlist, cut/material lists (no build123d required)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from furniture_cad.allowlist import (
    ALLOWED_BLOCK_IDS,
    AllowlistError,
    api_surface,
    check_import,
    get_block,
    is_allowed_block,
)
from furniture_cad.lists import (
    board_feet,
    compare_qty,
    cut_rows,
    material_plan,
    within_size_pct,
)
from furniture_cad.parts import PartRecord, dump_parts, load_parts, total_qty

ROOT = Path(__file__).resolve().parents[1]
BOOKSHELF_PARTS = ROOT / "examples" / "parts" / "bookshelf_parts.json"


def test_allowlist_blocks_match_catalog() -> None:
    assert "tapered_leg" in ALLOWED_BLOCK_IDS
    assert is_allowed_block("rail")
    assert not is_allowed_block("bent_panel")
    fn = get_block("rail")
    assert callable(fn)
    with pytest.raises(AllowlistError):
        get_block("nope")


def test_allowlist_import_gate() -> None:
    check_import("math")
    check_import("furniture_cad.blocks")
    with pytest.raises(AllowlistError):
        check_import("subprocess")
    check_import("subprocess", experimental=True)
    surf = api_surface(experimental=False)
    assert "rail" in surf["blocks"]
    assert "allowed_build123d" in surf


def test_part_record_roundtrip(tmp_path: Path) -> None:
    p = PartRecord(
        id="leg",
        name="Leg",
        qty=4,
        material="oak",
        thickness_mm=40,
        width_mm=40,
        length_mm=700,
        grain="z",
        how_made="sweep",
        curved=True,
        blank_thickness_mm=42,
        blank_width_mm=42,
        blank_length_mm=720,
    )
    path = dump_parts([p], tmp_path / "parts.json", meta={"object": "test"})
    loaded = load_parts(path)
    assert len(loaded) == 1
    assert loaded[0].blank_twl() == (42.0, 42.0, 720.0)
    assert total_qty(loaded) == 4


def test_bookshelf_qty_exact() -> None:
    parts = load_parts(BOOKSHELF_PARTS)
    expected = {
        "side_L": 1,
        "side_R": 1,
        "board": 6,
        "back": 1,
        "divider": 1,
        "drawer_front": 2,
        "drawer_side_L": 2,
        "drawer_side_R": 2,
        "drawer_back": 2,
        "drawer_bottom": 2,
    }
    assert compare_qty(parts, expected) == []
    assert total_qty(parts) == 20


def test_bookshelf_sizes_within_5pct() -> None:
    """Finished sizes match the browser cutList fixture within the Phase 1 gate."""
    parts = load_parts(BOOKSHELF_PARTS)
    gold = {p.id: p for p in parts}
    # Spot-check against known CAD.cutList numbers (same file is the source of truth).
    assert within_size_pct(gold["side_L"].length_mm, 1800, 5)
    assert within_size_pct(gold["board"].width_mm, 288, 5)
    assert within_size_pct(gold["back"].thickness_mm, 6, 5)
    rows = cut_rows(parts)
    assert len(rows) == 10
    plan = material_plan(parts)
    assert plan["totals"]["piece_count"] == 20
    assert plan["totals"]["blank_board_feet"] > 0
    assert any(s["kind"] == "sheet" for s in plan["summary"])
    assert board_feet(18, 300, 1800, 1) == pytest.approx((18 / 25.4) * (300 / 25.4) * (1800 / 25.4) / 12, rel=1e-6)


def test_lists_cli(tmp_path: Path) -> None:
    from furniture_cad.lists import main

    out = tmp_path / "plan.json"
    assert main(["--parts", str(BOOKSHELF_PARTS), "--out", str(out)]) == 0
    data = json.loads(out.read_text())
    assert data["totals"]["piece_count"] == 20
