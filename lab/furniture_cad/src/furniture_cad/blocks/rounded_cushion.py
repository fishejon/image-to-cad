"""Upholstered seat pad with rounded plan corners (Z-up, bottom at z=0)."""

from __future__ import annotations

from build123d import Axis, Box, BuildPart, Pos, fillet

from furniture_cad.validate import assert_finite_number, check_solid


def rounded_cushion(
    *,
    width: float,
    depth: float,
    height: float,
    corner_radius: float = 25.0,
) -> object:
    """
    Soft rectangular cushion centered on XY, bottom at z=0, top at z=height.

    Vertical edges are filleted by corner_radius (clamped to fit).
    """
    w = assert_finite_number("width", width, min_v=50.0, max_v=1200.0)
    d = assert_finite_number("depth", depth, min_v=50.0, max_v=1200.0)
    h = assert_finite_number("height", height, min_v=5.0, max_v=200.0)
    r = assert_finite_number("corner_radius", corner_radius, min_v=0.0, max_v=200.0)
    r = min(r, w / 2.0 - 0.5, d / 2.0 - 0.5)

    with BuildPart() as part:
        Box(w, d, h)
        if r > 0.5:
            fillet(part.edges().filter_by(Axis.Z), r)

    solid = Pos(0, 0, h / 2.0) * part.part
    check_solid(solid, expect_size=(w, d, h), tol=2.0, label="rounded_cushion")
    return solid
