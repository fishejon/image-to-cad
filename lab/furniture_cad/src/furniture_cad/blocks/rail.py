"""Rectilinear rail / stretcher along +X (Z-up)."""

from __future__ import annotations

from build123d import Box, Pos

from furniture_cad.validate import assert_finite_number, check_solid


def rail(
    *,
    length: float,
    section_w: float,
    section_h: float,
) -> object:
    """
    Rail centered on origin, length along X, section_w along Y, section_h along Z.
    Bottom of the rail sits at z=0.
    """
    length_v = assert_finite_number("length", length, min_v=1.0, max_v=5000.0)
    sw = assert_finite_number("section_w", section_w, min_v=1.0, max_v=200.0)
    sh = assert_finite_number("section_h", section_h, min_v=1.0, max_v=200.0)

    solid = Pos(0, 0, sh / 2.0) * Box(length_v, sw, sh)
    check_solid(solid, expect_size=(length_v, sw, sh), tol=1.5, label="rail")
    return solid
