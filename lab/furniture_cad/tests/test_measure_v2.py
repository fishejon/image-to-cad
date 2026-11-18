"""WP2 Measure — geometry from rectified intake (synthetic)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from furniture_cad.intake import intake_photo
from furniture_cad.perceive.measure import measure_from_intake
from furniture_cad.perceive.measure.end_outline import end_outline_segments
from furniture_cad.perceive.measure.profile import width_profile

SCHEMA = Path(__file__).resolve().parents[1] / "contracts" / "schemas" / "observation.v2.json"


def _casegood_scene(tmp_path: Path, *, w_mm: float = 1000.0) -> tuple[Path, float]:
    """Dark case with two drawer bands + legs on white; 1 px/mm."""
    # Image 1000×700; case body 100–900 x, 100–450 y; drawers 120–480 and 120–380ish
    img = Image.new("RGB", (1000, 700), (245, 245, 245))
    d = ImageDraw.Draw(img)
    d.rectangle((100, 100, 900, 450), fill=(50, 50, 50))  # case
    d.rectangle((120, 120, 880, 220), fill=(70, 70, 70))  # drawer 1
    d.rectangle((120, 240, 880, 340), fill=(70, 70, 70))  # drawer 2
    d.rectangle((140, 450, 220, 650), fill=(40, 40, 40))  # leg L
    d.rectangle((780, 450, 860, 650), fill=(40, 40, 40))  # leg R
    # Reveal lines
    d.line((120, 230, 880, 230), fill=(200, 200, 200), width=2)
    path = tmp_path / "case.jpg"
    img.save(path)
    return path, w_mm


def test_observation_v2_schema_exists() -> None:
    assert SCHEMA.is_file()
    assert json.loads(SCHEMA.read_text())["title"] == "observation.v2"


def test_measure_emits_cv_measurements(tmp_path: Path) -> None:
    photo, w_mm = _casegood_scene(tmp_path)
    # Known width = body width 800 px → ppm = 800/1000 = 0.8 if mask is body;
    # overall subject ~800 px wide (100..900)
    intake = intake_photo(photo, known_mm={"w": 800.0}, work_dir=tmp_path / "art")
    assert intake["scale"] and intake["scale"]["px_per_mm"]
    obs = measure_from_intake(intake, class_hint="casegood.console")
    assert obs["schema"] == "observation.v2"
    assert obs["measurements"]
    assert all(m["source"] == "cv" for m in obs["measurements"])
    kinds = {m["kind"] for m in obs["measurements"]}
    assert "body_width" in kinds or "case_bottom_y" in kinds
    # No model lengths — every value has err_mm
    assert all(m.get("err_mm") is not None for m in obs["measurements"])


def test_width_profile_finds_case_bottom() -> None:
    mask = np.zeros((700, 1000), dtype=bool)
    mask[100:450, 100:900] = True
    mask[450:650, 140:220] = True
    mask[450:650, 780:860] = True
    prof = width_profile(mask)
    assert prof["case_bottom_row"] is not None
    assert abs(prof["case_bottom_row"] - 450) <= 15  # ≤10 mm at 1 px/mm; allow 15 px synthetic


def test_end_outline_bounded_segments() -> None:
    mask = np.zeros((400, 300), dtype=bool)
    # Tapered left edge
    for y in range(50, 300):
        x0 = 40 + int((y - 50) * 0.05)
        mask[y, x0:250] = True
    out = end_outline_segments(mask, px_per_mm=1.0, epsilon_mm=1.5)
    assert out["n"] <= 24
    assert out["source"] == "cv"
    assert out["segments"]


def test_asks_capped_and_scale_block(tmp_path: Path) -> None:
    photo, _ = _casegood_scene(tmp_path)
    intake = intake_photo(photo, known_mm=None)
    obs = measure_from_intake(intake)
    # Without scale, measure asks rather than inventing lengths
    if not (intake.get("scale") or {}).get("px_per_mm"):
        assert obs["asks"]
        assert obs["measurements"] == []
    else:
        assert len(obs.get("asks") or []) <= 3
