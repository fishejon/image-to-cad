"""Rear stile / back leg: square section swept along a raked, curved path (Z-up)."""

from __future__ import annotations

from build123d import BuildLine, BuildPart, BuildSketch, Plane, Rectangle, Spline, sweep

from furniture_cad.validate import assert_finite_number, check_solid, solid_ok


def curved_stile(
    *,
    height: float,
    section: float,
    rake_y: float,
    curve_y: float = 0.0,
) -> object:
    """
    Foot at origin; top at (0, rake_y, height). curve_y adds mid-path bulge in +Y
    so the stile bows as it rises into the backrest.
    """
    h = assert_finite_number("height", height, min_v=50.0, max_v=2000.0)
    s = assert_finite_number("section", section, min_v=8.0, max_v=80.0)
    rake = assert_finite_number("rake_y", rake_y, min_v=-200.0, max_v=400.0)
    bulge = assert_finite_number("curve_y", curve_y, min_v=-100.0, max_v=200.0)

    mid_y = rake * 0.5 + bulge
    with BuildPart() as part:
        with BuildLine():
            Spline((0.0, 0.0, 0.0), (0.0, mid_y, h * 0.55), (0.0, rake, h))
        with BuildSketch(Plane.XY):
            Rectangle(s, s)
        sweep()

    solid = part.part
    if not solid_ok(solid):
        raise ValueError("curved_stile produced invalid solid")
    check_solid(solid, label="curved_stile")
    return solid
