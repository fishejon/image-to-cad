"""Proportions: Perceive -> Construct -> compile, plus per-class / per-dimension scoring."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from furniture_cad.construct import compile_ir, construct_ir_from_observation
from furniture_cad.dimension import apply_dims
from furniture_cad.eval.case_gt import CASES_DIR, is_ready, score_case
from furniture_cad.eval.scorer import score_parts
from furniture_cad.perceive.vision import _norm_proportions, perceive_vision, proportions_from_landmarks

KNOWN = {"w": 1193.8, "d": 304.8, "h": 762.0}
CONSOLE = CASES_DIR / "console_01"
TRUE_PROPS = {"under_z_frac": 0.65, "drawer_bank_frac": 0.4942}


def _obs(props: dict | None = None) -> dict:
    o = {
        "schema": "observation.v1",
        "class": "casegood.console",
        "components": [],
        "dims_mm": {},
        "counts": {"drawer": 2, "door": 0, "shelf": 1, "leg": 4, "open_cubby": 1, "pull": 0, "end_block_carved": 2},
        "end_form": "swept_leaning",
        "leg_style": "two_profile_flared",
        "unknowns": [],
        "meta": {"perceive": "test"},
    }
    if props is not None:
        o["proportions"] = props
    return o


def _compile(props: dict | None):
    o = _obs(props)
    ir = construct_ir_from_observation(o, apply_dims(o, known_mm=KNOWN))
    return ir, compile_ir(ir)


def test_norm_proportions_keeps_only_sane_numbers():
    assert _norm_proportions({"under_z_frac": 0.65, "drawer_bank_frac": 0.49}) == {
        "under_z_frac": 0.65,
        "drawer_bank_frac": 0.49,
    }
    assert _norm_proportions({"under_z_frac": 0.99, "drawer_bank_frac": 0.05}) == {}  # out of bounds
    assert _norm_proportions({"under_z_frac": None, "drawer_bank_frac": "x"}) == {}
    assert _norm_proportions(None) == {}


def test_vision_returns_proportions(tmp_path: Path):
    photo = tmp_path / "p.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xd9")
    counts = {"drawer": 2, "door": 0, "shelf": 1, "leg": 4, "open_cubby": 1, "pull": 0, "end_block_carved": 2}
    pass1 = {
        "schema": "observation.v1",
        "class": "casegood.console",
        "counts": counts,
        "components": [],
        "unknowns": [],
        "end_form": "swept_leaning",
        "leg_style": "two_profile_flared",
        # direct ratios are no longer read: only landmark rows count
        "proportions": {"under_z_frac": 0.10, "drawer_bank_frac": 0.20},
        "landmarks": {"top": 100, "floor": 900, "case_bottom": 380, "drawer_top": 170, "drawer_bottom": 308},
    }

    def _msg(**kw):
        m = MagicMock()
        b = MagicMock()
        b.type = "text"
        b.text = json.dumps(counts if "ONLY JSON" in str(kw.get("system")) else pass1)
        m.content = [b]
        m.usage = MagicMock(input_tokens=10, output_tokens=5)
        return m

    client = MagicMock()
    client.messages.create.side_effect = lambda **kw: _msg(**kw)
    intake = {"schema": "intake.v1", "path": str(photo), "segmentation": {"score": 0.5}, "rectify": {}, "scale": {}}
    block = {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "xx"}}
    with (
        patch("anthropic.Anthropic", return_value=client),
        patch("furniture_cad.perceive.vision._photo_content_block", return_value=block),
    ):
        obs = perceive_vision(intake, known_mm=KNOWN, photo=photo, api_key="k", model="m")
    assert obs["landmarks"]["floor"] == 900
    assert obs["proportions"]["under_z_frac"] == pytest.approx(0.65, abs=1e-3)
    assert obs["proportions"]["drawer_bank_frac"] == pytest.approx(0.4929, abs=1e-3)
    assert client.messages.create.call_count == 2  # no extra model call for proportions


def test_proportions_from_landmarks_console_like():
    p = proportions_from_landmarks({"top": 100, "floor": 900, "case_bottom": 380, "drawer_top": 170, "drawer_bottom": 308})
    assert p["under_z_frac"] == pytest.approx(0.65, abs=1e-3)
    assert p["drawer_bank_frac"] == pytest.approx(138 / 280, abs=1e-3)


def test_proportions_from_landmarks_drops_impossible_rows():
    base = {"top": 100, "floor": 900, "case_bottom": 380}
    assert proportions_from_landmarks({**base, "drawer_top": 300, "drawer_bottom": 200}) == {"under_z_frac": 0.65}
    assert proportions_from_landmarks({**base, "drawer_top": 170, "drawer_bottom": 500}) == {"under_z_frac": 0.65}
    assert proportions_from_landmarks({"top": 100, "floor": 900, "case_bottom": 950}) == {}
    assert proportions_from_landmarks({"top": 100, "floor": 900}) == {}
    assert proportions_from_landmarks({"top": "x", "floor": None}) == {}
    assert proportions_from_landmarks(None) == {}
    # drawer rows are ignored if the case rows are missing
    assert proportions_from_landmarks({"top": 100, "floor": 900, "drawer_top": 170, "drawer_bottom": 308}) == {}


def test_construct_uses_perceived_proportions_else_prior():
    ir, _ = _compile(None)
    assert ir["params"]["under_z"] == pytest.approx(762 * 0.35, abs=0.5)
    assert all("bank_frac" not in c for c in ir["layout"]["children"])
    assert any("under_z from prior" in n for n in ir["notes"])

    ir, _ = _compile(TRUE_PROPS)
    assert ir["params"]["under_z"] == pytest.approx(495.3, abs=0.5)
    bank = next(c for c in ir["layout"]["children"] if c["kind"] == "drawer_bank")
    assert bank["bank_frac"] == pytest.approx(0.4942)
    assert any("under_z from perceive" in n for n in ir["notes"])


def test_compile_sizes_drawers_from_measured_bank():
    ir, res = _compile(TRUE_PROPS)
    parts = {p.id: p for p in res["parts"]}
    case_h = 762 - 495.3
    want_front_h = 0.4942 * case_h - 2 * 1.5  # reveal from IR
    t, w, L = parts["DF1"].finished_twl()
    assert min(w, L) == pytest.approx(w, abs=1e-6)  # width is the middle dim here
    assert w == pytest.approx(want_front_h, abs=0.5)
    # box depth rule: D - front_t - back_t - 1/8 in, applied on every path
    _, res_prior = _compile(None)
    ds = {p.id: p for p in res_prior["parts"]}["DS1"]
    assert max(ds.finished_twl()) == pytest.approx(304.8 - 19.0 - 6.0 - 3.175, abs=0.5)


def test_compile_geometry_still_valid_with_extreme_proportions():
    for props in ({"under_z_frac": 0.8, "drawer_bank_frac": 0.9}, {"under_z_frac": 0.08, "drawer_bank_frac": 0.15}):
        _, res = _compile(props)
        assert res["report"]["ok"] is True
        assert res["features"]["drawer"] == 2


def test_score_parts_class_split_and_dim_share():
    truth = [
        {"id": "A", "thickness_mm": 20, "width_mm": 100, "length_mm": 500, "qty": 1},
        {"id": "B", "thickness_mm": 20, "width_mm": 100, "length_mm": 500, "qty": 1, "class": "construction"},
        {"id": "C", "thickness_mm": 10, "width_mm": 20, "length_mm": 200, "qty": 1, "class": "joinery"},
    ]
    pred = [
        {"id": "A", "thickness_mm": 20, "width_mm": 100, "length_mm": 500, "qty": 1},  # exact
        {"id": "B", "thickness_mm": 20, "width_mm": 100, "length_mm": 800, "qty": 1},  # 2 of 3 dims ok
    ]
    s = score_parts(pred, truth)
    assert s["by_class"]["visible"] == {"n": 1, "recall": 1.0, "cut_list_match_share": 1.0}
    assert s["by_class"]["construction"]["recall"] == 1.0
    assert s["by_class"]["construction"]["cut_list_match_share"] == 0.0
    assert s["by_class"]["joinery"]["recall"] == 0.0
    assert s["recall_excl_joinery"] == 1.0
    assert s["dim_match_share"] == pytest.approx((3 + 2) / 9, abs=1e-3)


def test_console_oracle_proportions_improve_dimensions_not_just_labels():
    """Upper bound if Perceive measured perfectly. Not a score: proportions come from the answer key."""
    if not is_ready(CONSOLE):
        pytest.skip("console_01 GT not present")

    def run(props):
        _, res = _compile(props)
        rows = [p.to_dict() for p in res["parts"]]
        return score_case(CONSOLE, parts_rows=rows, overall_pred_mm=KNOWN)["parts"]

    base, oracle = run(None), run(TRUE_PROPS)
    assert oracle["dim_match_share"] > base["dim_match_share"] + 0.10
    errs = {e["truth"]: e for e in oracle["size_errors"]}
    assert errs["DF1"]["max_pct"] < 0.04  # front height now ~exact; width still limits the pass
    # joinery is never invented, so its recall stays 0 on any photo-derived IR
    assert oracle["by_class"]["joinery"]["recall"] == 0.0
