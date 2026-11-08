"""Phase 2: job store, check/compare tools, A/B scorecard."""

from __future__ import annotations

from pathlib import Path

from furniture_cad.jobs.ab_score import build_scorecard
from furniture_cad.jobs.store import JobStore
from furniture_cad.jobs.server import run_job
from furniture_cad.tools.oracle_set import oracle_tool_calls as freeze_tool_calls
from furniture_cad.tools.handlers import ToolContext, dispatch
from furniture_cad.tools.loop import run_tool_script


def test_job_store_create_and_get(tmp_path: Path) -> None:
    store = JobStore(tmp_path)
    job = store.create(prompt="chair_04", work_dir=tmp_path / "w1")
    assert job.status == "queued"
    got = store.get(job.id)
    assert got and got.id == job.id


def test_run_freeze_job(tmp_path: Path) -> None:
    store = JobStore(tmp_path)
    job = store.create(prompt="case_01", work_dir=tmp_path / "case_01")
    out = run_job(store, job.id, mode="freeze")
    assert out["ok"] is True
    job2 = store.get(job.id)
    assert job2 and job2.status == "succeeded"
    assert (tmp_path / "case_01" / "case_01.stl").is_file()


def test_check_and_compare_tools(tmp_path: Path) -> None:
    ctx = ToolContext(work_dir=tmp_path)
    results = run_tool_script(ctx, freeze_tool_calls("case_01"))
    assert results[0]["result"]["ok"]
    chk = dispatch(ctx, "check", {"targets_mm": {"w": 900, "h": 1720}})
    assert chk["ok"] is True
    assert chk["piece_count"] == 31
    cmp_ = dispatch(ctx, "compare", {"expected_qty": {"post": 4, "shelf": 5, "sled_foot": 2}})
    assert cmp_["ok"] is True
    assert cmp_["qty_ok"] is True


def test_ab_scorecard_includes_create_b() -> None:
    card = build_scorecard(["chair_04", "chair_02", "case_01"], measure_iou=False)
    assert len(card["pieces"]) == 3
    by_id = {r["id"]: r for r in card["pieces"]}
    assert by_id["chair_04"]["baseline_B_create"]["iou"] == 0.641
    assert by_id["case_01"]["baseline_B_create"]["iou"] == 0.297
    assert by_id["case_01"]["baseline_A_tooluse"]["piece_count"] == 31


def test_silhouette_iou_smoke(tmp_path: Path) -> None:
    from furniture_cad.export import demo_box
    from furniture_cad.silhouette import silhouette_iou
    from PIL import Image, ImageDraw

    stl = demo_box(tmp_path)
    photo = tmp_path / "box.jpg"
    im = Image.new("L", (200, 200), 255)
    ImageDraw.Draw(im).rectangle([60, 40, 140, 160], fill=40)
    im.save(photo)
    m = silhouette_iou(photo, stl, size=(128, 128))
    assert m["iou"] >= 0.15
