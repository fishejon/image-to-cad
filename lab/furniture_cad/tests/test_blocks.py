"""Unit tests for v0 blocks."""

from __future__ import annotations

from pathlib import Path

import pytest

from furniture_cad.blocks import (
    back_mid_slat,
    back_panel,
    curved_stile,
    rail,
    rounded_cushion,
    seat_panel,
    tapered_leg,
    winged_top_rail,
)
from furniture_cad.catalog import BLOCK_CATALOG, list_blocks
from furniture_cad.export import export_solid
from furniture_cad.validate import bbox_size, solid_ok

OUT = Path(__file__).resolve().parents[1] / "out" / "blocks"


@pytest.mark.parametrize(
    "name",
    [
        "tapered_leg",
        "seat_panel",
        "rail",
        "back_panel",
        "back_mid_slat",
        "winged_top_rail",
        "rounded_cushion",
        "curved_stile",
    ],
)
def test_catalog_lists_block(name: str) -> None:
    assert name in BLOCK_CATALOG
    assert name in list_blocks()


def test_tapered_leg_square() -> None:
    s = tapered_leg(height=450, top_size=36, bot_size=28, section="square")
    assert solid_ok(s)
    dx, dy, dz = bbox_size(s)
    assert abs(dz - 450) < 1.5
    assert abs(dx - 36) < 2.0  # bbox XY uses larger end (top)
    assert abs(dy - 36) < 2.0
    OUT.mkdir(parents=True, exist_ok=True)
    export_solid(s, OUT / "tapered_leg", formats=("stl",))


def test_tapered_leg_round() -> None:
    s = tapered_leg(height=400, top_size=30, bot_size=24, section="round")
    assert solid_ok(s)
    assert abs(bbox_size(s)[2] - 400) < 1.5


def test_seat_panel() -> None:
    s = seat_panel(width=460, depth=430, thickness=28)
    assert solid_ok(s)
    dx, dy, dz = bbox_size(s)
    assert abs(dx - 460) < 1.5
    assert abs(dy - 430) < 1.5
    assert abs(dz - 28) < 1.5
    OUT.mkdir(parents=True, exist_ok=True)
    export_solid(s, OUT / "seat_panel", formats=("stl",))


def test_rail() -> None:
    s = rail(length=400, section_w=22, section_h=32)
    assert solid_ok(s)
    dx, dy, dz = bbox_size(s)
    assert abs(dx - 400) < 1.5
    assert abs(dy - 22) < 1.5
    assert abs(dz - 32) < 1.5
    OUT.mkdir(parents=True, exist_ok=True)
    export_solid(s, OUT / "rail", formats=("stl",))


def test_back_panel() -> None:
    s = back_panel(width=400, height=355, thickness=12)
    assert solid_ok(s)
    dx, dy, dz = bbox_size(s)
    assert abs(dx - 400) < 1.5
    assert abs(dy - 12) < 1.5
    assert abs(dz - 355) < 1.5
    OUT.mkdir(parents=True, exist_ok=True)
    export_solid(s, OUT / "back_panel", formats=("stl",))


def test_back_mid_slat() -> None:
    s = back_mid_slat(width=400, height=48, thickness=14)
    assert solid_ok(s)
    assert abs(bbox_size(s)[0] - 400) < 1.5
    OUT.mkdir(parents=True, exist_ok=True)
    export_solid(s, OUT / "back_mid_slat", formats=("stl",))


def test_winged_top_rail() -> None:
    s = winged_top_rail(width=420, end_height=95, mid_height=58, thickness=16)
    assert solid_ok(s)
    dx, dy, dz = bbox_size(s)
    assert abs(dx - 420) < 3.0
    assert abs(dy - 16) < 3.0
    assert abs(dz - 95) < 3.0
    OUT.mkdir(parents=True, exist_ok=True)
    export_solid(s, OUT / "winged_top_rail", formats=("stl",))


def test_winged_top_rail_curved() -> None:
    s = winged_top_rail(width=420, end_height=95, mid_height=58, thickness=16, curve_sag=40)
    assert solid_ok(s)
    OUT.mkdir(parents=True, exist_ok=True)
    export_solid(s, OUT / "winged_top_rail_curved", formats=("stl",))


def test_back_mid_slat_curved() -> None:
    s = back_mid_slat(width=318, height=44, thickness=14, curve_sag=35)
    assert solid_ok(s)


def test_curved_stile() -> None:
    s = curved_stile(height=800, section=25, rake_y=55, curve_y=28)
    assert solid_ok(s)
    OUT.mkdir(parents=True, exist_ok=True)
    export_solid(s, OUT / "curved_stile", formats=("stl",))


def test_rounded_cushion() -> None:
    s = rounded_cushion(width=430, depth=400, height=40, corner_radius=30)
    assert solid_ok(s)
    assert abs(bbox_size(s)[2] - 40) < 2.0
    OUT.mkdir(parents=True, exist_ok=True)
    export_solid(s, OUT / "rounded_cushion", formats=("stl",))


def test_bad_params_rejected() -> None:
    with pytest.raises((ValueError, TypeError)):
        tapered_leg(height=-1, top_size=10, bot_size=10)
    with pytest.raises(ValueError):
        tapered_leg(height=100, top_size=10, bot_size=10, section="hex")
