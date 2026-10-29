"""Failure log helper tests."""

from __future__ import annotations

from pathlib import Path

from furniture_cad.failures import log_missing_block, read_failures


def test_log_missing_block(tmp_path: Path) -> None:
    path = tmp_path / "failure_log.jsonl"
    rec = log_missing_block(
        "photo_chair_01",
        "bent_panel",
        notes="continuous molded seat; flat seat_panel wrong",
        template="four_leg_chair",
        path=path,
    )
    assert rec["kind"] == "missing_block"
    assert rec["need"] == "bent_panel"
    rows = read_failures(path)
    assert len(rows) == 1
    assert rows[0]["photo_id"] == "photo_chair_01"
