"""Orthographic silhouette IoU: reference photo mask vs STL front projection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def _photo_mask(path: Path, size: tuple[int, int] = (512, 512)) -> np.ndarray:
    from PIL import Image, ImageFilter, ImageOps

    img = Image.open(path).convert("L")
    img = ImageOps.exif_transpose(img)
    img = img.resize(size, Image.Resampling.BILINEAR)
    arr = np.asarray(img, dtype=np.float32)
    # Studio: bright background. Subject = darker than high percentile.
    bg = float(np.percentile(arr, 92))
    mask = arr < (bg - 12)
    # If room photo (low bg), use adaptive-ish threshold around mean
    if mask.mean() < 0.02 or mask.mean() > 0.75:
        thr = float(arr.mean() + 0.15 * arr.std())
        mask = arr < thr
    # Light cleanup
    pil = Image.fromarray(mask.astype(np.uint8) * 255)
    pil = pil.filter(ImageFilter.MaxFilter(3))
    return np.asarray(pil) > 127


def _stl_front_mask(stl_path: Path, size: tuple[int, int] = (512, 512), pad: float = 0.05) -> np.ndarray:
    from PIL import Image, ImageDraw
    import trimesh

    mesh = trimesh.load_mesh(str(stl_path), force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(g for g in mesh.geometry.values()))
    pts = np.asarray(mesh.vertices)
    # Try both front conventions: look along −Y (X,Z) and look along +Y
    views = [
        (pts[:, 0], pts[:, 2]),
        (pts[:, 0], pts[:, 1]),
        (-pts[:, 0], pts[:, 2]),
    ]
    best = None
    best_fill = -1
    w, h = size
    faces = np.asarray(mesh.faces)
    for x, z in views:
        xmin, xmax = float(x.min()), float(x.max())
        zmin, zmax = float(z.min()), float(z.max())
        span = max(xmax - xmin, zmax - zmin, 1e-6)
        cx, cz = (xmin + xmax) / 2, (zmin + zmax) / 2
        half = span * (0.5 + pad)

        def to_px(xv: np.ndarray, zv: np.ndarray) -> list[tuple[int, int]]:
            xs = (xv - (cx - half)) / (2 * half) * (w - 1)
            zs = (1.0 - (zv - (cz - half)) / (2 * half)) * (h - 1)
            return list(zip(xs.astype(int).tolist(), zs.astype(int).tolist()))

        img = Image.new("1", size, 0)
        draw = ImageDraw.Draw(img)
        for a, b, c in faces:
            draw.polygon(to_px(x[[a, b, c]], z[[a, b, c]]), fill=1)
        mask = np.asarray(img, dtype=bool)
        fill = int(mask.sum())
        if fill > best_fill:
            best_fill = fill
            best = mask
    assert best is not None
    return best


def _shift(mask: np.ndarray, dx: int, dy: int) -> np.ndarray:
    out = np.zeros_like(mask)
    h, w = mask.shape
    x0, x1 = max(0, dx), min(w, w + dx)
    y0, y1 = max(0, dy), min(h, h + dy)
    sx0, sx1 = max(0, -dx), min(w, w - dx)
    sy0, sy1 = max(0, -dy), min(h, h - dy)
    out[y0:y1, x0:x1] = mask[sy0:sy1, sx0:sx1]
    return out


def _resize_mask(mask: np.ndarray, scale: float, size: tuple[int, int]) -> np.ndarray:
    from PIL import Image

    h, w = mask.shape
    nh, nw = max(1, int(h * scale)), max(1, int(w * scale))
    img = Image.fromarray(mask.astype(np.uint8) * 255).resize((nw, nh), Image.Resampling.NEAREST)
    canvas = Image.new("L", size, 0)
    ox, oy = (size[0] - nw) // 2, (size[1] - nh) // 2
    canvas.paste(img, (ox, oy))
    return np.asarray(canvas) > 127


def _aligned_iou(ref: np.ndarray, model: np.ndarray) -> tuple[float, dict[str, Any]]:
    best_iou = 0.0
    best_meta: dict[str, Any] = {"scale": 1.0, "dx": 0, "dy": 0}
    h, w = ref.shape
    for scale in (0.65, 0.75, 0.85, 0.95, 1.0, 1.05, 1.15, 1.25, 1.35):
        m0 = _resize_mask(model, scale, (w, h))
        for dy in (-60, -40, -20, -10, 0, 10, 20, 40, 60):
            for dx in (-60, -40, -20, -10, 0, 10, 20, 40, 60):
                m = _shift(m0, dx, dy)
                inter = np.logical_and(ref, m).sum()
                union = np.logical_or(ref, m).sum()
                if union == 0:
                    continue
                iou = float(inter / union)
                if iou > best_iou:
                    best_iou = iou
                    best_meta = {"scale": scale, "dx": dx, "dy": dy, "inter": int(inter), "union": int(union)}
    return best_iou, best_meta


def silhouette_iou(photo: Path | str, stl: Path | str, *, size: tuple[int, int] = (384, 384)) -> dict[str, Any]:
    photo = Path(photo)
    stl = Path(stl)
    ref = _photo_mask(photo, size)
    model = _stl_front_mask(stl, size)
    iou, align = _aligned_iou(ref, model)
    return {
        "iou": round(iou, 3),
        "ref_fill": int(ref.sum()),
        "model_fill": int(model.sum()),
        "size": list(size),
        "align": align,
        "method": "stl_front_orthographic_aligned_v2",
    }


def rating_for_iou(iou: float) -> str:
    if iou >= 0.7:
        return "Match"
    if iou >= 0.55:
        return "Close+"
    if iou >= 0.4:
        return "Close"
    return "Wrong"
