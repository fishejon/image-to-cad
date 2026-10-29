"""Demo box export smoke test."""

from __future__ import annotations

from pathlib import Path

from furniture_cad.export import demo_box


def test_demo_box(tmp_path: Path) -> None:
    stl = demo_box(tmp_path)
    assert stl.exists()
    assert stl.stat().st_size > 100
    assert (tmp_path / "demo_box.step").exists()
