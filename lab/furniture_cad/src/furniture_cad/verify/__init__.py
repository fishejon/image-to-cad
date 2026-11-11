from furniture_cad.verify.camera_fit import calibrate_gt, fit_camera_iou
from furniture_cad.verify.critic import verify_against_dims
from furniture_cad.verify.repair import repair_loop
from furniture_cad.verify.render_shaded import render_perspective_stub

__all__ = [
    "render_perspective_stub",
    "verify_against_dims",
    "repair_loop",
    "fit_camera_iou",
    "calibrate_gt",
]
