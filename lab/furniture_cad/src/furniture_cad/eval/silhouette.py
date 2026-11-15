"""Solid-vs-solid orthographic silhouette IoU for case-run scoring."""

from __future__ import annotations

from typing import Any

import numpy as np


def _solid_mask(solid: Any, *, view: str, size: tuple[int, int], pad: float = 0.05) -> np.ndarray:
    """Rasterize a build123d solid/compound to a boolean silhouette mask."""
    from PIL import Image, ImageDraw

    solids = list(solid.solids()) if hasattr(solid, "solids") else [solid]
    tris: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    for s in solids:
        verts, faces = s.tessellate(0.8)
        v = np.array([[p.X, p.Y, p.Z] for p in verts], dtype=np.float64)
        for f in faces:
            tris.append((v[f[0]], v[f[1]], v[f[2]]))
    if not tris:
        return np.zeros(size, dtype=bool)

    pts = np.vstack(tris)
    if view == "side":
        # look along +X: image axes (Y, Z)
        u, w = pts[:, 1], pts[:, 2]
        pick = lambda a: (a[1], a[2])  # noqa: E731
    else:
        # front: look along -Y: image axes (X, Z)
        u, w = pts[:, 0], pts[:, 2]
        pick = lambda a: (a[0], a[2])  # noqa: E731

    umin, umax = float(u.min()), float(u.max())
    wmin, wmax = float(w.min()), float(w.max())
    span = max(umax - umin, wmax - wmin, 1e-6)
    uc, wc = (umin + umax) * 0.5, (wmin + wmax) * 0.5
    half = span * (0.5 + pad)
    W, H = size

    def to_px(p0, p1, p2):
        out = []
        for p in (p0, p1, p2):
            uu, ww = pick(p)
            x = (uu - (uc - half)) / (2 * half) * (W - 1)
            y = (1.0 - (ww - (wc - half)) / (2 * half)) * (H - 1)
            out.append((int(x), int(y)))
        return out

    img = Image.new("1", size, 0)
    draw = ImageDraw.Draw(img)
    for a, b, c in tris:
        draw.polygon(to_px(a, b, c), fill=1)
    return np.asarray(img, dtype=bool)


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = int(np.logical_and(a, b).sum())
    union = int(np.logical_or(a, b).sum())
    return inter / union if union else 0.0


def silhouette_iou(
    a: Any,
    b: Any,
    *,
    view: str = "front",
    mirror_ok: bool = False,
    size: tuple[int, int] = (256, 256),
) -> dict[str, Any]:
    """Orthographic IoU between two build123d solids/compounds.

    ``view`` is ``front`` (along −Y) or ``side`` (along +X). When ``mirror_ok``,
    also try a horizontally flipped model mask and keep the better score.
    """
    ref = _solid_mask(a, view=view, size=size)
    model = _solid_mask(b, view=view, size=size)
    iou = _iou(ref, model)
    mirrored = False
    if mirror_ok:
        flip = np.fliplr(model)
        iou2 = _iou(ref, flip)
        if iou2 > iou:
            iou, mirrored = iou2, True
    return {"iou": round(float(iou), 4), "view": view, "mirrored": mirrored, "size": list(size)}
