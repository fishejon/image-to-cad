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


def _letterbox_gray(img: Any, size: tuple[int, int]) -> Any:
    """Resize preserving aspect ratio; pad with near-white so studio thresholds still work."""
    from PIL import Image

    tw, th = size
    w, h = img.size
    scale = min(tw / max(w, 1), th / max(h, 1))
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    resized = img.resize((nw, nh), Image.Resampling.BILINEAR)
    canvas = Image.new("L", size, 245)
    canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
    return canvas


def _largest_component(mask: np.ndarray) -> np.ndarray:
    """Keep the largest connected True blob (4-connected)."""
    from scipy import ndimage

    labeled, n = ndimage.label(mask)
    if n <= 1:
        return mask
    counts = np.bincount(labeled.ravel())
    counts[0] = 0
    keep = int(counts.argmax())
    return labeled == keep


def _calibration_photo_mask(path: Path, size: tuple[int, int] = (384, 384)) -> np.ndarray:
    """Studio-aware mask: letterboxed, polarity search, largest connected blob."""
    from PIL import Image, ImageFilter, ImageOps

    img = Image.open(path).convert("L")
    img = ImageOps.exif_transpose(img)
    img = _letterbox_gray(img, size)
    arr = np.asarray(img, dtype=np.float32)
    candidates: list[np.ndarray] = []
    # Pure white / near-white studio backdrop (best for D8)
    corner = float(np.mean([arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]]))
    if corner > 220:
        # Strict white studio — drop soft floor shadow by using high threshold + cleanup
        candidates.append(arr < 248)
        candidates.append(arr < 240)
        candidates.append(arr < float(np.percentile(arr, 85)))
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
        m = _largest_component(m)
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
        best = _largest_component(best)
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
    use_hull: bool = False,
) -> np.ndarray:
    """Rasterize a filled silhouette from projected triangles (true outline).

    ``use_hull=True`` falls back to the old convex-hull behaviour (fills leg gaps).
    Perspective foreshortening is preserved: we fit scale from the orthographic
    AABB of the mesh, then apply the same mm→px scale to the perspective projection
    so FOV / cam distance actually change the mask.
    """
    from PIL import Image, ImageDraw

    R = _rot_yaw_pitch(yaw_deg, pitch_deg)
    # Center mesh
    c = (verts.min(axis=0) + verts.max(axis=0)) * 0.5
    v = (verts - c) @ R.T
    # Camera looks along −Y in camera space after rotation → use X,Z for image, Y as depth
    x = v[:, 0]
    depth = v[:, 1]
    z = v[:, 2]
    # Orthographic extents set a stable mm→px scale (FOV-independent)
    ox_min, ox_max = float(x.min()), float(x.max())
    oz_min, oz_max = float(z.min()), float(z.max())
    ospan = max(ox_max - ox_min, oz_max - oz_min, 1e-6)
    ocx, ocz = (ox_min + ox_max) * 0.5, (oz_min + oz_max) * 0.5
    half = ospan * (0.5 + pad)

    if perspective:
        span = float(max(x.max() - x.min(), z.max() - z.min(), 1e-6))
        cam_y = float(depth.min()) - cam_dist_factor * span
        f = 1.0 / max(1e-6, math.tan(math.radians(fov_deg) * 0.5))
        # Normalize so the central depth projects at scale ~1 relative to ortho
        depth_c = float(np.median(depth))
        f_ref = max(depth_c - cam_y, 1e-3)
        denom = np.maximum(depth - cam_y, 1e-3)
        xp = (x / denom) * f * f_ref
        zp = (z / denom) * f * f_ref
    else:
        xp, zp = x, z

    w, h = size
    xs = (xp - (ocx - half)) / (2 * half) * (w - 1)
    zs = (1.0 - (zp - (ocz - half)) / (2 * half)) * (h - 1)

    img = Image.new("1", size, 0)
    draw = ImageDraw.Draw(img)
    if use_hull:
        pts = np.column_stack([xs, zs])
        try:
            from scipy.spatial import ConvexHull

            hull = ConvexHull(pts)
            poly = [(int(pts[i, 0]), int(pts[i, 1])) for i in hull.vertices]
            draw.polygon(poly, fill=1)
        except Exception:
            use_hull = False
    if not use_hull:
        # All triangles — thin-shell STEP faces are often backfacing from one side.
        for a, b, c_i in faces:
            draw.polygon(
                [
                    (int(xs[a]), int(zs[a])),
                    (int(xs[b]), int(zs[b])),
                    (int(xs[c_i]), int(zs[c_i])),
                ],
                fill=1,
            )
    mask = np.asarray(img, dtype=bool)
    if not use_hull:
        # Close hairline gaps in the shell, then fill enclosed voids (carcass interior)
        # without filling the open space between legs (those touch the image border).
        from scipy.ndimage import binary_closing, binary_fill_holes

        mask = binary_closing(mask, iterations=2)
        mask = binary_fill_holes(mask)
    return mask


def _iou(ref: np.ndarray, model: np.ndarray, *, max_shift_frac: float = 0.12) -> tuple[float, dict[str, Any]]:
    h, w = ref.shape
    max_dx = max(1, int(round(w * max_shift_frac)))
    max_dy = max(1, int(round(h * max_shift_frac)))
    step = max(1, max_dx // 4)
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
    # Fine refine around best
    if best > 0:
        bdx, bdy = int(meta["dx"]), int(meta["dy"])
        for dy in range(bdy - step, bdy + step + 1):
            for dx in range(bdx - step, bdx + step + 1):
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
    use_persp = perspective or (pose_hint is not None and pose_hint != "front")
    fov_grid = [28.0, 35.0, 45.0, 60.0] if use_persp else [35.0]
    dist_grid = [2.2, 2.8, 3.6] if use_persp else [2.8]

    best: dict[str, Any] = {"iou": 0.0}
    for yaw in yaw_grid:
        for pitch in pitch_grid:
            for fov in fov_grid:
                for dist in dist_grid:
                    mask = _project_mask(
                        verts,
                        faces,
                        yaw_deg=yaw,
                        pitch_deg=pitch,
                        size=size,
                        perspective=use_persp or abs(yaw) > 5,
                        fov_deg=fov,
                        cam_dist_factor=dist,
                        use_hull=False,
                    )
                    iou, align = _iou(ref, mask)
                    if iou > best["iou"]:
                        best = {
                            "iou": round(iou, 4),
                            "yaw_deg": yaw,
                            "pitch_deg": pitch,
                            "fov_deg": fov,
                            "cam_dist_factor": dist,
                            "perspective": use_persp or abs(yaw) > 5,
                            "align": align,
                            "rating": rating_for_iou(iou),
                            "silhouette": "triangles",
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
