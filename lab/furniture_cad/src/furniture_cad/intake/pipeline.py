"""Intake pipeline — segment, rectify, scale → intake.v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from furniture_cad.intake.rectify import DEFAULT_MARKER_MM, detect_aruco, rectify_image
from furniture_cad.intake.scale import compute_scale
from furniture_cad.intake.segment import segment_subject


def _orient_and_load(path: Path) -> tuple[Any, dict[str, Any]]:
    from PIL import Image, ImageOps

    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    meta = {"mode": img.mode, "size": list(img.size), "exif_oriented": True}
    return img.convert("RGB"), meta


def segment_mask(img: Any) -> dict[str, Any]:
    """Public alias kept for older callers/tests."""
    return segment_subject(img)


def try_rectify(img: Any, *, mask: np.ndarray | None = None) -> dict[str, Any]:
    """Public alias — prefer ``rectify_image`` for new code."""
    return rectify_image(img, mask=mask)


def intake_photo(
    path: Path | str,
    *,
    known_mm: dict[str, float] | None = None,
    marker_size_mm: float = DEFAULT_MARKER_MM,
    work_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Run intake.v2: orient → segment → rectify → scale.

    Optional ``work_dir`` writes rectified image and mask artifacts.
    """
    path = Path(path)
    img, meta = _orient_and_load(path)
    seg = segment_subject(img)
    mask = seg["mask"]

    rect = rectify_image(img, mask=mask, marker_size_mm=marker_size_mm)
    rect_img = rect.get("image") or img
    rect_mask = rect.get("mask") if rect.get("mask") is not None else mask

    # Re-score fill on rectified mask
    if isinstance(rect_mask, np.ndarray):
        seg = {**seg, "fill": float(rect_mask.mean())}

    aruco_meta = dict(rect.get("aruco") or {})
    # Re-detect marker on the rectified image so px_per_mm matches rectified pixels
    if aruco_meta.get("found"):
        again = detect_aruco(rect_img, marker_size_mm=marker_size_mm)
        if again is not None:
            aruco_meta = {
                "dict": again["dict"],
                "id": again["id"],
                "size_mm": again["size_mm"],
                "found": True,
                "corners_px": again["corners_px"].tolist(),
            }
    scale = compute_scale(
        mask=rect_mask if isinstance(rect_mask, np.ndarray) else None,
        known_mm=known_mm,
        aruco=aruco_meta if aruco_meta.get("found") else None,
        image_size=tuple(getattr(rect_img, "size", meta["size"])),
    )
    asks = list(scale.pop("asks", []) or [])

    artifacts: dict[str, Any] = {"rectified_image_path": None, "mask_path": None}
    if work_dir is not None:
        work = Path(work_dir)
        work.mkdir(parents=True, exist_ok=True)
        from PIL import Image

        rpath = work / "rectified.png"
        mpath = work / "mask.png"
        if hasattr(rect_img, "save"):
            rect_img.save(rpath)
        else:
            Image.fromarray(np.asarray(rect_img)).save(rpath)
        Image.fromarray((np.asarray(rect_mask).astype(np.uint8) * 255)).save(mpath)
        artifacts["rectified_image_path"] = str(rpath)
        artifacts["mask_path"] = str(mpath)

    return {
        "schema": "intake.v2",
        "path": str(path),
        "meta": meta,
        "segmentation": {k: v for k, v in seg.items() if k != "mask"},
        "rectify": {
            k: v
            for k, v in rect.items()
            if k not in ("image", "mask")
        },
        "scale": scale,
        "asks": asks,
        "artifacts": artifacts,
        "mask": rect_mask,
        "image": rect_img,
    }
