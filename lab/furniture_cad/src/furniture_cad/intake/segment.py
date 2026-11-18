"""Subject segmentation: SAM 2 (optional) → GrabCut → brightness last resort."""

from __future__ import annotations

from typing import Any

import numpy as np


def _central_box(h: int, w: int, frac: float = 0.8) -> tuple[int, int, int, int]:
    """Return (x, y, bw, bh) covering the central ``frac`` of the image."""
    bw = max(1, int(round(w * frac)))
    bh = max(1, int(round(h * frac)))
    x = max(0, (w - bw) // 2)
    y = max(0, (h - bh) // 2)
    return x, y, bw, bh


def _largest_center_component(mask: np.ndarray) -> np.ndarray:
    """Keep the largest connected True blob that touches the image center (4-connected)."""
    try:
        import cv2
    except ImportError:
        return mask
    m = (mask.astype(np.uint8) * 255)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=4)
    if n <= 1:
        return mask
    cy, cx = mask.shape[0] // 2, mask.shape[1] // 2
    center_label = int(labels[cy, cx])
    # Prefer the component under the center; else the largest by area
    best = 0
    best_area = -1
    for lab in range(1, n):
        area = int(stats[lab, cv2.CC_STAT_AREA])
        if lab == center_label:
            return labels == lab
        if area > best_area:
            best_area = area
            best = lab
    return labels == best if best else mask


def _brightness_mask(img: Any) -> dict[str, Any]:
    from PIL import Image, ImageFilter

    arr = np.asarray(img.convert("L"), dtype=np.float32)
    bg = float(np.percentile(arr, 92))
    mask = arr < (bg - 12)
    fill = float(mask.mean())
    quality = "ok"
    if fill < 0.02 or fill > 0.75:
        thr = float(arr.mean() + 0.15 * arr.std())
        mask = arr < thr
        fill = float(mask.mean())
        quality = "fallback_adaptive"
    pil = Image.fromarray((mask.astype(np.uint8) * 255))
    pil = pil.filter(ImageFilter.MaxFilter(3))
    mask = np.asarray(pil) > 127
    mask = _largest_center_component(mask)
    fill = float(mask.mean())
    q = 1.0 - abs(fill - 0.25) / 0.25
    q = float(max(0.05, min(1.0, q)))
    return {
        "mask": mask,
        "fill": fill,
        "quality": "low" if quality == "fallback_adaptive" else quality,
        "score": round(q * 0.5, 3),  # brightness is last-resort → capped confidence
        "conf": round(q * 0.5, 3),
        "method": "brightness",
    }


def _grabcut_mask(img: Any) -> dict[str, Any] | None:
    try:
        import cv2
    except ImportError:
        return None
    arr = np.asarray(img.convert("RGB"))
    h, w = arr.shape[:2]
    x, y, bw, bh = _central_box(h, w, 0.8)
    mask = np.zeros((h, w), np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    rect = (x, y, bw, bh)
    try:
        cv2.grabCut(arr, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
    except Exception:
        return None
    binary = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), True, False)
    binary = _largest_center_component(binary)
    fill = float(binary.mean())
    if fill < 0.02 or fill > 0.85:
        return None
    # Confidence from fill compactness near center
    q = 1.0 - abs(fill - 0.22) / 0.22
    q = float(max(0.4, min(0.95, q)))
    return {
        "mask": binary,
        "fill": fill,
        "quality": "ok" if q >= 0.6 else "low",
        "score": round(q, 3),
        "conf": round(q, 3),
        "method": "grabcut",
    }


def _sam2_mask(img: Any) -> dict[str, Any] | None:
    """Optional SAM 2 path. Returns None when the package/weights are unavailable."""
    try:
        # Prefer the official sam2 package when present; otherwise skip.
        import sam2  # type: ignore  # noqa: F401
    except ImportError:
        return None
    # Full SAM 2 wiring (weights + predictor) is environment-specific; treat as not ready
    # until worker ships weights. Spec allows GrabCut fallback below conf 0.8.
    return None


def segment_subject(img: Any) -> dict[str, Any]:
    """Segment the furniture subject. Prefer SAM 2 → GrabCut → brightness."""
    for fn in (_sam2_mask, _grabcut_mask):
        out = fn(img)
        if out is not None and float(out.get("conf") or 0) >= 0.4:
            if float(out.get("conf") or 0) >= 0.8 or out["method"] != "sam2":
                return out
            # SAM present but low conf → still try GrabCut
            continue
    return _brightness_mask(img)


# Back-compat alias used by older tests / callers
def segment_mask(img: Any) -> dict[str, Any]:
    return segment_subject(img)
