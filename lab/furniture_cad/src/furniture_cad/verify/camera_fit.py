"""Camera-matched silhouette IoU (P0 / D8).

Fits yaw, pitch, FOV, and translation to maximize IoU vs a photo mask.
Scale is held fixed to the known size (AABB of the mesh maps to the frame).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from furniture_cad.silhouette import _photo_mask, _shift, rating_for_iou

D8_THRESHOLD = 0.8


def _calibration_photo_mask(path: Path, size: tuple[int, int] = (384, 384)) -> np.ndarray:
    """Studio-aware mask: try both polarities and keep the mid-fill connected blob."""
    from PIL import Image, ImageFilter, ImageOps

    img = Image.open(path).convert("L")
    img = ImageOps.exif_transpose(img)
    img = img.resize(size, Image.Resampling.BILINEAR)
    arr = np.asarray(img, dtype=np.float32)
    candidates: list[np.ndarray] = []
    # Pure white / near-white studio backdrop (best for D8)
    corner = float(np.mean([arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]]))
    if corner > 220:
        candidates.append(arr < 245)
        candidates.append(arr < 235)
    # Dark subject on light bg
    bg = float(np.percentile(arr, 90))
    candidates.append(arr < (bg - 15))
    # Light subject on dark bg
    fg = float(np.percentile(arr, 10))
    candidates.append(arr > (fg + 15))
    # Adaptive
    thr = float(arr.mean())
    candidates.append(arr < thr)
    candidates.append(arr > thr)

    best = None
    best_score = -1.0
    for mask in candidates:
        # cleanup
        pil = Image.fromarray((mask.astype(np.uint8) * 255))
        pil = pil.filter(ImageFilter.MaxFilter(3))
        pil = pil.filter(ImageFilter.MinFilter(3))
        m = np.asarray(pil) > 127
        fill = float(m.mean())
        if fill < 0.02 or fill > 0.45:
            continue
        # Prefer compact central mass
        ys, xs = np.where(m)
        if len(xs) == 0:
            continue
        cx, cy = xs.mean() / size[0], ys.mean() / size[1]
        center_bonus = 1.0 - abs(cx - 0.5) - abs(cy - 0.55)
        score = (1.0 - abs(fill - 0.18)) + 0.3 * center_bonus
        if score > best_score:
            best_score = score
            best = m
    if best is None:
        best = _photo_mask(path, size=size)
        # If still huge, take inverted if that is mid-fill
        fill = float(best.mean())
        if fill > 0.45:
            inv = ~best
            if 0.02 < float(inv.mean()) < 0.45:
                best = inv
    return best


def _load_mesh(stl: Path, *, max_faces: int = 12000) -> tuple[np.ndarray, np.ndarray]:
    import trimesh

    mesh = trimesh.load_mesh(str(stl), force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(g for g in mesh.geometry.values()))
    # Decimate for camera search — silhouette quality is enough for D8
    try:
        if len(mesh.faces) > max_faces:
            mesh = mesh.simplify_quadric_decimation(max_faces)
    except Exception:
        # Fallback: random face subset
        if len(mesh.faces) > max_faces:
            idx = np.linspace(0, len(mesh.faces) - 1, max_faces).astype(int)
            mesh = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces[idx], process=False)
    return np.asarray(mesh.vertices, dtype=np.float64), np.asarray(mesh.faces, dtype=np.int64)


def _rot_yaw_pitch(yaw_deg: float, pitch_deg: float) -> np.ndarray:
    y = math.radians(yaw_deg)
    p = math.radians(pitch_deg)
    cy, sy = math.cos(y), math.sin(y)
    cp, sp = math.cos(p), math.sin(p)
    # yaw about Z, then pitch about X
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]], dtype=np.float64)
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]], dtype=np.float64)
    return rx @ rz


def _project_mask(
    verts: np.ndarray,
    faces: np.ndarray,
    *,
    yaw_deg: float,
    pitch_deg: float,
    size: tuple[int, int] = (384, 384),
    pad: float = 0.08,
    perspective: bool = True,
    fov_deg: float = 35.0,
    cam_dist_factor: float = 2.8,
) -> np.ndarray:
    """Rasterize projected triangles into a boolean mask (scale fixed via AABB fit)."""
    from PIL import Image, ImageDraw

    R = _rot_yaw_pitch(yaw_deg, pitch_deg)
    # Center mesh
    c = (verts.min(axis=0) + verts.max(axis=0)) * 0.5
    v = (verts - c) @ R.T
    # Camera looks along −Y in camera space after rotation → use X,Z for image, Y as depth
    x = v[:, 0]
    depth = v[:, 1]
    z = v[:, 2]
    if perspective:
        # Push camera back along +depth so object is in front
        span = float(max(x.max() - x.min(), z.max() - z.min(), 1e-6))
        cam_y = float(depth.min()) - cam_dist_factor * span
        # Simple pinhole: x' = x / (depth - cam_y) * f
        f = 1.0 / max(1e-6, math.tan(math.radians(fov_deg) * 0.5))
        denom = np.maximum(depth - cam_y, 1e-3)
        xp = (x / denom) * f
        zp = (z / denom) * f
    else:
        xp, zp = x, z

    w, h = size
    xmin, xmax = float(xp.min()), float(xp.max())
    zmin, zmax = float(zp.min()), float(zp.max())
    span = max(xmax - xmin, zmax - zmin, 1e-6)
    cx, cz = (xmin + xmax) * 0.5, (zmin + zmax) * 0.5
    half = span * (0.5 + pad)

    def to_px(xv: np.ndarray, zv: np.ndarray) -> list[tuple[int, int]]:
        xs = (xv - (cx - half)) / (2 * half) * (w - 1)
        zs = (1.0 - (zv - (cz - half)) / (2 * half)) * (h - 1)
        return list(zip(xs.astype(int).tolist(), zs.astype(int).tolist()))

    img = Image.new("1", size, 0)
    draw = ImageDraw.Draw(img)
    for a, b, c_i in faces:
        draw.polygon(to_px(xp[[a, b, c_i]], zp[[a, b, c_i]]), fill=1)
    return np.asarray(img, dtype=bool)


def _iou(ref: np.ndarray, model: np.ndarray, *, max_shift_frac: float = 0.05) -> tuple[float, dict[str, Any]]:
    h, w = ref.shape
    max_dx = max(1, int(round(w * max_shift_frac)))
    max_dy = max(1, int(round(h * max_shift_frac)))
    step = max(1, max_dx // 3)
    best = 0.0
    meta: dict[str, Any] = {"dx": 0, "dy": 0}
    for dy in range(-max_dy, max_dy + 1, step):
        for dx in range(-max_dx, max_dx + 1, step):
            m = _shift(model, dx, dy)
            inter = np.logical_and(ref, m).sum()
            union = np.logical_or(ref, m).sum()
            if union == 0:
                continue
            iou = float(inter / union)
            if iou > best:
                best = iou
                meta = {"dx": dx, "dy": dy, "inter": int(inter), "union": int(union)}
    return best, meta


def fit_camera_iou(
    photo: Path | str,
    stl: Path | str,
    *,
    size: tuple[int, int] = (384, 384),
    pose_hint: str | None = None,
    coarse: bool = True,
) -> dict[str, Any]:
    """Multi-start camera fit; scale fixed via AABB → frame mapping."""
    photo = Path(photo)
    stl = Path(stl)
    ref = _calibration_photo_mask(photo, size=size)
    verts, faces = _load_mesh(stl)

    # Seed yaw from pose hint
    if pose_hint and "three_quarter" in pose_hint:
        yaw0 = 35.0 if "right" in pose_hint else -35.0
        perspective = True
    elif pose_hint == "side":
        yaw0 = 90.0
        perspective = True
    else:
        yaw0 = 0.0
        perspective = False if pose_hint == "front" else True

    if pose_hint and "three_quarter" in pose_hint:
        yaw_grid = [yaw0 - 25, yaw0 - 10, yaw0, yaw0 + 10, yaw0 + 25] if coarse else [yaw0 - 8, yaw0, yaw0 + 8]
        pitch_grid = [-5.0, 5.0, 15.0, 25.0, 35.0] if coarse else [5.0, 15.0, 25.0]
    else:
        yaw_grid = [yaw0 - 20, yaw0, yaw0 + 20] if coarse else [yaw0 - 8, yaw0, yaw0 + 8]
        pitch_grid = [0.0, 12.0, 24.0] if coarse else [0.0, 8.0, 16.0]
    fov_grid = [28.0, 35.0, 45.0] if perspective else [35.0]

    best: dict[str, Any] = {"iou": 0.0}
    for yaw in yaw_grid:
        for pitch in pitch_grid:
            for fov in fov_grid:
                mask = _project_mask(
                    verts,
                    faces,
                    yaw_deg=yaw,
                    pitch_deg=pitch,
                    size=size,
                    perspective=perspective or abs(yaw) > 5,
                    fov_deg=fov,
                )
                iou, align = _iou(ref, mask)
                if iou > best["iou"]:
                    best = {
                        "iou": round(iou, 4),
                        "yaw_deg": yaw,
                        "pitch_deg": pitch,
                        "fov_deg": fov,
                        "perspective": perspective or abs(yaw) > 5,
                        "align": align,
                        "rating": rating_for_iou(iou),
                    }
    best["schema"] = "camera_fit.v1"
    best["photo"] = str(photo)
    best["stl"] = str(stl)
    best["pose_hint"] = pose_hint
    return best


def calibrate_gt(
    *,
    photo: Path | str,
    step_or_stl: Path | str,
    pose_hint: str | None = None,
    threshold: float = D8_THRESHOLD,
) -> dict[str, Any]:
    """D8: GT solid vs its photo. Pass only if IoU ≥ threshold."""
    from furniture_cad.eval.console_gt import ensure_gt_stl

    stl = Path(step_or_stl)
    if stl.suffix.lower() in (".step", ".stp"):
        stl = ensure_gt_stl()
    fit = fit_camera_iou(photo, stl, pose_hint=pose_hint)
    passed = float(fit["iou"]) >= float(threshold)
    return {
        "schema": "calibration.d8.v1",
        "passed": passed,
        "threshold": threshold,
        "iou": fit["iou"],
        "rating": fit.get("rating"),
        "camera": {k: fit[k] for k in ("yaw_deg", "pitch_deg", "fov_deg", "perspective", "align") if k in fit},
        "pose_hint": pose_hint,
        "gate_note": (
            None
            if passed
            else "IoU untrusted for gates — use part/dimension metrics until D8 calibration passes"
        ),
    }
