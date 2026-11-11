"""P3: vision Perceive helpers + dimension conflict rules (offline)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from furniture_cad.dimension import apply_dims, snap_stock
from furniture_cad.eval.scorer import feature_recall
from furniture_cad.perceive import feature_counts_from_observation, perceive_vision
from furniture_cad.pipeline import run_pipeline

REPO = Path(__file__).resolve().parents[3]
FEATURES = REPO / "evals" / "photos" / "cases" / "console_01" / "features.json"
PHOTO = REPO / "evals" / "photos" / "cases" / "console_01" / "console_01_front_clean.jpg"


def test_dimension_user_wins_on_conflict() -> None:
    obs = {
        "schema": "observation.v1",
        "class": "casegood.console",
        "components": [],
        "dims_mm": {
            "W": {"v": 1000.0, "src": "pixel"},
            "D": {"v": 300.0, "src": "pixel"},
            "H": {"v": 700.0, "src": "pixel"},
        },
    }
    dims = apply_dims(obs, known_mm={"w": 1193.8, "d": 304.8, "h": 762.0})
    assert dims["ready"] is True
    assert dims["overall_mm"]["W"]["v"] == 1193.8
    assert dims["overall_mm"]["W"]["src"] == "user"
    assert any(c["axis"] == "W" for c in dims["conflicts"])
    assert dims["within_3pct"] is False


def test_dimension_scale_from_one_known() -> None:
    obs = {
        "schema": "observation.v1",
        "class": "casegood.console",
        "components": [],
        "dims_mm": {
            "W": {"v": 1000.0, "src": "pixel"},
            "D": {"v": 255.0, "src": "pixel"},
            "H": {"v": 638.0, "src": "pixel"},
        },
    }
    dims = apply_dims(obs, known_mm={"w": 1193.8})
    assert dims["ready"] is True
    assert abs(dims["overall_mm"]["W"]["v"] - 1193.8) < 0.01
    assert abs(dims["overall_mm"]["D"]["v"] - 255.0 * 1.1938) < 0.5
    assert dims["scale_factor"] is not None
    assert snap_stock(18.7) == 19.0


def test_feature_counts_from_observation() -> None:
    obs = {
        "counts": {
            "drawer": 2,
            "leg": 4,
            "shelf": 1,
            "open_cubby": 1,
            "pull": 0,
            "door": 0,
            "end_block_carved": 2,
        }
    }
    counts = feature_counts_from_observation(obs)
    assert counts["drawer"] == 2
    assert counts["end_block_carved"] == 2
    truth = json.loads(FEATURES.read_text(encoding="utf-8"))["counts"]
    fr = feature_recall(counts, truth)
    assert fr["recall"] >= 0.9


def test_perceive_vision_fallback_without_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("FURNITURE_CAD_ANTHROPIC_KEY", raising=False)
    photo = tmp_path / "x.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xd9")
    intake = {
        "schema": "intake.v1",
        "path": str(photo),
        "segmentation": {"score": 0.5},
        "rectify": {},
        "scale": {},
    }
    obs = perceive_vision(intake, known_mm={"w": 1193.8}, photo=photo, api_key="")
    assert obs["schema"] == "observation.v1"
    assert (obs.get("meta") or {}).get("perceive") == "heuristic_fallback"


def test_perceive_vision_mocked_two_pass(tmp_path: Path) -> None:
    photo = tmp_path / "console.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xd9")
    counts = {
        "drawer": 2,
        "door": 0,
        "shelf": 1,
        "leg": 4,
        "open_cubby": 1,
        "pull": 0,
        "end_block_carved": 2,
    }
    pass1 = {
        "schema": "observation.v1",
        "class": "casegood.console",
        "counts": {**counts, "drawer": 3},  # disagree → ask_user
        "components": [],
        "unknowns": [],
        "end_form": "swept_leaning",
        "leg_style": "two_profile_flared",
    }

    def _msg(**kwargs):
        m = MagicMock()
        sys_prompt = str(kwargs.get("system") or "")
        body = json.dumps(counts if "ONLY JSON" in sys_prompt else pass1)
        block = MagicMock()
        block.type = "text"
        block.text = body
        m.content = [block]
        m.usage = MagicMock(input_tokens=100, output_tokens=50)
        return m

    intake = {
        "schema": "intake.v1",
        "path": str(photo),
        "segmentation": {"score": 0.5, "quality": "ok"},
        "rectify": {"rectified": False},
        "scale": {},
    }
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = lambda **kw: _msg(**kw)

    with (
        patch("anthropic.Anthropic", return_value=fake_client),
        patch(
            "furniture_cad.perceive.vision._photo_content_block",
            return_value={
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": "xx"},
            },
        ),
    ):
        obs = perceive_vision(
            intake,
            known_mm={"w": 1193.8, "d": 304.8, "h": 762.0},
            photo=photo,
            api_key="test-key",
            model="claude-haiku-4-5",
        )
    assert (obs.get("meta") or {}).get("perceive") == "vision_v1"
    assert obs["counts"]["drawer"] == 2
    assert obs["counts"]["leg"] == 4
    assert any("drawer" in str(u.get("q")) for u in obs.get("unknowns") or [])
    assert fake_client.messages.create.call_count == 2


def test_pipeline_heuristic_still_zero_spend(tmp_path: Path) -> None:
    known = {"w": 1193.8, "d": 304.8, "h": 762.0}
    photo = PHOTO if PHOTO.is_file() else None
    summary = run_pipeline(work_dir=tmp_path, photo=photo, known_mm=known, use_vision=False)
    assert summary["ok"] is True
    assert summary["spent_usd_approx"] == 0.0
    assert "heuristic" in str(summary.get("perceive_mode") or "")
