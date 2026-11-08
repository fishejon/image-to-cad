"""Flat rectangular panel (carcass side, door blank, divider)."""

from __future__ import annotations

from build123d import Box, Pos


def panel(*, width: float, height: float, thickness: float, name: str = "panel"):
    """Axis-aligned panel; thickness along Y (depth of board face in XY plan).

    Returns a solid centered on origin, bottom at z=0… wait — match seat_panel convention:
    box with size (width, thickness, height) centered? Prefer bottom-front convention:

    Solid: width along X, thickness along Y, height along Z; centered in X/Y, z from 0..height.
    """
    solid = Pos(0, 0, height / 2.0) * Box(width, thickness, height)
    solid.label = name  # type: ignore[attr-defined]
    return solid
