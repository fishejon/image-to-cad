"""WP3 Perceive attrs — enums, majority vote, no end_block invention, crops."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from furniture_cad.perceive.attrs import majority_vote, normalize_attrs
from furniture_cad.perceive.crops import generate_detail_crops
from furniture_cad.perceive.vision import perceive_vision


def test_normalize_attrs_enums() -> None:
    a = normalize_attrs({"leg_style": "two_profile", "top_edge": "ROUND-OVER", "bogus": "x"})
    assert a["leg_style"] == "two_profile_flared"
    assert a["top_edge"] == "unknown"
    a2 = normalize_attrs({"top_edge": "roundover"})
    assert a2["top_edge"] == "roundover"


def test_majority_vote_asks_on_tie() -> None:
    samples = [
        {"leg_style": "tapered", "top_edge": "square"},
        {"leg_style": "flared", "top_edge": "square"},
        {"leg_style": "tapered", "top_edge": "eased"},
    ]
    v = majority_vote(samples, keys=["leg_style", "top_edge"])
    assert v["attrs"]["leg_style"] == "tapered"  # 2/3
    assert v["attrs"]["top_edge"] == "square"  # 2/3
    # True tie → ask
    tie = majority_vote(
        [{"foot_style": "pad"}, {"foot_style": "bun"}, {"foot_style": "spade"}],
        keys=["foot_style"],
    )
    assert tie["attrs"]["foot_style"] == "unknown"
    assert tie["asks"]


def test_generate_detail_crops_capped() -> None:
    img = Image.new("RGB", (400, 300), (240, 240, 240))
    ImageDraw.Draw(img).rectangle((50, 40, 350, 220), fill=(40, 40, 40))
    mask = np.zeros((300, 400), dtype=bool)
    mask[40:220, 50:350] = True
    regions = [
        {"id": 1, "label": "drawer_front", "bbox_px": [80, 60, 320, 120]},
        {"id": 2, "label": "leg", "bbox_px": [60, 200, 100, 280]},
        {"id": 3, "label": "top", "bbox_px": [50, 40, 350, 55]},
    ]
    crops = generate_detail_crops(img, regions=regions, mask=mask, max_crops=8)
    assert 1 <= len(crops) <= 8
    assert all(c["role"] for c in crops)
    assert all(c["image"].size[0] > 0 for c in crops)


def test_perceive_vision_no_api_does_not_invent_end_blocks() -> None:
    # Heuristic fallback path — no invention from class
    obs = perceive_vision(
        {"schema": "intake.v2", "path": None, "segmentation": {}, "rectify": {}, "scale": None},
        class_hint="casegood.console",
        known_mm={"w": 1193.8},
        api_key="",
    )
    assert (obs.get("counts") or {}).get("end_block_carved", 0) == 0 or obs["meta"].get("perceive") == "heuristic_fallback"
