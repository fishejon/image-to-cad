"""P2: staged pipeline end-to-end without a model call."""

from __future__ import annotations

from pathlib import Path

from furniture_cad.pipeline import run_pipeline


REPO = Path(__file__).resolve().parents[3]
PHOTO = REPO / "evals" / "photos" / "cases" / "console_01" / "console_01_front_clean.jpg"


def test_pipeline_console_with_known_dims(tmp_path: Path) -> None:
    known = {"w": 1193.8, "d": 304.8, "h": 762.0}
    photo = PHOTO if PHOTO.is_file() else None
    summary = run_pipeline(work_dir=tmp_path, photo=photo, known_mm=known)
    assert summary["mode"] == "pipeline"
    assert summary["ok"] is True
    assert summary["stages"] == [
        "intake",
        "perceive",
        "dimension",
        "construct",
        "compile",
        "verify",
        "derive",
    ]
    assert (tmp_path / "model.stl").is_file()
    assert (tmp_path / "ir.json").is_file()
    assert (tmp_path / "cut_list_v2.json").is_file()
    assert (tmp_path / "events.json").is_file()
    assert abs(summary["bbox_mm"]["h"] - 762.0) < 2.0
    assert summary["features"].get("drawer") == 2
    assert summary["spent_usd_approx"] == 0.0
