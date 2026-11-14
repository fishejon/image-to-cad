"""Generic GT cases: scaffolding, readiness skip, board feet, provenance, console regression."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from furniture_cad.eval.board_feet import board_feet_error, hand_net_bf, score_board_feet
from furniture_cad.eval.case_gt import CASE_FILES, CASES_DIR, is_ready, scaffold_case, score_case
from furniture_cad.eval.console_gt import load_hand_cut_list
from furniture_cad.pipeline import run_pipeline

KNOWN = {"w": 1193.8, "d": 304.8, "h": 762.0}


def _run(tmp_path: Path) -> tuple[dict, list[dict]]:
    summary = run_pipeline(work_dir=tmp_path, photo=None, known_mm=KNOWN, use_vision=False)
    rows = json.loads((tmp_path / "parts.json").read_text(encoding="utf-8"))["parts"]
    return summary, rows


def test_scaffold_creates_template_files(tmp_path):
    out = scaffold_case("sideboard_x", dims_in=(60, 18, 32), root=tmp_path)
    for name in CASE_FILES:
        assert (out / name).is_file(), name
    known = json.loads((out / "known_sizes.json").read_text())
    assert known["overall"]["w"]["v"] == pytest.approx(1524.0)
    hand = json.loads((out / "cut_list.hand.json").read_text())
    assert hand["schema"] == "hand_cut_list.v1" and hand["status"] == "template"
    assert not is_ready(out)


def test_scaffold_refuses_overwrite_and_bad_ids(tmp_path):
    scaffold_case("a", root=tmp_path)
    with pytest.raises(FileExistsError):
        scaffold_case("a", root=tmp_path)
    for bad in ("", "../x", ".hidden", "a/b"):
        with pytest.raises(ValueError):
            scaffold_case(bad, root=tmp_path)


def test_template_case_with_step_but_empty_plan_is_not_ready(tmp_path):
    out = scaffold_case("b", root=tmp_path)
    (out / "b.step").write_text("ISO-10303-21;")
    assert not is_ready(out)


def _case_dirs() -> list[Path]:
    return sorted(p for p in CASES_DIR.iterdir() if p.is_dir() and (p / "cut_list.hand.json").is_file())


@pytest.mark.parametrize("case_dir", _case_dirs(), ids=lambda p: p.name)
def test_every_case_is_valid_or_waiting(case_dir):
    if not is_ready(case_dir):
        pytest.skip(f"{case_dir.name}: awaiting Fusion STEP + filled hand cut list")
    hand = json.loads((case_dir / "cut_list.hand.json").read_text())
    assert hand["schema"] == "hand_cut_list.v1"
    for p in hand["parts"]:
        for k in ("id", "qty", "thickness_mm", "width_mm", "length_mm"):
            assert k in p, (case_dir.name, p.get("id"), k)


def test_board_feet_error_helper():
    assert board_feet_error(55.0, 50.0) == pytest.approx(0.1)
    assert board_feet_error(1.0, None) is None


def test_console_hand_board_feet_truth():
    truth = hand_net_bf(load_hand_cut_list())
    assert truth["stated"] == pytest.approx(59.4, abs=0.05)
    assert truth["recomputed"] == pytest.approx(56.1, abs=0.1)


def test_pipeline_default_is_blind_construct(tmp_path):
    summary, _ = _run(tmp_path)
    assert summary["construct_answer_key_seeded"] is False
    ev = [e for e in summary["events"] if e["stage"] == "construct"][0]
    assert ev["answer_key_seeded"] is False
    assert ev["ir_path"] == "from_observation"


def test_explicit_seed_ir_is_answer_key(tmp_path):
    from furniture_cad.pipeline import CONSOLE_IR

    summary = run_pipeline(work_dir=tmp_path, photo=None, known_mm=KNOWN, use_vision=False, seed_ir=CONSOLE_IR)
    assert summary["construct_answer_key_seeded"] is True


def test_console_cut_list_match_regression_on_golden_seed(tmp_path):
    """Guard block-fidelity gains against the golden answer-key IR (not blind Construct)."""
    from furniture_cad.pipeline import CONSOLE_IR

    summary = run_pipeline(
        work_dir=tmp_path, photo=None, known_mm=KNOWN, use_vision=False, seed_ir=CONSOLE_IR
    )
    rows = json.loads((tmp_path / "parts.json").read_text(encoding="utf-8"))["parts"]
    case = CASES_DIR / "console_01"
    if not is_ready(case):
        pytest.skip("console_01 GT not present")
    rep = score_case(case, parts_rows=rows, overall_pred_mm=KNOWN)
    assert summary["construct_answer_key_seeded"] is True
    assert rep["parts"]["recall"] == 1.0
    assert rep["parts"]["cut_list_match_share"] >= 0.45
    by = {e["truth"]: e for e in rep["parts"]["size_errors"]}
    for pid in ("T1", "D1", "BK1"):
        assert by[pid]["within_5mm_or_3pct"], pid
    bf = rep["board_feet"]
    assert bf["pred_bf"] > 0 and bf["truth_bf"]["stated"] == pytest.approx(59.4, abs=0.05)
    assert score_board_feet(load_hand_cut_list(), rows)["pred_bf"] == bf["pred_bf"]


def test_drawer_box_front_applied_has_back_only():
    from furniture_cad.construct.blocks import drawer_box

    full = drawer_box(W=400, D=300, H=80)
    applied = drawer_box(W=400, D=300, H=80, front_applied=True)
    qty = lambda r: {p.id: p.qty for p in r["parts"]}  # noqa: E731
    assert qty(full)["drawer_fb"] == 2 and qty(applied)["drawer_fb"] == 1
