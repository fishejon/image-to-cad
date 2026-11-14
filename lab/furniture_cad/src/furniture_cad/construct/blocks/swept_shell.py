"""Swept-shell carcass — leaning ends + open front (console form)."""

from __future__ import annotations

import math
from typing import Any

from build123d import Box, Compound, Pos

from furniture_cad.derive import part


def swept_shell(
    *,
    W: float,
    H: float,
    D: float,
    wall: float = 22.2,
    lean_deg: float = 6.0,
    sweep_r: float = 121.9,
    under_z: float = 495.3,
    back_t: float = 12.7,
    open_front: bool = True,
    front_setback: float | None = None,
    back_groove: float = 0.0,
    material: str = "walnut",
) -> dict[str, Any]:
    """Open-front casegood shell approximating the Fusion walnut console.

    Geometry is a practical build123d approximation of leaning ends + case mass.
    Part IDs match the hand cut list (T1/E1/B1/D1/BK1).

    Sizing rules (all driven by IR fields, no per-piece constants):
    * ``front_setback``: divider is set back from the front edge by this much
      (drawer fronts overlap it); depth = D - back_t - front_setback.
      ``None`` keeps the legacy 10 mm.
    * ``back_groove``: the floating back panel's tongues enter grooves in the top
      and bottom, so the back blank is taller than the void by 2 x groove depth.
    * Carved end envelope thickness = lean inset + sweep radius (the block the
      lean and the underside sweep are carved from).
    """
    case_h = max(40.0, H - under_z)
    inset = case_h * math.tan(math.radians(lean_deg))

    # Main case outer envelope
    outer = Pos(0, 0, under_z + case_h / 2) * Box(W, D, case_h)

    # Interior void — open to the front
    void_w = max(10.0, W - 2 * wall)
    void_d = max(10.0, D - back_t) if open_front else max(10.0, D - 2 * wall)
    void_h = max(10.0, case_h - 2 * wall)
    void = Pos(0, (D - void_d) / 2 - 0.5, under_z + case_h / 2) * Box(void_w, void_d + 2, void_h)
    shell = outer - void

    # End blanks for cut list (not placed outside the W envelope — avoid AABB blowout)
    end_w = wall + max(inset, 8.0)

    top = Pos(0, 0, H - wall / 2) * Box(W, D, wall)
    bottom = Pos(0, 0, under_z + wall / 2) * Box(max(10.0, W - 2 * wall), D, wall)
    back = Pos(0, -D / 2 + back_t / 2, under_z + case_h / 2) * Box(max(10.0, W - 2 * wall), back_t, max(10.0, case_h - 2 * wall))

    div_z = under_z + wall + (case_h - 2 * wall) * 0.52
    div_setback = 10.0 if front_setback is None else float(front_setback)
    div_d = max(10.0, D - back_t - div_setback)
    div = Pos(0, back_t * 0.25, div_z) * Box(max(10.0, W - 2 * wall), div_d, wall)
    end_env_t = inset + sweep_r
    back_h = max(10.0, case_h - 2 * wall + 2 * float(back_groove))

    # Sweep cue kept inside envelope
    sweep_box = Box(min(sweep_r * 0.25, 45), D * 0.85, min(sweep_r * 0.2, 35))
    sw_l = Pos(-W / 2 + wall + 25, 0, under_z + 12) * sweep_box
    sw_r = Pos(W / 2 - wall - 25, 0, under_z + 12) * sweep_box

    assembly = Compound(children=[shell, top, bottom, back, div, sw_l, sw_r])

    parts = [
        part("T1", Box(W, D, wall), material=material, qty=1, name="Top plank"),
        part(
            "E1",
            Box(end_env_t, D, case_h),
            material=material,
            qty=2,
            name="End block, carved",
            make="shaped",
            blank_pad_mm=12.0,
        ),
        part("B1", Box(max(10.0, W - 2 * wall), D, wall), material=material, qty=1, name="Bottom panel"),
        part(
            "D1",
            Box(max(10.0, W - 2 * wall), div_d, wall),
            material=material,
            qty=1,
            name="Divider shelf",
        ),
        part(
            "BK1",
            Box(max(10.0, W - 2 * wall), back_t, back_h),
            material=material,
            qty=1,
            make="sheet",
            name="Back panel",
        ),
    ]
    return {
        "assembly": assembly,
        "parts": parts,
        "features": {"end_block": 2, "open_cubby": 1, "shelf": 1},
        "meta": {
            "block": "swept_shell",
            "W": W,
            "H": H,
            "D": D,
            "under_z": under_z,
            "case_h": case_h,
            "wall": wall,
            "lean_deg": lean_deg,
            "sweep_r": sweep_r,
            "div_z": div_z,
            "void_h": void_h,
        },
    }
