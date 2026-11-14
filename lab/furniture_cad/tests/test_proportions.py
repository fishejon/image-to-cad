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
from furniture_cad.perceive.vision import SYSTEM, perceive_vision

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


def test_vision_no_longer_asks_for_geometry(tmp_path: Path):
    assert "landmarks" not in SYSTEM and "proportions" not in SYSTEM and "_frac" not in SYSTEM
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
        "proportions": {"under_z_frac": 0.10},  # ignored even if a model volunteers it
        "landmarks": {"top": 1, "floor": 2},
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
    assert "proportions" not in obs and "landmarks" not in obs
    assert obs["counts"]["drawer"] == 2
    assert client.messages.create.call_count == 2

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


def _compile_known(known: dict):
    o = _obs(None)
    dims = apply_dims(o, known_mm={**KNOWN, **known})
    ir = construct_ir_from_observation(o, dims)
    return dims, ir, compile_ir(ir)


def test_dimension_records_known_extra_and_asks():
    o = _obs(None)
    d = apply_dims(o, known_mm=KNOWN)
    assert d["known_extra_mm"] == {}
    assert {a["key"] for a in d["asks"]} == {"leg", "drawer_front"}
    d = apply_dims(o, known_mm={**KNOWN, "leg": 495.3, "drawer_front": 128.6})
    assert d["known_extra_mm"] == {"leg_h": 495.3, "drawer_front_h": 128.6}
    assert d["asks"] == []
    # no drawers observed: no drawer question
    o2 = _obs(None)
    o2["counts"]["drawer"] = 0
    assert {a["key"] for a in apply_dims(o2, known_mm=KNOWN)["asks"]} == {"leg"}


def test_user_known_sizes_drive_construct_and_beat_perceived():
    o = _obs({"under_z_frac": 0.2, "drawer_bank_frac": 0.9})  # wrong perceived values
    dims = apply_dims(o, known_mm={**KNOWN, "leg": 495.3, "drawer_front": 128.6})
    ir = construct_ir_from_observation(o, dims)
    assert ir["params"]["under_z"] == pytest.approx(495.3, abs=0.01)
    assert any("under_z from user" in n for n in ir["notes"]) and any("drawer bank height from user" in n for n in ir["notes"])
    parts = {p.id: p for p in compile_ir(ir)["parts"]}
    _, w, _L = parts["DF1"].finished_twl()
    assert w == pytest.approx(128.6, abs=0.5)  # drawer front height is exactly what the user typed


def test_user_known_sizes_match_the_oracle_gain():
    if not is_ready(CONSOLE):
        pytest.skip("console_01 GT not present")

    def share(known):
        _, _, res = _compile_known(known)
        rows = [p.to_dict() for p in res["parts"]]
        return score_case(CONSOLE, parts_rows=rows, overall_pred_mm=KNOWN)["parts"]["dim_match_share"]

    assert share({"leg": 495.3, "drawer_front": 128.6}) > share({}) + 0.10


def test_pipeline_surfaces_asks_only_when_missing(tmp_path: Path):
    from furniture_cad.pipeline import run_pipeline

    s1 = run_pipeline(work_dir=tmp_path / "a", photo=None, known_mm=KNOWN, use_vision=False)
    assert {a["key"] for a in s1["asks"]} == {"leg"}  # offline: no drawers observed
    s2 = run_pipeline(work_dir=tmp_path / "b", photo=None, known_mm={**KNOWN, "leg": 495.3}, use_vision=False)
    assert s2["asks"] == [] and s2["known_extra_mm"] == {"leg_h": 495.3}
    assert s2["ok"] is True
