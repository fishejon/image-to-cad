"""Horizontal mid backrest slat — optional plan curve (cups the sitter)."""

from __future__ import annotations

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Plane,
    Polyline,
    Pos,
    Rectangle,
    ThreePointArc,
    sweep,
)

from furniture_cad.validate import assert_finite_number, check_solid, solid_ok


def back_mid_slat(
    *,
    width: float,
    height: float,
    thickness: float,
    curve_sag: float = 0.0,
) -> object:
    """
    Mid rail spanning width in X. If curve_sag > 0, center bows toward +Y (backward).

    Local: bottom of section near z=0; centered on X.
    """
    w = assert_finite_number("width", width, min_v=50.0, max_v=1200.0)
    h = assert_finite_number("height", height, min_v=8.0, max_v=200.0)
    t = assert_finite_number("thickness", thickness, min_v=4.0, max_v=80.0)
    sag = assert_finite_number("curve_sag", curve_sag, min_v=0.0, max_v=200.0)

    half = w / 2.0
    if sag < 0.5:
        from build123d import Box

        solid = Pos(0, 0, h / 2.0) * Box(w, t, h)
        check_solid(solid, expect_size=(w, t, h), tol=1.5, label="back_mid_slat")
        return solid

    # Arc chord on X, sag in +Y; section in plane at left end
    with BuildPart() as part:
        with BuildLine() as path:
            ThreePointArc((-half, 0, 0), (0, sag, 0), (half, 0, 0))
        # Section: thickness along path normal≈Y at start, height along Z
        with BuildSketch(Plane.YZ):
            Rectangle(t, h)
        sweep()

    solid = part.part
    # Shift so bottom sits near z=0 (section was centered on path)
    solid = Pos(0, 0, h / 2.0) * solid
    if not solid_ok(solid):
        raise ValueError("back_mid_slat curved solid invalid")
    check_solid(solid, label="back_mid_slat")
    return solid
