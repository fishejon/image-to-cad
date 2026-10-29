"""Small geometry helpers for assemblies."""

from __future__ import annotations

import math

from build123d import Box, Pos, Rot


def span_rail(
    p0: tuple[float, float, float],
    p1: tuple[float, float, float],
    *,
    section_w: float,
    section_h: float,
) -> object:
    """
    Axis-aligned box from p0→p1 in plan (constant z = average), rotated about Z to span.

    p0/p1 are rail-axis endpoints at the vertical center of the rail.
    section_w is horizontal thickness perpendicular to the span; section_h is vertical.
    """
    x0, y0, z0 = p0
    x1, y1, z1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length < 1.0:
        raise ValueError("span_rail endpoints too close")
    z = 0.5 * (z0 + z1)
    yaw = math.degrees(math.atan2(dy, dx))
    # Box along +X, bottom at -section_h/2 locally then lift so center at z
    rail = Box(length, section_w, section_h)
    mid = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, z)
    return Pos(*mid) * Rot(0, 0, yaw) * rail
