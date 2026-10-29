"""Flat rectangular backrest panel (local: width→X, thickness→Y, height→Z; bottom at z=0)."""

from __future__ import annotations

from build123d import Box, Pos

from furniture_cad.validate import assert_finite_number, check_solid


def back_panel(
    *,
    width: float,
    height: float,
    thickness: float,
) -> object:
    """
    Flat backrest. Centered on XY origin in local space; bottom face at z=0.

    width → X, thickness → Y (fore-aft), height → Z.
    """
    w = assert_finite_number("width", width, min_v=50.0, max_v=1200.0)
    h = assert_finite_number("height", height, min_v=50.0, max_v=1200.0)
    t = assert_finite_number("thickness", thickness, min_v=2.0, max_v=80.0)

    solid = Pos(0, 0, h / 2.0) * Box(w, t, h)
    check_solid(solid, expect_size=(w, t, h), tol=1.5, label="back_panel")
    return solid
