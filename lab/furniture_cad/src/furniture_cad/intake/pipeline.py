"""Intake pipeline stubs — brightness seg fallback; OpenCV rectify when available."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def _orient_and_load(path: Path) -> tuple[Any, dict[str, Any]]:
    from PIL import Image, ImageOps

    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    meta = {"mode": img.mode, "size": list(img.size), "exif_oriented": True}
    return img.convert("RGB"), meta


def segment_mask(img: Any) -> dict[str, Any]:
    """Promptable-SAM placeholder: improved brightness threshold with quality score."""
    from PIL import ImageFilter

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
    # Light cleanup
    from PIL import Image

    pil = Image.fromarray((mask.astype(np.uint8) * 255))
    pil = pil.filter(ImageFilter.MaxFilter(3))
    mask = np.asarray(pil) > 127
    # Quality: prefer mid fill
    q = 1.0 - abs(fill - 0.25) / 0.25
    q = float(max(0.05, min(1.0, q)))
    return {"mask": mask, "fill": fill, "quality": quality, "score": round(q, 3), "method": "brightness_v1_pending_sam"}


def try_rectify(img: Any) -> dict[str, Any]:
    """Estimate dominant lines / vanishing; return fronto-parallel when OpenCV available."""
    try:
        import cv2  # type: ignore
    except ImportError:
        return {
            "rectified": False,
            "confidence": "low",
            "reason": "opencv_not_installed",
            "image": img,
        }
    arr = np.asarray(img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=40, maxLineGap=10)
    n = 0 if lines is None else len(lines)
    # Phase 0: detect only — full homography in Phase 1
    return {
        "rectified": False,
        "confidence": "low" if n < 8 else "medium",
        "reason": "homography_deferred",
        "hough_lines": int(n),
        "image": img,
    }


def intake_photo(path: Path | str, *, known_mm: dict[str, float] | None = None) -> dict[str, Any]:
    path = Path(path)
    img, meta = _orient_and_load(path)
    seg = segment_mask(img)
    rect = try_rectify(img)
    scale = None
    if known_mm and known_mm.get("w") and meta["size"][0]:
        # Rough px_per_mm from overall width spanning image (assumes subject fills ~70% width)
        scale = {
            "px_per_mm": round((meta["size"][0] * 0.70) / float(known_mm["w"]), 4),
            "scale_source": f"user:W={known_mm['w']}",
            "confidence": 0.5,
            "note": "coarse fill-fraction estimate until rectified bbox",
        }
    return {
        "schema": "intake.v1",
        "path": str(path),
        "meta": meta,
        "segmentation": {k: v for k, v in seg.items() if k != "mask"},
        "rectify": {k: v for k, v in rect.items() if k != "image"},
        "scale": scale,
        "mask": seg["mask"],
        "image": rect.get("image") or img,
    }
