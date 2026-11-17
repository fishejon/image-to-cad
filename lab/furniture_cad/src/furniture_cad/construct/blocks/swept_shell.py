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
    bank_open_h: float | None = None,
    material: str = "walnut",
    top_t: float | None = None,
    include_horizontal_divider: bool = True,
    end_bottom_r: float = 0.0,
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
    * ``bank_open_h``: drawer opening height (measured); the divider sits on top of it.
      ``None`` keeps the legacy fixed fraction of the void.
    * ``include_horizontal_divider``: when False (multi-bay layouts), omit D1 —
      vertical dividers / shelves come from the layout compiler instead.
    * Carved end envelope thickness = lean inset + sweep radius (the block the
      lean and the underside sweep are carved from).
    """
    case_h = max(40.0, H - under_z)
    top_t = float(wall if top_t is None else top_t)
    inset = case_h * math.tan(math.radians(lean_deg))

    # Main case outer envelope
    outer = Pos(0, 0, under_z + case_h / 2) * Box(W, D, case_h)

    # Interior void — open to the front
    void_w = max(10.0, W - 2 * wall)
    void_d = max(10.0, D - back_t) if open_front else max(10.0, D - 2 * wall)
    void_h = max(10.0, case_h - 2 * wall)
    void = Pos(0, (D - void_d) / 2 - 0.5, under_z + case_h / 2) * Box(void_w, void_d + 2, void_h)
    shell = outer - void

    top = Pos(0, 0, H - top_t / 2) * Box(W, D, top_t)
    bottom = Pos(0, 0, under_z + wall / 2) * Box(max(10.0, W - 2 * wall), D, wall)
    back = Pos(0, -D / 2 + back_t / 2, under_z + case_h / 2) * Box(
        max(10.0, W - 2 * wall), back_t, max(10.0, case_h - 2 * wall)
    )

    if bank_open_h is not None:
        # divider underside = top of the opening; keep it inside the void
        open_h = max(20.0, min(float(bank_open_h), case_h - 3 * wall))
        div_z = under_z + wall + open_h + wall / 2
    else:
        div_z = under_z + wall + (case_h - 2 * wall) * 0.52
    div_setback = 10.0 if front_setback is None else float(front_setback)
    div_d = max(10.0, D - back_t - div_setback)
    # Straight ends (no lean, no sweep) are plain panels, not carved end blocks.
    straight = lean_deg == 0 and sweep_r <= 2.0
    end_env_t = wall if straight else inset + sweep_r
    back_h = max(10.0, case_h - 2 * wall + 2 * float(back_groove))
    # Sweep radius clamps to 1 mm so square corners stay numerically stable.
    r_eff = 1.0 if straight else max(1.0, float(sweep_r))
    bottom_len = max(10.0, W - 2 * wall)
    # Ends sit under the top plank on straight carcasses.
    end_h = max(10.0, case_h - top_t) if straight else case_h

    children: list[Any] = [shell, top, bottom, back]
    if include_horizontal_divider:
        div = Pos(0, back_t * 0.25, div_z) * Box(max(10.0, W - 2 * wall), div_d, wall)
        children.append(div)
    if not straight:
        # Sweep / wishbone cue at the case-to-leg transition (front view massing).
        sweep_box = Box(min(sweep_r * 0.25, 45), D * 0.85, min(sweep_r * 0.2, 35))
        children.append(Pos(-W / 2 + wall + 25, 0, under_z + 12) * sweep_box)
        children.append(Pos(W / 2 - wall - 25, 0, under_z + 12) * sweep_box)
        # Pill cue: thickened lower end mass inside the envelope (wishbone/pill massing)
        pill_h = min(case_h * 0.35, 120)
        pill = Box(min(end_env_t * 0.55, 60), D * 0.7, pill_h)
        children.append(Pos(-W / 2 + end_env_t * 0.45, 0, under_z + pill_h / 2 + 8) * pill)
        children.append(Pos(W / 2 - end_env_t * 0.45, 0, under_z + pill_h / 2 + 8) * pill)

    assembly = Compound(children=children)

    if straight:
        e1 = part("E1", Box(end_env_t, D, end_h), material=material, qty=2, name="End panel")
    else:
        e1 = part(
            "E1",
            Box(end_env_t, D, end_h),
            material=material,
            qty=2,
            name="End block, carved",
            make="shaped",
            blank_pad_mm=12.0,
        )
    parts = [
        part("T1", Box(W, D, top_t), material=material, qty=1, name="Top plank"),
        e1,
        part("B1", Box(max(10.0, W - 2 * wall), D, wall), material=material, qty=1, name="Bottom panel"),
    ]
    features: dict[str, int] = {"end_block": 0 if straight else 2, "open_cubby": 0, "shelf": 0}
    if include_horizontal_divider:
        parts.append(
            part(
                "D1",
                Box(max(10.0, W - 2 * wall), div_d, wall),
                material=material,
                qty=1,
                name="Divider shelf",
            )
        )
        features["shelf"] = 1
        features["open_cubby"] = 1
    parts.append(
        part(
            "BK1",
            Box(max(10.0, W - 2 * wall), back_t, back_h),
            material=material,
            qty=1,
            make="sheet",
            name="Back panel",
        )
    )
    return {
        "assembly": assembly,
        "parts": parts,
        "features": features,
        "meta": {
            "block": "swept_shell",
            "W": W,
            "H": H,
            "D": D,
            "under_z": under_z,
            "case_h": case_h,
            "wall": wall,
            "top_t": top_t,
            "lean_deg": lean_deg,
            "sweep_r": sweep_r,
            "div_z": div_z,
            "void_h": void_h,
            "x_tangent": -W / 2 + r_eff,
            "bottom_len": bottom_len,
            "straight": straight,
            "include_horizontal_divider": include_horizontal_divider,
        },
    }
