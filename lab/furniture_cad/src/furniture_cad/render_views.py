"""Orthographic PNG views of an STL for the tool-use loop (not photoreal)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def _load_mesh(stl_path: Path):
    import trimesh

    mesh = trimesh.load_mesh(str(stl_path), force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(g for g in mesh.geometry.values()))
    return mesh


def _project_uv(
    mesh,
    u: np.ndarray,
    v: np.ndarray,
    *,
    size: tuple[int, int] = (384, 384),
    pad: float = 0.06,
) -> np.ndarray:
    from PIL import Image, ImageDraw

    faces = np.asarray(mesh.faces)
    w, h = size
    umin, umax = float(u.min()), float(u.max())
    vmin, vmax = float(v.min()), float(v.max())
    span = max(umax - umin, vmax - vmin, 1e-6)
    cu, cv = (umin + umax) / 2, (vmin + vmax) / 2
    half = span * (0.5 + pad)

    def to_px(uu: np.ndarray, vv: np.ndarray) -> list[tuple[int, int]]:
        xs = (uu - (cu - half)) / (2 * half) * (w - 1)
        ys = (1.0 - (vv - (cv - half)) / (2 * half)) * (h - 1)
        return list(zip(xs.astype(int).tolist(), ys.astype(int).tolist()))

    img = Image.new("1", size, 0)
    draw = ImageDraw.Draw(img)
    for a, b, c in faces:
        draw.polygon(to_px(u[[a, b, c]], v[[a, b, c]]), fill=1)
    return np.asarray(img, dtype=bool)


def _mask_to_png(mask: np.ndarray, path: Path, *, fill: tuple[int, int, int] = (180, 140, 90)) -> Path:
    from PIL import Image

    h, w = mask.shape
    rgba = np.zeros((h, w, 3), dtype=np.uint8)
    rgba[:] = (245, 242, 236)
    rgba[mask] = fill
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGB").save(path)
    return path


def render_stl_views(
    stl_path: Path | str,
    out_dir: Path | str,
    views: list[str],
    *,
    size: tuple[int, int] = (384, 384),
) -> dict[str, Any]:
    """Write PNG silhouettes for requested views. Returns paths + meta."""
    stl_path = Path(stl_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    mesh = _load_mesh(stl_path)
    pts = np.asarray(mesh.vertices)
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    written: dict[str, str] = {}
    for raw in views:
        view = str(raw).lower().strip()
        if view == "front":
            mask = _project_uv(mesh, x, z, size=size)
        elif view == "back":
            mask = _project_uv(mesh, -x, z, size=size)
        elif view == "side":
            mask = _project_uv(mesh, y, z, size=size)
        elif view == "top":
            mask = _project_uv(mesh, x, y, size=size)
        elif view == "iso":
            mask = _project_uv(mesh, (x + y) / np.sqrt(2.0), z, size=size)
        else:
            continue
        path = out_dir / f"{view}.png"
        _mask_to_png(mask, path)
        written[view] = str(path)
    return {"ok": True, "views": written, "size": list(size), "stl": str(stl_path)}


def overlay_masks_png(ref_mask: np.ndarray, model_mask: np.ndarray, path: Path) -> Path:
    """Red = photo only, green = model only, amber = overlap."""
    from PIL import Image

    h, w = ref_mask.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[:] = 30
    only_ref = ref_mask & ~model_mask
    only_model = model_mask & ~ref_mask
    both = ref_mask & model_mask
    rgb[only_ref] = (200, 60, 60)
    rgb[only_model] = (60, 180, 90)
    rgb[both] = (220, 180, 60)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb, "RGB").save(path)
    return path
