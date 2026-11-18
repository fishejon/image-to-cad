"""Capture guidance (D3) — front-on studio contract + ArUco marker."""

from __future__ import annotations

from typing import Any

from furniture_cad.intake.rectify import ARUCO_DICT_NAME, ARUCO_ID, DEFAULT_MARKER_MM


def capture_checklist(*, piece_class: str = "casegood") -> dict[str, Any]:
    views = [
        {
            "role": "front",
            "required": True,
            "hint": (
                "Front-on: camera at mid-height of the piece, subject ≥2 m away, "
                "70–100 mm equivalent focal length, plain light background"
            ),
        },
        {"role": "side", "required": False, "hint": "Straight side view if depth is ambiguous"},
        {"role": "three_quarter", "required": False, "hint": "45° for depth / legs (diagnostic)"},
    ]
    if piece_class.startswith("chair") or "organic" in piece_class:
        views.append({"role": "detail", "required": False, "hint": "Joinery / curve detail"})
        views.append(
            {
                "role": "top",
                "required": False,
                "hint": "Required for curved / organic pieces (WP10)",
            }
        )
    return {
        "schema": "capture_guidance.v2",
        "piece_class": piece_class,
        "require_known_dim": True,
        "known_dim_prompt": "Enter one overall dimension in inches or mm (width preferred).",
        "views": views,
        "aruco": {
            "required": True,
            "dict": ARUCO_DICT_NAME,
            "id": ARUCO_ID,
            "size_mm": DEFAULT_MARKER_MM,
            "placement": "Floor plane in front of the piece, or flat against a vertical face, fully visible",
            "print": "Print the marker PDF at 100% scale (no fit-to-page); verify the square is 100 mm.",
        },
        "tips": [
            "Camera at mid-height of the piece; avoid looking down",
            "Subject distance at least 2 m; 70–100 mm equivalent focal length",
            "Plain light background; even lighting; no heavy backlight",
            "Include a clear floor line under the piece",
            "Place ArUco marker (DICT_4X4_50 id 7, 100 mm) in frame for metric scale",
            "If keystone residual exceeds 3°, retake front-on",
        ],
        "reject_if": [
            "Extreme wide-angle distortion",
            "Subject clipped at the frame edge",
            "Busy / cluttered background that breaks the mask",
        ],
    }
