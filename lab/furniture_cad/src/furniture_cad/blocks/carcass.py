"""Simple open-front box carcass (two sides + shelves + optional back)."""

from __future__ import annotations

from typing import Any

from build123d import Box, Compound, Pos

from furniture_cad.blocks.panel import panel
from furniture_cad.blocks.shelf_board import shelf_board
from furniture_cad.derive import part


def carcass(
    *,
    W: float,
    D: float,
    H: float,
    t: float = 18.0,
    shelves: int = 4,
    back_t: float = 6.0,
    material: str = "oak",
) -> dict[str, Any]:
    """Tangent-rectilinear carcass; open front. Returns assembly + derived parts."""
    n = max(1, int(shelves))
    side = panel(width=D, height=H, thickness=t, name="side")
    # Reorient: panel is W=depth along X, t along Y, H along Z — rotate for left/right sides
    # For sides we want thickness along X: use Box directly for clarity
    side_solid = Box(t, D, H)
    board = shelf_board(length=W - 2 * t, depth=D - 12, thickness=t)
    boards = []
    zs = [t / 2.0 + i * ((H - t) / max(1, n - 1)) for i in range(n)] if n > 1 else [H / 2.0]
    for z in zs:
        boards.append(Pos(0, 0, z) * board)
    sides = [
        Pos(-W / 2.0 + t / 2.0, 0, H / 2.0) * side_solid,
        Pos(W / 2.0 - t / 2.0, 0, H / 2.0) * side_solid,
    ]
    back = Pos(0, -D / 2.0 + back_t / 2.0, H / 2.0) * Box(W - 2 * t, back_t, H - 2 * t)
    assembly = Compound(children=sides + boards + [back])
    parts = [
        part("side", side_solid, material=material, qty=2, name="Side"),
        part("board", board, material=material, qty=n, name="Shelf / board"),
        part("back", Box(W - 2 * t, back_t, H - 2 * t), material="ply", qty=1, make="sheet", name="Back"),
    ]
    return {"assembly": assembly, "parts": parts, "meta": {"helper": "carcass", "W": W, "D": D, "H": H}}
