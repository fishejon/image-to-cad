"""Flat rectangular seat / panel (Z-up, bottom face at z=0)."""

from __future__ import annotations

from build123d import Box, Pos

from furniture_cad.validate import assert_finite_number, check_solid


def seat_panel(
    *,
    width: float,
    depth: float,
    thickness: float,
) -> object:
    """
    Axis-aligned panel centered on XY origin, bottom at z=0, top at z=thickness.

    width → X, depth → Y, thickness → Z (mm).
    """
    w = assert_finite_number("width", width, min_v=10.0, max_v=3000.0)
    d = assert_finite_number("depth", depth, min_v=10.0, max_v=3000.0)
    t = assert_finite_number("thickness", thickness, min_v=1.0, max_v=200.0)

    solid = Pos(0, 0, t / 2.0) * Box(w, d, t)
    check_solid(solid, expect_size=(w, d, t), tol=1.5, label="seat_panel")
    return solid
