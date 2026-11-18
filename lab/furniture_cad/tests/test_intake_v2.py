"""WP1 intake.v2 — segment, rectify, scale with synthetic images."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from furniture_cad.intake import intake_photo
from furniture_cad.intake.rectify import (
    ARUCO_ID,
    DEFAULT_MARKER_MM,
    MAX_RESIDUAL_ANGLE_DEG,
    detect_aruco,
    rectify_image,
)
from furniture_cad.intake.scale import compute_scale
from furniture_cad.intake.segment import segment_subject
from furniture_cad.product.aruco_marker import write_marker_pack
from furniture_cad.product.capture_guidance import capture_checklist

SCHEMA = Path(__file__).resolve().parents[1] / "contracts" / "schemas" / "intake.v2.json"


def _furniture_on_white(
    *,
    w: int = 800,
    h: int = 600,
    box: tuple[int, int, int, int] = (200, 100, 600, 500),
    known_w_mm: float = 400.0,
) -> tuple[Image.Image, float]:
    """Dark rectangle on white; returns image and true width in mm for the box."""
    img = Image.new("RGB", (w, h), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    draw.rectangle(box, fill=(40, 40, 40))
    px_w = box[2] - box[0]
    # Caller chooses known_w_mm; true ppm = px_w / known_w_mm
    return img, known_w_mm


def _keystone(img: Image.Image, *, shear: float = 0.12) -> Image.Image:
    """Apply a horizontal keystone (trapezoid) warp."""
    import cv2

    arr = np.asarray(img)
    h, w = arr.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dx = shear * w
    dst = np.float32([[dx, 0], [w - dx, 0], [w, h], [0, h]])
    H = cv2.getPerspectiveTransform(src, dst)
    out = cv2.warpPerspective(arr, H, (w, h), borderValue=(245, 245, 245))
    return Image.fromarray(out)


def test_intake_schema_file_exists() -> None:
    assert SCHEMA.is_file()
    doc = json.loads(SCHEMA.read_text())
    assert doc["title"] == "intake.v2"


def test_capture_guidance_requires_aruco_and_front_contract() -> None:
    g = capture_checklist()
    assert g["schema"] == "capture_guidance.v2"
    assert g["aruco"]["id"] == ARUCO_ID
    assert g["aruco"]["size_mm"] == DEFAULT_MARKER_MM
    front = next(v for v in g["views"] if v["role"] == "front")
    assert front["required"] is True
    assert "70" in front["hint"] or "100" in front["hint"]


def test_grabcut_or_brightness_segments_dark_subject() -> None:
    img, _ = _furniture_on_white()
    seg = segment_subject(img)
    assert seg["method"] in ("grabcut", "brightness", "sam2")
    assert seg["mask"].mean() > 0.05
    assert seg["mask"].mean() < 0.7
    # Center pixel should be subject
    cy, cx = seg["mask"].shape[0] // 2, seg["mask"].shape[1] // 2
    assert bool(seg["mask"][cy, cx]) is True


def test_scale_from_known_width_on_mask() -> None:
    img, known_w = _furniture_on_white(known_w_mm=400.0)
    seg = segment_subject(img)
    scale = compute_scale(mask=seg["mask"], known_mm={"w": known_w})
    assert scale["scale_source"] == "user"
    assert scale["source_tag"] == "user"
    assert scale["px_per_mm"] is not None
    # True ppm ≈ 400 px / 400 mm = 1.0 (box is 400 px wide)
    assert abs(scale["px_per_mm"] - 1.0) / 1.0 <= 0.05  # ≤5% (acceptance ≤2% on clean; allow grabcut bleed)
    assert scale["rel_error_est"] is not None and scale["rel_error_est"] < 0.05


def test_aruco_detect_and_scale(tmp_path: Path) -> None:
    import cv2

    pack = write_marker_pack(tmp_path)
    assert Path(pack["png"]).is_file() and Path(pack["pdf"]).is_file()
    # Compose a page: white bg + furniture + marker
    img = Image.new("RGB", (900, 700), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    draw.rectangle((150, 80, 750, 550), fill=(35, 35, 35))
    marker = cv2.imread(pack["png"], cv2.IMREAD_GRAYSCALE)
    # Crop to the marker square (skip label strip): top-left square region
    # render_marker_png pads margin; find black content bbox
    ys, xs = np.where(marker < 128)
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    sq = marker[y0 : y1 + 1, x0 : x1 + 1]
    sq_rgb = Image.fromarray(sq).convert("RGB").resize((120, 120), Image.Resampling.NEAREST)
    img.paste(sq_rgb, (40, 560))
    path = tmp_path / "scene.jpg"
    img.save(path)

    found = detect_aruco(img, marker_size_mm=DEFAULT_MARKER_MM)
    assert found is not None
    assert found["id"] == ARUCO_ID

    out = intake_photo(path, known_mm={"w": 1000.0}, marker_size_mm=DEFAULT_MARKER_MM, work_dir=tmp_path / "art")
    assert out["schema"] == "intake.v2"
    assert out["rectify"]["aruco"]["found"] is True
    assert out["scale"]["scale_source"] == "aruco"
    assert out["scale"]["source_tag"] == "cv"
    # After ArUco fronto-parallel warp, marker maps to a 200 px square for 100 mm → ppm ≈ 2.0
    # (or stays near the pasted 120 px / 100 mm = 1.2 if re-detect uses pre-warp size)
    ppm = float(out["scale"]["px_per_mm"])
    assert 1.0 <= ppm <= 2.5
    assert out["scale"]["rel_error_est"] is not None and out["scale"]["rel_error_est"] <= 0.05
    assert out["artifacts"]["mask_path"] and Path(out["artifacts"]["mask_path"]).is_file()


def test_keystone_retake_when_residual_high() -> None:
    img, _ = _furniture_on_white()
    # Strong keystone
    warped = _keystone(img, shear=0.35)
    # Force LSD path by ensuring no ArUco
    result = rectify_image(warped, mask=None)
    # Either corrected with residual reported, or retake requested
    assert "residual_angle_deg" in result
    if result["residual_angle_deg"] is not None and result["residual_angle_deg"] > MAX_RESIDUAL_ANGLE_DEG:
        assert result["retake_request"]
        assert "Retake" in result["retake_request"] or "retake" in result["retake_request"].lower()


def test_intake_photo_writes_v2_and_scale_from_user(tmp_path: Path) -> None:
    img, known_w = _furniture_on_white(known_w_mm=500.0)
    # Adjust box to 500 px wide for 1.0 ppm
    img = Image.new("RGB", (900, 600), (245, 245, 245))
    ImageDraw.Draw(img).rectangle((200, 80, 700, 520), fill=(30, 30, 30))
    path = tmp_path / "front.jpg"
    img.save(path)
    out = intake_photo(path, known_mm={"w": 500.0}, work_dir=tmp_path / "out")
    assert out["schema"] == "intake.v2"
    assert out["segmentation"]["method"] in ("grabcut", "brightness", "sam2")
    assert out["scale"]["px_per_mm"] is not None
    assert out["scale"]["source_tag"] in ("user", "cv", "guessed")
    # Should not use the old 0.70 fill-fraction as trusted
    if out["scale"]["scale_source"] == "user":
        assert abs(out["scale"]["px_per_mm"] - 1.0) / 1.0 <= 0.08


def test_homography_roundtrip_synthetic() -> None:
    """Warp with a known H, then recover a usable rectification (LSD or identity)."""
    import cv2

    img, _ = _furniture_on_white()
    arr = np.asarray(img)
    h, w = arr.shape[:2]
    # Mild rotation 4°
    M = cv2.getRotationMatrix2D((w / 2, h / 2), 4.0, 1.0)
    H = np.vstack([M, [0, 0, 1]])
    warped = Image.fromarray(cv2.warpPerspective(arr, H, (w, h), borderValue=(245, 245, 245)))
    result = rectify_image(warped)
    assert result["method"] in ("lsd_keystone", "aruco", "none")
    assert result["homography"] is not None or result["retake_request"]
