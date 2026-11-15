"""Generic case runner + the synthetic sideboard_01 ground truth."""

from __future__ import annotations

import json

import pytest
from build123d import import_step

from furniture_cad.construct import compile_ir, construct_ir_from_observation
from furniture_cad.construct.blocks.swept_shell import swept_shell
from furniture_cad.dimension import apply_dims
from furniture_cad.eval.case_gt import CASES_DIR, is_ready, load_case, step_path
from furniture_cad.eval.case_run import oracle_observation, run_case, summarize

SIDE = CASES_DIR / "sideboard_01"
CONSOLE = CASES_DIR / "console_01"
needs_side = pytest.mark.skipif(not is_ready(SIDE), reason="sideboard_01 GT not present")


@needs_side
def test_sideboard_is_labelled_synthetic_and_consistent_with_its_step():
    hand = load_case(SIDE)["hand"]
    assert hand["synthetic"] is True and hand["status"] == "synthetic_design"
    assert (SIDE / "make_synthetic_gt.py").is_file()
    bb = import_step(str(step_path(SIDE))).bounding_box()
    assert (bb.size.X, bb.size.Y, bb.size.Z) == pytest.approx((1524.0, 457.2, 812.8), abs=0.05)
    dims = hand["dims_mm"]
    assert (dims["w"], dims["d"], dims["h"]) == pytest.approx((1524.0, 457.2, 812.8))
    pieces = sum(p["qty"] for p in hand["parts"])
    assert pieces == len(import_step(str(step_path(SIDE))).solids())  # one solid per piece
    classes = {p["class"] for p in hand["parts"]}
    assert classes <= {"visible", "construction", "joinery"}


@needs_side
def test_oracle_observation_reads_features_json():
    o = oracle_observation(SIDE)
    assert o["class"] == "casegood.sideboard" and o["end_form"] == "flat" and o["leg_style"] == "tapered"
    assert o["counts"]["drawer"] == 3 and o["counts"]["door"] == 2 and o["counts"]["leg"] == 4


@needs_side
def test_run_case_reports_everything_for_the_sideboard():
    rep = run_case("sideboard_01", assist=True)
    s = summarize(rep)
    assert s["assisted"] is True and s["case"] == "sideboard_01"
    for k in ("part_recall", "dim_match_share", "cut_list_match_share", "feature_count_match"):
        assert 0.0 <= s[k] <= 1.0
    assert s["shape_iou_front"] > 0.8 and s["shape_iou_side"] > 0.7  # simple straight-sided silhouette
    built = rep["features_built_vs_truth"]
    assert built["drawer"] == {"built": 3, "truth": 3} and built["leg"] == {"built": 4, "truth": 4}
    assert rep["asks"] == []  # assisted: leg and drawer-front heights supplied


@needs_side
def test_run_case_blind_asks_for_the_two_sizes():
    rep = run_case("sideboard_01", assist=False)
    assert {a["key"] for a in rep["asks"]} == {"leg", "drawer_front"}


@pytest.mark.skipif(not is_ready(CONSOLE), reason="console_01 GT not present")
def test_run_case_reproduces_the_console_harness_numbers():
    rep = run_case("console_01")
    # same generic IR + oracle counts as the earlier offline baseline: dimension share 0.385
    assert rep["parts"]["dim_match_share"] == pytest.approx(0.3846, abs=0.01)
    assert rep["parts"]["recall_excl_joinery"] == 1.0


def test_straight_ends_stay_straight_and_square():
    """lean_deg 0 must not fall back to the console's 6 degrees; flat ends are plain panels."""
    o = {
        "schema": "observation.v1",
        "class": "casegood.sideboard",
        "components": [],
        "dims_mm": {},
        "counts": {"drawer": 3, "door": 0, "shelf": 0, "leg": 4, "open_cubby": 0, "pull": 0, "end_block_carved": 0},
        "end_form": "flat",
        "leg_style": "tapered",
        "unknowns": [],
        "meta": {},
    }
    K = {"w": 1524.0, "d": 457.2, "h": 812.8, "leg": 177.8}
    ir = construct_ir_from_observation(o, apply_dims(o, known_mm=K))
    assert ir["carcass"]["outline"]["lean_deg"] == 0.0 and ir["carcass"]["outline"]["sweep_r"] == 0.0
    res = compile_ir(ir)
    parts = {p.id: p for p in res["parts"]}
    assert min(parts["E1"].finished_twl()) == pytest.approx(ir["params"]["wall"], abs=0.01)
    shell = swept_shell(W=1524, H=812.8, D=457.2, wall=19, lean_deg=0, sweep_r=0, under_z=177.8, back_t=6)
    assert shell["meta"]["x_tangent"] == pytest.approx(-762 + 1.0, abs=0.01)  # r clamps to 1 mm: square corner
    assert shell["meta"]["bottom_len"] == pytest.approx(1524 - 2 * 19, abs=0.01)


# ---- known generalisation gaps: strict xfail so they flip loudly when implemented -----------------
@needs_side
@pytest.mark.xfail(strict=True, reason="Construct has no doors yet")
def test_gap_doors_are_built():
    assert run_case("sideboard_01")["features_built_vs_truth"]["door"]["built"] == 2


@needs_side
@pytest.mark.xfail(strict=True, reason="drawer banks are side by side only; no stacked drawers yet")
def test_gap_stacked_drawers_share_one_bay():
    _, ir = None, construct_ir_from_observation(
        oracle_observation(SIDE), apply_dims(oracle_observation(SIDE), known_mm={"w": 1524.0, "d": 457.2, "h": 812.8})
    )
    bank = next(c for c in ir["layout"]["children"] if c["kind"] == "drawer_bank")
    assert bank.get("rows") == 3


@needs_side
@pytest.mark.xfail(strict=True, reason="no vertical dividers / multi-bay layout yet")
def test_gap_vertical_dividers_and_second_shelf_exist():
    rep = run_case("sideboard_01", assist=True)
    matched = {e["truth"] for e in rep["parts"]["size_errors"]}
    assert {"V1", "SH1", "DR1"} <= matched
