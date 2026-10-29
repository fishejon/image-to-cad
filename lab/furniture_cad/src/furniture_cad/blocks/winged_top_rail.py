"""Bow-tie / winged top rail with optional plan curve."""

from __future__ import annotations

from build123d import (
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Plane,
    Polyline,
    Pos,
    Rectangle,
    ThreePointArc,
    extrude,
    make_face,
    sweep,
)

from furniture_cad.validate import assert_finite_number, check_solid, solid_ok


def winged_top_rail(
    *,
    width: float,
    end_height: float,
    mid_height: float,
    thickness: float,
    curve_sag: float = 0.0,
) -> object:
    """
    Winged profile (taller ends). If curve_sag > 0, center bows toward +Y.

    Flat: bow-tie in XZ extruded in Y.
    Curved: sweep full-height bar along arc, notch center top down to mid_height.
    """
    w = assert_finite_number("width", width, min_v=80.0, max_v=1200.0)
    eh = assert_finite_number("end_height", end_height, min_v=20.0, max_v=250.0)
    mh = assert_finite_number("mid_height", mid_height, min_v=10.0, max_v=250.0)
    t = assert_finite_number("thickness", thickness, min_v=4.0, max_v=80.0)
    sag = assert_finite_number("curve_sag", curve_sag, min_v=0.0, max_v=200.0)
    if mh > eh:
        raise ValueError("mid_height should be <= end_height for a winged rail")

    half = w / 2.0
    cut_depth = eh - mh

    if sag < 0.5:
        neck = w * 0.22
        z_mid_bot = max(2.0, eh - mh)
        z_mid_top = z_mid_bot + mh
        pts = [
            (-half, 0.0),
            (-half, eh),
            (-neck, z_mid_top),
            (neck, z_mid_top),
            (half, eh),
            (half, 0.0),
            (neck, z_mid_bot),
            (-neck, z_mid_bot),
        ]
        with BuildPart() as part:
            with BuildSketch(Plane.XZ):
                with BuildLine():
                    Polyline(*pts, close=True)
                make_face()
            extrude(amount=t)
        solid = Pos(0, -t / 2.0, 0) * part.part
        check_solid(solid, expect_size=(w, t, eh), tol=3.0, label="winged_top_rail")
        return solid

    with BuildPart() as part:
        with BuildLine():
            ThreePointArc((-half, 0, 0), (0, sag, 0), (half, 0, 0))
        with BuildSketch(Plane.YZ):
            Rectangle(t, eh)
        sweep()

    bar = Pos(0, 0, eh / 2.0) * part.part
    if cut_depth > 1.0:
        notch = Pos(0, sag, eh - cut_depth / 2.0) * Box(w * 0.55, t + 8, cut_depth + 1)
        bar = bar - notch

    if not solid_ok(bar):
        raise ValueError("winged_top_rail curved solid invalid")
    check_solid(bar, label="winged_top_rail")
    return bar
