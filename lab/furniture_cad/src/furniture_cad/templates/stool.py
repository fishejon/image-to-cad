"""Three- or four-leg stool with flat seat."""

from __future__ import annotations

import math
from typing import Any

from build123d import Compound, Pos

from furniture_cad.blocks import rail, seat_panel, tapered_leg
from furniture_cad.validate import assert_finite_number, check_solid


def stool(params: dict[str, Any]) -> dict[str, Any]:
    """
    Expected params:
      legs (3|4, default 4), seat_w, seat_d, seat_t, seat_h,
      leg_top, leg_bot, leg_section, stretcher (bool)
    """
    n_legs = int(params.get("legs", 4))
    if n_legs not in (3, 4):
        raise ValueError("legs must be 3 or 4")

    seat_w = assert_finite_number("seat_w", params.get("seat_w", 350), min_v=200, max_v=600)
    seat_d = assert_finite_number("seat_d", params.get("seat_d", 350), min_v=200, max_v=600)
    seat_t = assert_finite_number("seat_t", params.get("seat_t", 30), min_v=5, max_v=80)
    seat_h = assert_finite_number("seat_h", params.get("seat_h", 650), min_v=300, max_v=900)
    leg_top = assert_finite_number("leg_top", params.get("leg_top", 32), min_v=10, max_v=80)
    leg_bot = assert_finite_number("leg_bot", params.get("leg_bot", 25), min_v=10, max_v=80)
    leg_section = str(params.get("leg_section", "round"))
    use_stretcher = bool(params.get("stretcher", True))
    st_w = assert_finite_number("stretcher_section_w", params.get("stretcher_section_w", 18), min_v=5, max_v=60)
    st_h = assert_finite_number("stretcher_section_h", params.get("stretcher_section_h", 25), min_v=5, max_v=80)
    st_z = assert_finite_number("stretcher_z", params.get("stretcher_z", 200), min_v=20, max_v=seat_h - 20)

    radius = min(seat_w, seat_d) / 2.0 - max(leg_top, leg_bot) / 2.0 - 8.0
    if radius < 20:
        raise ValueError("seat too small for legs")

    parts: dict[str, object] = {}
    seat = seat_panel(width=seat_w, depth=seat_d, thickness=seat_t)
    parts["seat"] = Pos(0, 0, seat_h) * seat

    positions: list[tuple[float, float]] = []
    if n_legs == 4:
        hx = seat_w / 2.0 - max(leg_top, leg_bot) / 2.0 - 5.0
        hy = seat_d / 2.0 - max(leg_top, leg_bot) / 2.0 - 5.0
        positions = [(-hx, -hy), (hx, -hy), (-hx, hy), (hx, hy)]
    else:
        for i in range(3):
            ang = -math.pi / 2 + i * (2 * math.pi / 3)
            positions.append((radius * math.cos(ang), radius * math.sin(ang)))

    for i, (x, y) in enumerate(positions):
        leg = tapered_leg(height=seat_h, top_size=leg_top, bot_size=leg_bot, section=leg_section)
        parts[f"leg_{i}"] = Pos(x, y, 0) * leg

    if use_stretcher and n_legs == 4:
        hx = positions[1][0]
        hy = abs(positions[0][1])
        r_f = rail(length=2.0 * hx, section_w=st_w, section_h=st_h)
        parts["stretcher_f"] = Pos(0, -hy, st_z) * r_f
        parts["stretcher_b"] = Pos(0, hy, st_z) * r_f

    compound = Compound(children=list(parts.values()))
    check_solid(compound, label="stool")
    return {
        "template": "stool",
        "parts": parts,
        "assembly": compound,
        "params": {
            "legs": n_legs,
            "seat_w": seat_w,
            "seat_d": seat_d,
            "seat_t": seat_t,
            "seat_h": seat_h,
            "leg_top": leg_top,
            "leg_bot": leg_bot,
            "leg_section": leg_section,
            "stretcher": use_stretcher,
            "stretcher_section_w": st_w,
            "stretcher_section_h": st_h,
            "stretcher_z": st_z,
        },
    }
