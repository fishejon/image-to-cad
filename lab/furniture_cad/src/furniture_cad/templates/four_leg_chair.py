"""Four-legged chair: seat + legs + flush side rails, optional MCM curved back."""

from __future__ import annotations

import math
from typing import Any

from build123d import Compound, Pos

from furniture_cad.blocks import (
    back_mid_slat,
    back_panel,
    curved_stile,
    rail,
    rounded_cushion,
    seat_panel,
    tapered_leg,
    winged_top_rail,
)
from furniture_cad.geom_util import span_rail
from furniture_cad.validate import assert_finite_number, check_solid


def four_leg_chair(params: dict[str, Any]) -> dict[str, Any]:
    """
    seat_h = top of sitting surface (one-piece seat unless cushion=True).
    Side stretchers: inside face of front legs → outside face of rear legs (flush).
    Rear stiles: optional rake_y + curve_y. Back rails: optional curve_sag.
    """
    seat_w = assert_finite_number("seat_w", params.get("seat_w", 450), min_v=200, max_v=900)
    seat_d = assert_finite_number("seat_d", params.get("seat_d", 420), min_v=200, max_v=900)
    seat_t = assert_finite_number("seat_t", params.get("seat_t", 25), min_v=5, max_v=80)
    seat_h = assert_finite_number("seat_h", params.get("seat_h", 450), min_v=200, max_v=600)
    leg_top = assert_finite_number("leg_top", params.get("leg_top", 35), min_v=10, max_v=80)
    leg_bot = assert_finite_number("leg_bot", params.get("leg_bot", 28), min_v=10, max_v=80)
    leg_section = str(params.get("leg_section", "square"))
    # No visual taper unless sizes differ
    use_stretcher = bool(params.get("stretcher", True))
    stretcher_front = bool(params.get("stretcher_front", True))
    st_w = assert_finite_number("stretcher_section_w", params.get("stretcher_section_w", 20), min_v=5, max_v=60)
    st_h = assert_finite_number("stretcher_section_h", params.get("stretcher_section_h", 30), min_v=5, max_v=80)
    st_z_side = assert_finite_number(
        "stretcher_z_side",
        params.get("stretcher_z_side", params.get("stretcher_z", 150)),
        min_v=20,
        max_v=seat_h - 20,
    )
    st_z_rear = assert_finite_number(
        "stretcher_z_rear",
        params.get("stretcher_z_rear", params.get("stretcher_z", st_z_side)),
        min_v=20,
        max_v=seat_h - 20,
    )

    use_back = bool(params.get("back", False))
    back_style = str(params.get("back_style", "panel")).lower().strip()
    if back_style not in ("panel", "mcm_rails"):
        raise ValueError("back_style must be 'panel' or 'mcm_rails'")
    back_w = assert_finite_number("back_w", params.get("back_w", seat_w - 20), min_v=50, max_v=1200)
    back_h = assert_finite_number("back_h", params.get("back_h", 350), min_v=50, max_v=1200)
    back_t = assert_finite_number("back_t", params.get("back_t", 12), min_v=2, max_v=80)
    winged_width = assert_finite_number(
        "winged_width", params.get("winged_width", back_w + 20), min_v=80, max_v=1200
    )
    winged_end_h = assert_finite_number("winged_end_h", params.get("winged_end_h", 90), min_v=20, max_v=250)
    winged_mid_h = assert_finite_number("winged_mid_h", params.get("winged_mid_h", 55), min_v=10, max_v=250)
    winged_thickness = assert_finite_number(
        "winged_thickness", params.get("winged_thickness", back_t + 2), min_v=4, max_v=80
    )
    mid_slat_h = assert_finite_number("mid_slat_h", params.get("mid_slat_h", 45), min_v=8, max_v=200)
    curve_sag = assert_finite_number("curve_sag", params.get("curve_sag", 0), min_v=0, max_v=200)
    rake_y = assert_finite_number("rake_y", params.get("rake_y", 0), min_v=-50, max_v=250)
    stile_curve_y = assert_finite_number("stile_curve_y", params.get("stile_curve_y", 0), min_v=-50, max_v=150)

    use_cushion = bool(params.get("cushion", False))
    cushion_h = assert_finite_number("cushion_h", params.get("cushion_h", 40), min_v=5, max_v=120)
    cushion_r = assert_finite_number("cushion_corner_r", params.get("cushion_corner_r", 28), min_v=0, max_v=120)

    if "mid_slat_z_from_seat" in params:
        mid_from_seat = assert_finite_number(
            "mid_slat_z_from_seat", params["mid_slat_z_from_seat"], min_v=0, max_v=back_h
        )
        mid_slat_z_frac = (mid_from_seat + mid_slat_h / 2.0) / back_h if back_h else 0.42
    else:
        mid_slat_z_frac = assert_finite_number(
            "mid_slat_z_frac", params.get("mid_slat_z_frac", 0.42), min_v=0.15, max_v=0.85
        )
        mid_from_seat = back_h * mid_slat_z_frac - mid_slat_h / 2.0

    # One-piece seat: sitting surface at seat_h; no floating cushion / apron
    frame_top = seat_h - cushion_h if use_cushion else seat_h - seat_t
    if use_cushion:
        sit_top = seat_h
    else:
        sit_top = seat_h
        frame_top = seat_h - seat_t

    s_leg = max(leg_top, leg_bot)
    inset_f = s_leg / 2.0
    hx_front = seat_w / 2.0 - inset_f
    hy = seat_d / 2.0 - inset_f

    if "rear_outer_w" in params:
        rear_outer = assert_finite_number("rear_outer_w", params["rear_outer_w"], min_v=100, max_v=1200)
        hx_rear = rear_outer / 2.0 - s_leg / 2.0
    else:
        rear_outer = None
        hx_rear = hx_front

    parts: dict[str, object] = {}

    # Seat as a single slab to sit_top (rounded corners lightly via cushion block only if asked)
    if use_cushion:
        seat = seat_panel(width=seat_w, depth=seat_d, thickness=seat_t)
        parts["seat"] = Pos(0, 0, frame_top) * seat
        pad = rounded_cushion(
            width=seat_w - 8,
            depth=seat_d - 8,
            height=cushion_h,
            corner_radius=cushion_r,
        )
        parts["cushion"] = Pos(0, 0, frame_top + seat_t) * pad
    else:
        # One piece: rounded slab, top at seat_h — no separate pad, no apron ring
        seat = rounded_cushion(
            width=seat_w,
            depth=seat_d,
            height=seat_t,
            corner_radius=min(28.0, seat_w / 10, seat_d / 10),
        )
        parts["seat"] = Pos(0, 0, seat_h - seat_t) * seat

    front_h = seat_h - seat_t  # front legs meet underside of seat slab
    if use_cushion:
        front_h = frame_top
    rear_h = sit_top + back_h if use_back else front_h

    # Front legs — straight prism (equal top/bot ⇒ no taper)
    for name, (x, y) in {
        "leg_fl": (-hx_front, -hy),
        "leg_fr": (hx_front, -hy),
    }.items():
        leg = tapered_leg(height=front_h, top_size=leg_top, bot_size=leg_bot, section=leg_section)
        parts[name] = Pos(x, y, 0) * leg

    # Rear stiles — raked + curved when requested
    use_curved_rear = use_back and (abs(rake_y) > 0.5 or abs(stile_curve_y) > 0.5)
    for name, x in (("leg_bl", -hx_rear), ("leg_br", hx_rear)):
        if use_curved_rear:
            stile = curved_stile(
                height=rear_h,
                section=s_leg,
                rake_y=rake_y,
                curve_y=stile_curve_y,
            )
            parts[name] = Pos(x, hy, 0) * stile
        else:
            leg = tapered_leg(height=rear_h, top_size=leg_top, bot_size=leg_bot, section=leg_section)
            parts[name] = Pos(x, hy, 0) * leg

    if use_stretcher:
        # Flush joinery: inside of front legs, outside of rear legs
        # Left rail: front attach on +X side of left-front inner face; rear on -X side of left-rear outer face
        z_side = st_z_side + st_h / 2.0
        # Inner face of front-left leg at x = -hx_front + s_leg/2; rail center just inboard
        x_fl_in = -hx_front + s_leg / 2.0 + st_w / 2.0
        x_fr_in = hx_front - s_leg / 2.0 - st_w / 2.0
        # Outer face of rear-left at x = -hx_rear - s_leg/2; rail center just outboard
        x_bl_out = -hx_rear - s_leg / 2.0 - st_w / 2.0
        x_br_out = hx_rear + s_leg / 2.0 + st_w / 2.0
        y_f = -hy
        y_b = hy + (rake_y * (st_z_side / rear_h) if use_curved_rear and rear_h > 0 else 0.0)

        parts["stretcher_l"] = span_rail(
            (x_fl_in, y_f, z_side),
            (x_bl_out, y_b, z_side),
            section_w=st_w,
            section_h=st_h,
        )
        parts["stretcher_r"] = span_rail(
            (x_fr_in, y_f, z_side),
            (x_br_out, y_b, z_side),
            section_w=st_w,
            section_h=st_h,
        )

        if stretcher_front:
            z_f = st_z_side + st_h / 2.0
            parts["stretcher_f"] = span_rail(
                (-hx_front, -hy, z_f),
                (hx_front, -hy, z_f),
                section_w=st_w,
                section_h=st_h,
            )
        else:
            z_r = st_z_rear + st_h / 2.0
            # Rear stretcher between outer/inner — keep between rear leg centers, flush-ish
            y_rear = hy + (rake_y * (st_z_rear / rear_h) if use_curved_rear and rear_h > 0 else 0.0)
            parts["stretcher_b"] = span_rail(
                (-hx_rear + s_leg / 2.0, y_rear, z_r),
                (hx_rear - s_leg / 2.0, y_rear, z_r),
                section_w=st_w,
                section_h=st_h,
            )

    if use_back:
        def y_at(z: float) -> float:
            if use_curved_rear and rear_h > 0:
                t = max(0.0, min(1.0, z / rear_h))
                return hy + rake_y * t + stile_curve_y * math.sin(t * math.pi)
            return hy

        if back_style == "panel":
            y_back = y_at(sit_top + back_h / 2) - back_t / 2.0
            panel = back_panel(width=back_w, height=back_h, thickness=back_t)
            parts["back"] = Pos(0, y_back, sit_top) * panel
        else:
            z_slat = sit_top + mid_from_seat
            y_slat = y_at(z_slat) - back_t / 2.0
            slat = back_mid_slat(
                width=back_w, height=mid_slat_h, thickness=back_t, curve_sag=curve_sag * 0.85
            )
            parts["back_mid_slat"] = Pos(0, y_slat, z_slat) * slat

            z_top = sit_top + back_h - winged_end_h
            y_top = y_at(z_top + winged_end_h / 2) - winged_thickness / 2.0
            top = winged_top_rail(
                width=winged_width,
                end_height=winged_end_h,
                mid_height=winged_mid_h,
                thickness=winged_thickness,
                curve_sag=curve_sag,
            )
            parts["winged_top_rail"] = Pos(0, y_top, z_top) * top

    compound = Compound(children=list(parts.values()))
    check_solid(compound, label="four_leg_chair")
    return {
        "template": "four_leg_chair",
        "parts": parts,
        "assembly": compound,
        "params": {
            "seat_w": seat_w,
            "seat_d": seat_d,
            "seat_t": seat_t,
            "seat_h": seat_h,
            "leg_top": leg_top,
            "leg_bot": leg_bot,
            "leg_section": leg_section,
            "rear_outer_w": rear_outer,
            "stretcher": use_stretcher,
            "stretcher_front": stretcher_front,
            "stretcher_section_w": st_w,
            "stretcher_section_h": st_h,
            "stretcher_z_side": st_z_side,
            "stretcher_z_rear": st_z_rear,
            "back": use_back,
            "back_style": back_style,
            "back_w": back_w,
            "back_h": back_h,
            "back_t": back_t,
            "winged_width": winged_width,
            "winged_end_h": winged_end_h,
            "winged_mid_h": winged_mid_h,
            "winged_thickness": winged_thickness,
            "mid_slat_h": mid_slat_h,
            "mid_slat_z_from_seat": mid_from_seat,
            "mid_slat_z_frac": mid_slat_z_frac,
            "curve_sag": curve_sag,
            "rake_y": rake_y,
            "stile_curve_y": stile_curve_y,
            "cushion": use_cushion,
            "cushion_h": cushion_h,
            "cushion_corner_r": cushion_r,
        },
    }
