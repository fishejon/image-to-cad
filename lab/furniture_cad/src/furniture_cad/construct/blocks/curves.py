"""Curve / sweep / laminate blocks (Phase 3 scaffolding)."""

from __future__ import annotations

from typing import Any

from build123d import Box, BuildPart, BuildSketch, Compound, Plane, Pos, Rectangle, loft

from furniture_cad.derive import part


def sweep_rail(
    *,
    length: float,
    width: float = 40.0,
    thickness: float = 20.0,
    camber_mm: float = 0.0,
    material: str = "oak",
) -> dict[str, Any]:
    """Straight rail with optional camber approximated by loft (blank padded)."""
    if camber_mm <= 0:
        solid = Box(length, thickness, width)
    else:
        with BuildPart() as bp:
            with BuildSketch(Plane.XY):
                Rectangle(thickness, width)
            with BuildSketch(Plane.XY.offset(length)):
                Rectangle(thickness, width)
            loft()
            # Camber: raise mid via second loft pass is heavy — pad blank instead
        solid = bp.part
    pad = max(2.0, float(camber_mm) * 0.5)
    rec = part(
        "sweep_rail",
        solid,
        material=material,
        qty=1,
        name="Sweep rail",
        make="shaped",
        blank_pad_mm=pad,
    )
    return {"solid": solid, "parts": [rec], "meta": {"block": "sweep_rail", "camber_mm": camber_mm}}


def laminate_blank(
    *,
    finished_t: float,
    finished_w: float,
    finished_l: float,
    plies: int = 5,
    springback_pct: float = 0.02,
    material: str = "oak",
) -> dict[str, Any]:
    """Derive laminated blank size from finished curve envelope."""
    plies = max(2, int(plies))
    ply_t = finished_t / plies
    # Blank longer for bend + springback
    blank_l = finished_l * (1.0 + float(springback_pct)) + 25.0
    blank_w = finished_w + 6.0
    blank_t = finished_t + 2.0
    solid = Box(blank_l, blank_w, blank_t)
    rec = part(
        "laminate",
        solid,
        material=material,
        qty=1,
        name=f"Laminate blank ({plies} ply)",
        make="shaped",
    )
    rec.blank_thickness_mm = blank_t
    rec.blank_width_mm = blank_w
    rec.blank_length_mm = blank_l
    rec.notes = f"plies={plies}; ply_t≈{ply_t:.2f}; springback={springback_pct}"
    return {
        "solid": solid,
        "parts": [rec],
        "meta": {"block": "laminate_blank", "plies": plies, "ply_t": ply_t, "blank_mm": [blank_t, blank_w, blank_l]},
    }


def spline_stile_approx(
    *,
    height: float,
    top_w: float = 45.0,
    mid_w: float = 55.0,
    bot_w: float = 40.0,
    thickness: float = 22.0,
    material: str = "oak",
) -> dict[str, Any]:
    """Three-section loft approximating a curved stile (template-free)."""
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            Rectangle(thickness, bot_w)
        with BuildSketch(Plane.XY.offset(height * 0.45)):
            Rectangle(thickness, mid_w)
        with BuildSketch(Plane.XY.offset(height)):
            Rectangle(thickness, top_w)
        loft()
    solid = bp.part
    rec = part("spline_stile", solid, material=material, qty=1, name="Spline stile", make="shaped", blank_pad_mm=8.0)
    return {"solid": solid, "parts": [rec], "meta": {"block": "spline_stile"}}


def chair_side_assembly(
    *,
    seat_h: float = 450.0,
    seat_d: float = 420.0,
    seat_w: float = 450.0,
    back_h: float = 420.0,
    material: str = "oak",
) -> dict[str, Any]:
    """Minimal template-free chair from blocks (rectilinear + loft stile)."""
    from furniture_cad.blocks.tapered_leg import tapered_leg

    leg_f = tapered_leg(height=seat_h, top_size=38, bot_size=28, section="square")
    leg_b = tapered_leg(height=seat_h + back_h * 0.35, top_size=38, bot_size=28, section="square")
    seat = Box(seat_w, seat_d, 22)
    stile = spline_stile_approx(height=back_h, material=material)
    children = [
        Pos(-seat_w / 2 + 40, -seat_d / 2 + 40, seat_h / 2) * leg_f,
        Pos(seat_w / 2 - 40, -seat_d / 2 + 40, seat_h / 2) * leg_f,
        Pos(-seat_w / 2 + 40, seat_d / 2 - 40, (seat_h + back_h * 0.35) / 2) * leg_b,
        Pos(seat_w / 2 - 40, seat_d / 2 - 40, (seat_h + back_h * 0.35) / 2) * leg_b,
        Pos(0, 0, seat_h + 11) * seat,
        Pos(-seat_w / 2 + 30, seat_d / 2 - 30, seat_h + back_h / 2) * stile["solid"],
        Pos(seat_w / 2 - 30, seat_d / 2 - 30, seat_h + back_h / 2) * stile["solid"],
    ]
    parts = [
        part("front_leg", leg_f, material=material, qty=2, name="Front leg", make="shaped"),
        part("back_leg", leg_b, material=material, qty=2, name="Back leg", make="shaped"),
        part("seat", seat, material=material, qty=1, name="Seat"),
    ]
    stile["parts"][0].qty = 2
    parts.extend(stile["parts"])
    return {
        "assembly": Compound(children=children),
        "parts": parts,
        "meta": {"block": "chair_side_assembly", "seat_h": seat_h, "label": "approximate"},
    }


CURVE_BLOCKS = {
    "sweep_rail": sweep_rail,
    "laminate_blank": laminate_blank,
    "spline_stile": spline_stile_approx,
    "chair_side_assembly": chair_side_assembly,
}
