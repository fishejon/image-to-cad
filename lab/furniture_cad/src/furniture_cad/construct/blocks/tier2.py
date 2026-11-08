"""Tier-2 blocks — tables, benches, stools, angled legs (Phase 2)."""

from __future__ import annotations

import math
from typing import Any

from build123d import Box, Compound, Pos, Rot

from furniture_cad.construct.blocks.casegood import apron, leg_set, stretcher
from furniture_cad.derive import part


def angled_leg(
    *,
    height: float = 720.0,
    top: list[float] | None = None,
    foot: list[float] | None = None,
    splay_deg: float = 8.0,
    material: str = "oak",
) -> dict[str, Any]:
    """Leg with plan-view splay; compound cut blank uses max section + length pad."""
    top = top or [45.0, 45.0]
    foot = foot or [32.0, 32.0]
    lx = max(float(top[0]), float(foot[0]))
    ly = max(float(top[1]), float(foot[1]))
    # Approximate splay as longer blank along vertical
    blank_h = height / max(0.5, math.cos(math.radians(splay_deg)))
    solid = Box(lx, ly, height)
    # Tilt in XZ for silhouette mass
    placed = Rot(0, splay_deg, 0) * solid
    rec = part(
        "angled_leg",
        solid,
        material=material,
        qty=1,
        name="Angled leg",
        make="shaped",
        blank_pad_mm=max(5.0, blank_h - height),
    )
    return {
        "solid": placed,
        "parts": [rec],
        "meta": {"block": "angled_leg", "splay_deg": splay_deg, "blank_h": blank_h},
    }


def table(
    *,
    W: float,
    D: float,
    H: float,
    top_t: float = 25.0,
    apron_h: float = 70.0,
    leg_section: list[float] | None = None,
    material: str = "oak",
) -> dict[str, Any]:
    """Rectilinear 4-leg table with apron."""
    leg_section = leg_section or [45.0, 45.0]
    leg_h = max(50.0, H - top_t)
    top = Box(W, D, top_t)
    legs = leg_set(count=4, top=leg_section, height=leg_h, material=material)
    ap_l = apron(length=W - 2 * leg_section[0] - 10, height=apron_h, material=material)
    ap_w = apron(length=D - 2 * leg_section[1] - 10, height=apron_h, material=material)
    inset = 40.0
    lx, ly = float(leg_section[0]), float(leg_section[1])
    children = [
        Pos(0, 0, H - top_t / 2) * top,
        Pos(-(W / 2 - inset - lx / 2), -(D / 2 - inset - ly / 2), leg_h / 2) * legs["solid"],
        Pos(W / 2 - inset - lx / 2, -(D / 2 - inset - ly / 2), leg_h / 2) * legs["solid"],
        Pos(-(W / 2 - inset - lx / 2), D / 2 - inset - ly / 2, leg_h / 2) * legs["solid"],
        Pos(W / 2 - inset - lx / 2, D / 2 - inset - ly / 2, leg_h / 2) * legs["solid"],
        Pos(0, -(D / 2 - inset), leg_h - apron_h / 2) * ap_l["solid"],
        Pos(0, D / 2 - inset, leg_h - apron_h / 2) * ap_l["solid"],
        Pos(-(W / 2 - inset), 0, leg_h - apron_h / 2) * Rot(0, 0, 90) * ap_w["solid"],
        Pos(W / 2 - inset, 0, leg_h - apron_h / 2) * Rot(0, 0, 90) * ap_w["solid"],
    ]
    parts = [
        part("top", top, material=material, qty=1, name="Table top"),
        *legs["parts"],
    ]
    ap_l["parts"][0].qty = 2
    ap_w["parts"][0].qty = 2
    ap_w["parts"][0].id = "apron_end"
    parts.extend(ap_l["parts"])
    parts.extend(ap_w["parts"])
    return {
        "assembly": Compound(children=children),
        "parts": parts,
        "meta": {"block": "table", "W": W, "D": D, "H": H},
    }


def bench(
    *,
    W: float,
    D: float = 350.0,
    H: float = 450.0,
    top_t: float = 32.0,
    material: str = "oak",
) -> dict[str, Any]:
    """Simple bench: top + 4 legs + long stretchers."""
    leg_h = max(50.0, H - top_t)
    top = Box(W, D, top_t)
    legs = leg_set(count=4, top=[38, 38], height=leg_h, material=material)
    st = stretcher(length=W - 100, width=38, thickness=19, material=material)
    children = [
        Pos(0, 0, H - top_t / 2) * top,
        Pos(-W / 2 + 50, -D / 2 + 40, leg_h / 2) * legs["solid"],
        Pos(W / 2 - 50, -D / 2 + 40, leg_h / 2) * legs["solid"],
        Pos(-W / 2 + 50, D / 2 - 40, leg_h / 2) * legs["solid"],
        Pos(W / 2 - 50, D / 2 - 40, leg_h / 2) * legs["solid"],
        Pos(0, -D / 2 + 40, 120) * st["solid"],
        Pos(0, D / 2 - 40, 120) * st["solid"],
    ]
    st["parts"][0].qty = 2
    parts = [part("seat", top, material=material, qty=1, name="Bench seat"), *legs["parts"], *st["parts"]]
    return {"assembly": Compound(children=children), "parts": parts, "meta": {"block": "bench", "W": W, "D": D, "H": H}}


def stool(
    *,
    W: float = 320.0,
    D: float = 320.0,
    H: float = 450.0,
    top_t: float = 25.0,
    material: str = "oak",
) -> dict[str, Any]:
    """Four-leg stool."""
    return table(W=W, D=D, H=H, top_t=top_t, apron_h=40.0, leg_section=[32, 32], material=material) | {
        "meta": {"block": "stool", "W": W, "D": D, "H": H}
    }


TIER2_BLOCKS = {
    "angled_leg": angled_leg,
    "table": table,
    "bench": bench,
    "stool": stool,
}
