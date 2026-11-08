"""Horizontal shelf board with optional knife-edge end steps (AABB approximation)."""

from __future__ import annotations

from build123d import Box, Pos


def shelf_board(
    *,
    length: float,
    depth: float,
    thickness: float,
    knife_overhang: float = 0.0,
) -> object:
    """Shelf: length X, depth Y, thickness Z; centered on XY, bottom at z=0."""
    solid = Pos(0, 0, thickness / 2.0) * Box(length, depth, thickness)
    # Knife edge as thinner tip boxes is left to mesh/viewer; solid stays full for lists.
    _ = knife_overhang
    return solid
