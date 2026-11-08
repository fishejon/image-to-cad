"""Open 4-post etagere / MCM bookshelf built from helpers (R3)."""

from __future__ import annotations

from typing import Any

from build123d import Box, Compound, Pos

from furniture_cad.blocks.shelf_board import shelf_board
from furniture_cad.derive import part


def open_etagere(
    *,
    W: float,
    D: float,
    H: float,
    shelves: int = 5,
    post_s: float = 32.0,
    shelf_t: float = 18.0,
    foot_h: float = 64.0,
    clearance: float = 48.0,
    overhang: float = 90.0,
    fin_w: float = 70.0,
    material: str = "walnut",
) -> dict[str, Any]:
    """Return {assembly, parts, meta} scaled to overall W×D×H (mm)."""
    n = max(1, int(shelves))
    run_t = post_s + 8.0
    post_h = H - foot_h
    bay = (post_h - clearance - n * shelf_t) / max(1, n - 1) if n > 1 else 0.0
    hx = W / 2.0 - overhang - post_s / 2.0
    hy = D / 2.0 - 18.0

    post_solid = Box(post_s, post_s, post_h)
    shelf_solid = shelf_board(length=W, depth=D, thickness=shelf_t)
    posts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            posts.append(Pos(sx * hx, sy * hy, foot_h + post_h / 2.0) * post_solid)

    shelves_s = []
    for i in range(n):
        z = foot_h + clearance + shelf_t / 2.0 + i * (shelf_t + bay)
        shelves_s.append(Pos(0, 0, z) * shelf_solid)

    runner = Box(run_t, D, foot_h)
    fin = Box(fin_w, D * 0.55, foot_h * 0.8)
    feet = [
        Pos(-hx, 0, foot_h / 2.0) * runner,
        Pos(hx, 0, foot_h / 2.0) * runner,
        Pos(-hx + run_t / 2.0 + fin_w / 2.0, 0, foot_h * 0.4) * fin,
        Pos(hx - run_t / 2.0 - fin_w / 2.0, 0, foot_h * 0.4) * fin,
    ]
    assembly = Compound(children=posts + shelves_s + feet)
    parts = [
        part("post", post_solid, material=material, qty=4, name="Vertical post"),
        part("shelf", shelf_solid, material=material, qty=n, name="Shelf board"),
        part("sled_foot", runner, material=material, qty=2, name="Sled foot", make="shaped"),
    ]
    return {
        "assembly": assembly,
        "parts": parts,
        "meta": {"W": W, "D": D, "H": H, "shelves": n, "helper": "open_etagere"},
    }
