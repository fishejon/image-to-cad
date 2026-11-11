"""Two-profile flared leg (console L1)."""

from __future__ import annotations

from typing import Any

from build123d import Box, BuildPart, BuildSketch, Plane, Pos, Rectangle, loft

from furniture_cad.derive import part


def two_profile_flared_leg(
    *,
    height: float = 520.7,
    top: list[float] | None = None,
    foot: list[float] | None = None,
    flare_r: list[float] | None = None,
    material: str = "walnut",
) -> dict[str, Any]:
    """Tapered leg via loft between top and foot sections (two-profile approximation)."""
    top = top or [76.2, 50.8]
    foot = foot or [28.0, 25.4]
    flare_r = flare_r or [25.4, 50.8, 25.4]
    tx, ty = float(top[0]), float(top[1])
    fx, fy = float(foot[0]), float(foot[1])

    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            Rectangle(fx, fy)
        with BuildSketch(Plane.XY.offset(height * 0.35)):
            # Mid flare — larger section
            Rectangle(max(tx, fx) * 1.05, max(ty, fy) * 1.05)
        with BuildSketch(Plane.XY.offset(height)):
            Rectangle(tx, ty)
        loft()
    solid = bp.part
    rec = part(
        "L1",
        solid,
        material=material,
        qty=1,
        name="Leg",
        make="shaped",
        blank_pad_mm=max(8.0, float(flare_r[0]) * 0.2),
    )
    return {
        "solid": solid,
        "parts": [rec],
        "meta": {"block": "two_profile_flared", "height": height, "top": top, "foot": foot, "flare_r": flare_r},
    }


def leg_set_flared(
    *,
    count: int = 4,
    height: float = 520.7,
    top: list[float] | None = None,
    foot: list[float] | None = None,
    flare_r: list[float] | None = None,
    material: str = "walnut",
) -> dict[str, Any]:
    one = two_profile_flared_leg(height=height, top=top, foot=foot, flare_r=flare_r, material=material)
    one["parts"][0].qty = max(1, int(count))
    return one
