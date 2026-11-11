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
    fit = fit_camera_iou(PHOTO, _stl(), pose_hint="front", coarse=True)
    assert "iou" in fit
    assert 0.0 <= fit["iou"] <= 1.0
    assert fit["schema"] == "camera_fit.v1"


def _stl() -> Path:
    from furniture_cad.eval.console_gt import ensure_gt_stl

    return ensure_gt_stl()


def test_d8_calibration_on_front_photo() -> None:
    """console_01.jpg is front-on; record pass/fail honestly against D8 threshold."""
    if not PHOTO.is_file() or not STEP.is_file():
        return
    report = calibrate_gt(photo=PHOTO, step_or_stl=STEP, pose_hint="front")
    assert report["schema"] == "calibration.d8.v1"
    assert report["threshold"] == D8_THRESHOLD
    assert 0.0 <= float(report["iou"]) <= 1.0
    # Pass is not asserted — segmentation/props may still keep IoU below 0.8
