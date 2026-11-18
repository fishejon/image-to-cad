"""Fronto-parallel rectification via ArUco marker or LSD line keystone correction."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

# Spec: DICT_4X4_50, id 7
ARUCO_DICT_NAME = "DICT_4X4_50"
ARUCO_ID = 7
DEFAULT_MARKER_MM = 100.0
MAX_RESIDUAL_ANGLE_DEG = 3.0


def _aruco_dict():
    import cv2

    return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, ARUCO_DICT_NAME))


def detect_aruco(
    img: Any,
    *,
    marker_id: int = ARUCO_ID,
    marker_size_mm: float = DEFAULT_MARKER_MM,
) -> dict[str, Any] | None:
    """Return marker corners (px) and size if the configured ArUco id is found."""
    try:
        import cv2
    except ImportError:
        return None
    arr = np.asarray(img.convert("RGB") if hasattr(img, "convert") else img)
    if arr.ndim == 3 and arr.shape[2] == 3:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    else:
        gray = arr
    dictionary = _aruco_dict()
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(dictionary, params)
    corners, ids, _ = detector.detectMarkers(gray)
    if ids is None or len(ids) == 0:
        return None
    ids_flat = ids.flatten().tolist()
    if marker_id not in ids_flat:
        return None
    idx = ids_flat.index(marker_id)
    pts = corners[idx].reshape(4, 2).astype(np.float64)
    return {
        "corners_px": pts,
        "id": marker_id,
        "size_mm": float(marker_size_mm),
        "dict": ARUCO_DICT_NAME,
    }


def _homography_from_aruco(corners: np.ndarray, size_mm: float) -> np.ndarray:
    """Map marker corners to a fronto-parallel square of ``size_mm`` (in px space we use mm as units)."""
    import cv2

    # Destination: axis-aligned square. Pixel size is arbitrary for homography shape;
    # scale is recovered separately via marker_size_mm / side_length_px after warp.
    side = 200.0  # destination square side in px
    dst = np.array([[0, 0], [side, 0], [side, side], [0, side]], dtype=np.float64)
    H, _ = cv2.findHomography(corners, dst, method=0)
    return H


def _angle_of_line(x0: float, y0: float, x1: float, y1: float) -> float:
    return math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180.0


def _cluster_angles(angles: list[float], tol: float = 8.0) -> list[tuple[float, int]]:
    """Greedy cluster of angles in [0, 180); return (mean, count) sorted by count."""
    if not angles:
        return []
    used = [False] * len(angles)
    clusters: list[tuple[float, int]] = []
    for i, a in enumerate(angles):
        if used[i]:
            continue
        members = [a]
        used[i] = True
        for j in range(i + 1, len(angles)):
            if used[j]:
                continue
            d = abs(angles[j] - a)
            d = min(d, 180.0 - d)
            if d <= tol:
                used[j] = True
                members.append(angles[j])
        # Circular mean for nearly-horizontal lines near 0/180
        rad = [math.radians(m * 2) for m in members]
        mean = math.degrees(math.atan2(sum(math.sin(r) for r in rad), sum(math.cos(r) for r in rad))) / 2
        mean = mean % 180.0
        clusters.append((mean, len(members)))
    clusters.sort(key=lambda t: -t[1])
    return clusters


def _lsd_keystone_homography(img: Any, mask: np.ndarray | None) -> tuple[np.ndarray | None, float, str]:
    """Estimate a keystone-correcting homography from dominant H/V line families.

    Returns (H, residual_angle_deg, reason).
    """
    try:
        import cv2
    except ImportError:
        return None, 90.0, "opencv_not_installed"

    arr = np.asarray(img.convert("RGB") if hasattr(img, "convert") else img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    if mask is not None:
        gray = cv2.bitwise_and(gray, gray, mask=(mask.astype(np.uint8) * 255))

    # LSD (OpenCV 4+ createLineSegmentDetector)
    try:
        lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
        lines, *_ = lsd.detect(gray)
    except Exception:
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 60, minLineLength=min(h, w) // 10, maxLineGap=8)
        if lines is None:
            return None, 90.0, "no_lines"
        lines = lines.reshape(-1, 1, 4)

    if lines is None or len(lines) < 4:
        return None, 90.0, "too_few_lines"

    angles: list[float] = []
    segs: list[tuple[float, float, float, float]] = []
    for ln in lines:
        x0, y0, x1, y1 = map(float, ln.reshape(-1)[:4])
        length = math.hypot(x1 - x0, y1 - y0)
        if length < min(h, w) * 0.05:
            continue
        ang = _angle_of_line(x0, y0, x1, y1)
        # Snap near-H / near-V
        if min(abs(ang - 0), abs(ang - 180)) <= 12 or abs(ang - 90) <= 12:
            angles.append(ang)
            segs.append((x0, y0, x1, y1))

    clusters = _cluster_angles(angles, tol=10.0)
    if len(clusters) < 2:
        return None, 90.0, "need_two_line_families"

    # Pick the most horizontal and most vertical clusters
    horiz = min(clusters, key=lambda c: min(abs(c[0] - 0), abs(c[0] - 180)))
    vert = min(clusters, key=lambda c: abs(c[0] - 90))
    residual = abs(abs(vert[0] - horiz[0]) - 90.0)
    residual = min(residual, abs(180 - residual))  # fold

    # Build a mild affine that rotates so horiz → 0° and scales shear toward orthogonality
    # Using four image corners → slightly trapezoid-corrected corners from vanishing-ish estimate.
    # Practical Phase-1 approach: rotate by -horiz_angle so rails are horizontal.
    rot = -horiz[0] if horiz[0] <= 90 else (180 - horiz[0])
    if abs(rot) < 0.1 and residual < 1.0:
        # Already fronto-parallel enough
        H = np.eye(3, dtype=np.float64)
        return H, float(residual), "already_orthogonal"

    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, 1.0)
    H = np.vstack([M, [0, 0, 1]]).astype(np.float64)

    # Optional shear to push vertical family toward 90°
    shear = math.radians(vert[0] + rot - 90.0) * 0.5  # dampened
    S = np.array([[1.0, math.tan(shear), 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    H = S @ H
    return H, float(residual), "lsd_keystone"


def apply_homography(img: Any, H: np.ndarray, *, mask: np.ndarray | None = None) -> tuple[Any, np.ndarray | None]:
    """Warp image (and optional mask) with H; returns PIL image and warped mask."""
    import cv2
    from PIL import Image

    arr = np.asarray(img.convert("RGB") if hasattr(img, "convert") else img)
    h, w = arr.shape[:2]
    # Output size: bounding box of warped corners
    corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float64).reshape(-1, 1, 2)
    warped = cv2.perspectiveTransform(corners, H)
    xs = warped[:, 0, 0]
    ys = warped[:, 0, 1]
    min_x, max_x = float(xs.min()), float(xs.max())
    min_y, max_y = float(ys.min()), float(ys.max())
    out_w = max(1, int(math.ceil(max_x - min_x)))
    out_h = max(1, int(math.ceil(max_y - min_y)))
    T = np.array([[1, 0, -min_x], [0, 1, -min_y], [0, 0, 1]], dtype=np.float64)
    H2 = T @ H
    out = cv2.warpPerspective(arr, H2, (out_w, out_h), flags=cv2.INTER_LINEAR, borderValue=(245, 245, 245))
    out_mask = None
    if mask is not None:
        m = (mask.astype(np.uint8) * 255)
        wm = cv2.warpPerspective(m, H2, (out_w, out_h), flags=cv2.INTER_NEAREST, borderValue=0)
        out_mask = wm > 127
    return Image.fromarray(out), out_mask


def rectify_image(
    img: Any,
    *,
    mask: np.ndarray | None = None,
    marker_size_mm: float = DEFAULT_MARKER_MM,
    marker_id: int = ARUCO_ID,
) -> dict[str, Any]:
    """Produce a fronto-parallel image when possible.

    Sets ``retake_request`` when residual angle error exceeds 3°.
    """
    from PIL import Image

    if not isinstance(img, Image.Image):
        img = Image.fromarray(np.asarray(img))

    aruco = detect_aruco(img, marker_id=marker_id, marker_size_mm=marker_size_mm)
    if aruco is not None:
        H = _homography_from_aruco(aruco["corners_px"], aruco["size_mm"])
        rect_img, rect_mask = apply_homography(img, H, mask=mask)
        # After ArUco warp, residual should be near 0
        return {
            "rectified": True,
            "method": "aruco",
            "confidence": "high",
            "residual_angle_deg": 0.0,
            "retake_request": None,
            "homography": H.tolist(),
            "aruco": {
                "dict": aruco["dict"],
                "id": aruco["id"],
                "size_mm": aruco["size_mm"],
                "found": True,
                "corners_px": aruco["corners_px"].tolist(),
            },
            "image": rect_img,
            "mask": rect_mask if rect_mask is not None else mask,
            "reason": "aruco_homography",
        }

    H, residual, reason = _lsd_keystone_homography(img, mask)
    retake = None
    if residual > MAX_RESIDUAL_ANGLE_DEG:
        retake = (
            f"Photo keystone residual {residual:.1f}° exceeds {MAX_RESIDUAL_ANGLE_DEG}°. "
            "Retake front-on at mid-height with a 70–100 mm equivalent lens, or place the ArUco marker in frame."
        )
    if H is None:
        return {
            "rectified": False,
            "method": "none",
            "confidence": "low",
            "residual_angle_deg": residual,
            "retake_request": retake or "Could not estimate a keystone correction; retake front-on.",
            "homography": None,
            "aruco": {"dict": ARUCO_DICT_NAME, "id": marker_id, "size_mm": marker_size_mm, "found": False},
            "image": img,
            "mask": mask,
            "reason": reason,
        }

    rect_img, rect_mask = apply_homography(img, H, mask=mask)
    conf = "high" if residual <= 1.0 else ("medium" if residual <= MAX_RESIDUAL_ANGLE_DEG else "low")
    return {
        "rectified": retake is None,
        "method": "lsd_keystone",
        "confidence": conf,
        "residual_angle_deg": round(residual, 3),
        "retake_request": retake,
        "homography": H.tolist(),
        "aruco": {"dict": ARUCO_DICT_NAME, "id": marker_id, "size_mm": marker_size_mm, "found": False},
        "image": rect_img,
        "mask": rect_mask if rect_mask is not None else mask,
        "reason": reason,
    }
