"""P0 / D8: camera-fit calibration against console_01 GT."""

from __future__ import annotations

from pathlib import Path

from furniture_cad.verify.camera_fit import D8_THRESHOLD, calibrate_gt, fit_camera_iou


REPO = Path(__file__).resolve().parents[3]
GT = REPO / "evals" / "photos" / "cases" / "console_01"
PHOTO = GT / "console_01.jpg"
STEP = GT / "console_01.step"


def test_camera_fit_runs_on_console_photo() -> None:
    if not PHOTO.is_file() or not STEP.is_file():
        return
    fit = fit_camera_iou(PHOTO, _stl(), pose_hint="three_quarter_right", coarse=True)
    assert "iou" in fit
    assert 0.0 <= fit["iou"] <= 1.0
    assert fit["schema"] == "camera_fit.v1"


def _stl() -> Path:
    from furniture_cad.eval.console_gt import ensure_gt_stl

    return ensure_gt_stl()


def test_d8_calibration_fails_on_three_quarter_until_front_on() -> None:
    """Current photo is 3/4 + clutter — D8 must not pass (honest ruler)."""
    if not PHOTO.is_file() or not STEP.is_file():
        return
    report = calibrate_gt(photo=PHOTO, step_or_stl=STEP, pose_hint="three_quarter_right")
    assert report["schema"] == "calibration.d8.v1"
    assert report["threshold"] == D8_THRESHOLD
    # Gate: do not claim trusted IoU on this photo
    assert report["passed"] is False
    assert report["iou"] < D8_THRESHOLD
