#!/usr/bin/env python3
"""
Bespoke MCM dining chair (chair_02) — designer/CAD-engineer model.

Implements evals/photos/chairs/chair_02.brief.md + reference photo.
Units mm. +Z up, +Y toward back of chair, +X right.

Back-post side elevation (do not reverse):
  foot AFT of seat → rises FORWARD to seat → rakes AFT above seat.
Posts stop ~3/4 up the top-rail height. Apron recessed under cushion overhang.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from build123d import (  # noqa: E402
    Axis,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Compound,
    Curve,
    Plane,
    Pos,
    Rectangle,
    Rot,
    Spline,
    ThreePointArc,
    export_step,
    export_stl,
    extrude,
    fillet,
    loft,
    sweep,
)

OUT = ROOT / "out" / "chair_02_bespoke"

# --- tape / design constants ------------------------------------------------
SEAT_H = 445.0
SEAT_T = 19.0
SEAT_FRONT_W = 445.0
SEAT_D = 420.0

APRON_INSET = 18.0
FRONT_INSET = 28.0  # cushion overhang past front apron/legs
APRON_H = 38.0
APRON_T = 22.0

LEG = 25.0
LEG_TAPER = 0.88

STRETCHER_H = 28.0
STRETCHER_T = 18.0
STRETCHER_Z = 229.0  # underside ≈ 9"
REAR_STRETCHER_Z = 317.0  # underside ≈ 12.5" so center nearer 13"

STILE_OUTER = 368.0
BACK_ABOVE_SEAT = 356.0
MID_FROM_SEAT = 102.0
MID_H = 44.0
TOP_RAIL_W = 533.0
TOP_RAIL_H = 140.0
TOP_RAIL_T = 16.0
POST_INTO_RAIL = TOP_RAIL_H * 0.75
POST_TOP_Z = SEAT_H + BACK_ABOVE_SEAT - TOP_RAIL_H + POST_INTO_RAIL

CURVE_SAG = 48.0
FOOT_AFT = 52.0
RISE_FORWARD = 58.0  # foot → seat: move forward (−Y)
RAKE_AFT = 72.0  # seat → post top: move aft (+Y)

Y_SEAT_REAR = SEAT_D / 2.0
Y_FOOT = Y_SEAT_REAR + FOOT_AFT
Y_AT_SEAT = Y_FOOT - RISE_FORWARD
Y_POST_TOP = Y_AT_SEAT + RAKE_AFT


def span_box(p0, p1, *, section_w: float, section_h: float):
    x0, y0, z0 = p0
    x1, y1, z1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length < 1:
        raise ValueError("span too short")
    yaw = math.degrees(math.atan2(dy, dx))
    z = 0.5 * (z0 + z1)
    mid = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, z)
    return Pos(*mid) * Rot(0, 0, yaw) * Box(length, section_w, section_h)


def seat_cushion():
    with BuildPart() as part:
        with BuildSketch(Plane.XY.offset(SEAT_H - SEAT_T)):
            Rectangle(SEAT_FRONT_W, SEAT_D)
        extrude(amount=SEAT_T)
        try:
            fillet(part.edges().filter_by(Axis.Z), 32)
        except Exception:
            pass
    return part.part


def front_leg(x: float, y: float, height: float):
    bot = LEG * LEG_TAPER
    with BuildPart() as part:
        with BuildSketch(Plane.XY):
            Rectangle(bot, bot)
        with BuildSketch(Plane.XY.offset(height)):
            Rectangle(LEG, LEG)
        loft()
    return Pos(x, y, 0) * part.part


def back_post(x: float):
    """
    Path in LOCAL coords starting at (0,0,0)=foot, then Pos to world (x, Y_FOOT, 0).
    Local +Y is world +Y. Forward toward seat = decreasing world Y = negative local Δy.
    """
    # Local path: foot origin; seat is −RISE_FORWARD in Y; top is −RISE_FORWARD+RAKE_AFT
    y_seat_l = -RISE_FORWARD
    y_top_l = -RISE_FORWARD + RAKE_AFT
    z_seat = SEAT_H
    z_top = POST_TOP_Z

    with BuildPart() as part:
        with BuildLine() as bl:
            Spline(
                (0, 0, 0),
                (0, y_seat_l * 0.45, z_seat * 0.45),
                (0, y_seat_l, z_seat),
                (0, y_seat_l + RAKE_AFT * 0.35, z_seat + (z_top - z_seat) * 0.45),
                (0, y_top_l, z_top),
            )
        path = bl.line
        # Section at path start, normal to path tangent
        n = path % 0
        with BuildSketch(Plane(origin=path @ 0, z_dir=n)):
            Rectangle(LEG, LEG * 0.92)
        sweep()

    return Pos(x, Y_FOOT, 0) * part.part


def post_y_at_z(z: float) -> float:
    """Approximate world Y of post centerline at height z (piecewise)."""
    if z <= 0:
        return Y_FOOT
    if z >= POST_TOP_Z:
        return Y_POST_TOP
    if z <= SEAT_H:
        t = z / SEAT_H
        return Y_FOOT + (Y_AT_SEAT - Y_FOOT) * t
    t = (z - SEAT_H) / (POST_TOP_Z - SEAT_H)
    return Y_AT_SEAT + (Y_POST_TOP - Y_AT_SEAT) * t


def apron_parts(hx_front: float, hy_front: float):
    z = SEAT_H - SEAT_T - APRON_H / 2.0
    ax = SEAT_FRONT_W / 2.0 - APRON_INSET - APRON_T / 2.0
    x_post = STILE_OUTER / 2.0 - LEG / 2.0
    y_back = post_y_at_z(SEAT_H - SEAT_T - APRON_H / 2.0)
    # Side aprons into front leg inner / back post (overlap leg volume)
    left = span_box(
        (-hx_front + LEG / 2.0, -hy_front, z),
        (-x_post, y_back, z),
        section_w=APRON_T,
        section_h=APRON_H,
    )
    right = span_box(
        (hx_front - LEG / 2.0, -hy_front, z),
        (x_post, y_back, z),
        section_w=APRON_T,
        section_h=APRON_H,
    )
    front = span_box(
        (-hx_front + LEG / 2.0, -hy_front, z),
        (hx_front - LEG / 2.0, -hy_front, z),
        section_w=APRON_T,
        section_h=APRON_H,
    )
    return left, right, front


def side_stretcher(sign: float, hx_front: float, hy_front: float):
    z = STRETCHER_Z + STRETCHER_H / 2.0
    y_b = post_y_at_z(z)
    x_post = sign * (STILE_OUTER / 2.0 - LEG / 2.0)
    # Tenon into front leg centerline; penetrate ~10mm past front face of leg
    x_f = sign * hx_front
    y_f = -hy_front + LEG / 2.0 - 10.0
    return span_box((x_f, y_f, z), (x_post, y_b, z), section_w=STRETCHER_T, section_h=STRETCHER_H)


def rear_stretcher():
    z = REAR_STRETCHER_Z + STRETCHER_H / 2.0
    y = post_y_at_z(z)
    x = STILE_OUTER / 2.0 - LEG / 2.0
    # Extend into posts
    return span_box((-x, y, z), (x, y, z), section_w=STRETCHER_T, section_h=STRETCHER_H)


def curved_rail(*, width: float, height: float, thickness: float, z_bottom: float, sag: float, y_center: float):
    """Plan-curved rail; path local, then placed in world."""
    half = width / 2.0
    with BuildPart() as part:
        with BuildLine() as bl:
            ThreePointArc((-half, 0, 0), (0, sag, 0), (half, 0, 0))
        path = bl.line
        with BuildSketch(Plane(origin=path @ 0, z_dir=path % 0)):
            Rectangle(thickness, height)
        sweep()
    # Path mid at (0,sag,0); shift so geometric center near y_center and z mid
    return Pos(0, y_center - sag / 2.0, z_bottom + height / 2.0) * part.part


def crescent_top_rail(y_posts: float):
    """Soft pill (stadium) section swept on plan arc; on forward face of posts."""
    from build123d import SlotOverall

    half = TOP_RAIL_W / 2.0
    h = TOP_RAIL_H
    t = TOP_RAIL_T
    z_c = SEAT_H + BACK_ABOVE_SEAT - h / 2.0
    with BuildPart() as part:
        with BuildLine() as bl:
            ThreePointArc((-half, 0, 0), (0, CURVE_SAG, 0), (half, 0, 0))
        path = bl.line
        with BuildSketch(Plane(origin=path @ 0, z_dir=path % 0)):
            # Stadium in section plane: length along "height" of rail face, width = thickness
            SlotOverall(h, t)
        sweep()
    return Pos(0, y_posts - t / 2.0 - 1.0 - CURVE_SAG / 2.0, z_c) * part.part


def build():
    hy_front = SEAT_D / 2.0 - FRONT_INSET - LEG / 2.0
    hx_front = SEAT_FRONT_W / 2.0 - APRON_INSET - LEG / 2.0
    x_post = STILE_OUTER / 2.0 - LEG / 2.0

    parts: dict[str, object] = {}
    parts["seat"] = seat_cushion()
    al, ar, af = apron_parts(hx_front, hy_front)
    parts["apron_l"], parts["apron_r"], parts["apron_f"] = al, ar, af

    front_h = SEAT_H - SEAT_T
    parts["leg_fl"] = front_leg(-hx_front, -hy_front, front_h)
    parts["leg_fr"] = front_leg(hx_front, -hy_front, front_h)
    parts["leg_bl"] = back_post(-x_post)
    parts["leg_br"] = back_post(x_post)

    parts["stretcher_l"] = side_stretcher(-1.0, hx_front, hy_front)
    parts["stretcher_r"] = side_stretcher(1.0, hx_front, hy_front)
    parts["stretcher_b"] = rear_stretcher()

    y_mid = post_y_at_z(SEAT_H + MID_FROM_SEAT + MID_H / 2.0)
    y_top = post_y_at_z(POST_TOP_Z)

    mid_w = STILE_OUTER - LEG + 8.0
    parts["mid_rail"] = curved_rail(
        width=mid_w,
        height=MID_H,
        thickness=TOP_RAIL_T,
        z_bottom=SEAT_H + MID_FROM_SEAT,
        sag=CURVE_SAG * 0.85,
        y_center=y_mid - TOP_RAIL_T / 2.0 - 1.0,
    )
    parts["top_rail"] = crescent_top_rail(y_top)

    return Compound(children=list(parts.values())), parts


def export_all(asm, parts):
    OUT.mkdir(parents=True, exist_ok=True)
    export_stl(asm, str(OUT / "chair_02.stl"))
    export_step(asm, str(OUT / "chair_02.step"))
    pdir = OUT / "parts"
    pdir.mkdir(exist_ok=True)
    for name, solid in parts.items():
        try:
            export_stl(solid, str(pdir / f"{name}.stl"))
        except Exception as e:
            print(f"skip {name}: {e}")
    # Sanity: print post bbox
    bb = parts["leg_bl"].bounding_box()
    print(
        f"leg_bl bbox Y [{bb.min.Y:.1f}, {bb.max.Y:.1f}] Z [{bb.min.Z:.1f}, {bb.max.Z:.1f}] "
        f"(expect Y near {Y_AT_SEAT:.0f}..{Y_FOOT:.0f}, Z top ~{POST_TOP_Z:.0f})"
    )
    print(f"wrote {OUT / 'chair_02.stl'}")


def main():
    asm, parts = build()
    export_all(asm, parts)


if __name__ == "__main__":
    main()
