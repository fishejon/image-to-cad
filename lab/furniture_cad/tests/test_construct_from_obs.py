"""Construct IR from Perceive observation (no answer-key seed)."""

from __future__ import annotations

from pathlib import Path

from furniture_cad.construct import compile_ir, construct_ir_from_observation, load_ir
from furniture_cad.dimension import apply_dims
from furniture_cad.geom_check import bbox_mm_from_solid
from furniture_cad.pipeline import CONSOLE_IR, run_pipeline

KNOWN = {"w": 1193.8, "d": 304.8, "h": 762.0}


def _obs_console(**counts: int) -> dict:
    base = {
        "schema": "observation.v1",
        "class": "casegood.console",
        "components": [],
        "dims_mm": {},
        "counts": {
            "drawer": 2,
            "door": 0,
            "shelf": 1,
            "leg": 4,
            "open_cubby": 1,
            "pull": 0,
            "end_block_carved": 2,
            **counts,
        },
        "end_form": "swept_leaning",
        "leg_style": "two_profile_flared",
        "unknowns": [],
        "meta": {"perceive": "test"},
    }
    return base


def test_construct_ir_from_observation_layout() -> None:
    obs = _obs_console()
    dims = apply_dims(obs, known_mm=KNOWN)
    ir = construct_ir_from_observation(obs, dims)
    assert ir["schema"] == "furniture_ir.v2"
    assert ir["params"]["W"] == 1193.8
    kinds = [c["kind"] for c in ir["layout"]["children"]]
    assert "drawer_bank" in kinds and "open" in kinds
    bank = next(c for c in ir["layout"]["children"] if c["kind"] == "drawer_bank")
    assert bank["cols"] == 2
    assert ir["legs"]["count"] == 4
    assert "joinery" not in ir  # no answer-key blanks
    # Not the Fusion under_z
    assert abs(float(ir["params"]["under_z"]) - 495.3) > 1.0


def test_construct_compiles_valid_solid() -> None:
    obs = _obs_console()
    dims = apply_dims(obs, known_mm=KNOWN)
    ir = construct_ir_from_observation(obs, dims)
    result = compile_ir(ir)
    assert result["report"]["ok"] is True
    bb = bbox_mm_from_solid(result["assembly"])
    assert abs(bb["w"] - 1193.8) < 5.0
    assert abs(bb["h"] - 762.0) < 5.0
    assert result["features"].get("drawer") == 2
    assert result["features"].get("leg") == 4
    ids = {p.id for p in result["parts"]}
    assert "LT" not in ids and "W1" not in ids  # joinery not invented


def test_golden_console_ir_still_has_joinery() -> None:
    result = compile_ir(load_ir(CONSOLE_IR))
    ids = {p.id for p in result["parts"]}
    assert {"LT", "W1", "R1"} <= ids
    assert result["features"].get("drawer") == 2


def test_pipeline_default_is_not_answer_key(tmp_path: Path) -> None:
    summary = run_pipeline(work_dir=tmp_path, photo=None, known_mm=KNOWN, use_vision=False)
    assert summary["ok"] is True
    assert summary["construct_answer_key_seeded"] is False
    assert abs(summary["bbox_mm"]["h"] - 762.0) < 2.0


def test_pipeline_seed_ir_is_answer_key(tmp_path: Path) -> None:
    summary = run_pipeline(
        work_dir=tmp_path, photo=None, known_mm=KNOWN, use_vision=False, seed_ir=CONSOLE_IR
    )
    assert summary["ok"] is True
    assert summary["construct_answer_key_seeded"] is True
    assert summary["features"].get("drawer") == 2
