"""Template compile smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

from furniture_cad.compile import compile_template, load_params
from furniture_cad.export import export_assembly
from furniture_cad.validate import bbox_size, solid_ok

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "programs"
OUT = Path(__file__).resolve().parents[1] / "out" / "tests"


def test_four_leg_chair_demo() -> None:
    params = load_params(EXAMPLES / "four_leg_chair_demo.json")
    result = compile_template("four_leg_chair", params)
    assert result["template"] == "four_leg_chair"
    assert solid_ok(result["assembly"])
    assert "seat" in result["parts"]
    assert "leg_fl" in result["parts"]
    written = export_assembly(result, OUT / "four_leg_chair", name="four_leg_chair")
    assert written["stl"].exists()
    assert written["step"].exists()


def test_four_leg_chair_with_back() -> None:
    result = compile_template(
        "four_leg_chair",
        {
            "seat_w": 420,
            "seat_d": 400,
            "seat_h": 465,
            "leg_top": 22,
            "leg_bot": 22,
            "leg_section": "round",
            "stretcher": False,
            "back": True,
            "back_h": 355,
            "back_w": 400,
            "back_t": 12,
        },
    )
    assert "back" in result["parts"]
    assert solid_ok(result["assembly"])
    # Rear legs taller than front when back is on
    assert bbox_size(result["parts"]["leg_bl"])[2] > bbox_size(result["parts"]["leg_fl"])[2]


def test_four_leg_chair_mcm_rails_one_piece_seat() -> None:
    result = compile_template(
        "four_leg_chair",
        {
            "seat_w": 445,
            "seat_d": 420,
            "seat_t": 19,
            "seat_h": 445,
            "leg_top": 25,
            "leg_bot": 25,
            "leg_section": "square",
            "rear_outer_w": 368,
            "stretcher": True,
            "stretcher_front": False,
            "back": True,
            "back_style": "mcm_rails",
            "back_h": 356,
            "cushion": False,
            "curve_sag": 40,
            "rake_y": 50,
            "stile_curve_y": 25,
        },
    )
    assert "cushion" not in result["parts"]
    assert "seat" in result["parts"]
    assert "back_mid_slat" in result["parts"]
    assert "winged_top_rail" in result["parts"]
    assert "back" not in result["parts"]
    assert solid_ok(result["assembly"])
    written = export_assembly(result, OUT / "mcm_chair", name="mcm_chair")
    assert written["stl"].exists()


def test_stool_demo() -> None:
    params = load_params(EXAMPLES / "stool_demo.json")
    result = compile_template("stool", params)
    assert result["template"] == "stool"
    assert solid_ok(result["assembly"])
    assert len([k for k in result["parts"] if k.startswith("leg_")]) == 4
    written = export_assembly(result, OUT / "stool", name="stool")
    assert written["stl"].exists()


def test_stool_three_leg() -> None:
    result = compile_template(
        "stool",
        {
            "legs": 3,
            "seat_w": 320,
            "seat_d": 320,
            "seat_h": 600,
            "stretcher": False,
            "leg_section": "round",
        },
    )
    assert len([k for k in result["parts"] if k.startswith("leg_")]) == 3
    assert solid_ok(result["assembly"])


def test_params_wrapper_json() -> None:
    raw = json.loads((EXAMPLES / "four_leg_chair_demo.json").read_text(encoding="utf-8"))
    assert "seat_w" in load_params(EXAMPLES / "four_leg_chair_demo.json")
    assert raw["template"] == "four_leg_chair"
