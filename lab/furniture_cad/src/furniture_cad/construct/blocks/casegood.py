"""Tier-1 casegood blocks — rectilinear solids for IR compiler."""

from __future__ import annotations

from typing import Any

from build123d import Box, Compound, Pos

from furniture_cad.derive import part


def divider(*, width: float, height: float, thickness: float = 19.0, material: str = "walnut") -> dict[str, Any]:
    solid = Box(thickness, width, height)
    return {
        "solid": solid,
        "parts": [part("divider", solid, material=material, qty=1, name="Divider")],
        "meta": {"block": "divider"},
    }


def top_panel(*, W: float, D: float, t: float = 19.0, overhang: list[float] | None = None, material: str = "walnut") -> dict[str, Any]:
    oh = overhang or [0.0, 0.0, 0.0]
    # overhang: [front, side, back] — enlarge footprint
    Ww = W + 2 * float(oh[1] if len(oh) > 1 else 0)
    Dd = D + float(oh[0] if oh else 0) + float(oh[2] if len(oh) > 2 else 0)
    solid = Box(Ww, Dd, t)
    return {
        "solid": solid,
        "parts": [part("top", solid, material=material, qty=1, name="Top")],
        "meta": {"block": "top", "overhang": oh},
    }


def drawer_box(
    *,
    W: float,
    D: float,
    H: float,
    t: float = 12.0,
    bottom_t: float = 6.0,
    material: str = "maple",
) -> dict[str, Any]:
    """Open-top drawer box (four sides + bottom), centered at origin."""
    side = Box(t, D, H)
    front_back = Box(W - 2 * t, t, H)
    bottom = Box(W - 2 * t, D - 2 * t, bottom_t)
    children = [
        Pos(-W / 2 + t / 2, 0, 0) * side,
        Pos(W / 2 - t / 2, 0, 0) * side,
        Pos(0, D / 2 - t / 2, 0) * front_back,
        Pos(0, -D / 2 + t / 2, 0) * front_back,
        Pos(0, 0, -H / 2 + bottom_t / 2) * bottom,
    ]
    assembly = Compound(children=children)
    parts = [
        part("drawer_side", side, material=material, qty=2, name="Drawer side"),
        part("drawer_fb", front_back, material=material, qty=2, name="Drawer front/back"),
        part("drawer_bottom", bottom, material="ply", qty=1, make="sheet", name="Drawer bottom"),
    ]
    return {"assembly": assembly, "parts": parts, "meta": {"block": "drawer_box", "W": W, "D": D, "H": H}}


def drawer_front(*, W: float, H: float, t: float = 19.0, material: str = "walnut") -> dict[str, Any]:
    solid = Box(W, t, H)
    return {
        "solid": solid,
        "parts": [part("drawer_front", solid, material=material, qty=1, name="Drawer front")],
        "meta": {"block": "drawer_front"},
    }


def door(*, W: float, H: float, t: float = 19.0, style: str = "slab", material: str = "walnut") -> dict[str, Any]:
    solid = Box(W, t, H)
    return {
        "solid": solid,
        "parts": [part("door", solid, material=material, qty=1, name=f"Door ({style})")],
        "meta": {"block": "door", "style": style},
    }


def face_frame(
    *,
    W: float,
    H: float,
    stile_w: float = 45.0,
    rail_w: float = 45.0,
    t: float = 19.0,
    material: str = "walnut",
) -> dict[str, Any]:
    stile = Box(stile_w, t, H)
    rail = Box(max(10.0, W - 2 * stile_w), t, rail_w)
    children = [
        Pos(-W / 2 + stile_w / 2, 0, H / 2) * stile,
        Pos(W / 2 - stile_w / 2, 0, H / 2) * stile,
        Pos(0, 0, H - rail_w / 2) * rail,
        Pos(0, 0, rail_w / 2) * rail,
    ]
    assembly = Compound(children=children)
    parts = [
        part("stile", stile, material=material, qty=2, name="Face-frame stile"),
        part("rail", rail, material=material, qty=2, name="Face-frame rail"),
    ]
    return {"assembly": assembly, "parts": parts, "meta": {"block": "face_frame"}}


def leg_set(
    *,
    count: int = 4,
    top: list[float] | None = None,
    foot: list[float] | None = None,
    height: float = 165.0,
    splay_deg: float = 0.0,
    material: str = "walnut",
) -> dict[str, Any]:
    """Square/tapered legs (taper approximated as top section for Phase 1)."""
    top = top or [38.0, 38.0]
    foot = foot or top
    # Use max section so blank covers taper; solid uses top for now
    lx, ly = float(top[0]), float(top[1])
    solid = Box(lx, ly, height)
    parts = [
        part(
            "leg",
            solid,
            material=material,
            qty=max(1, int(count)),
            name="Leg",
            make="shaped" if foot != top or splay_deg else "solid",
            blank_pad_mm=3.0 if foot != top else 0.0,
        )
    ]
    return {
        "solid": solid,
        "parts": parts,
        "meta": {"block": "leg_set", "count": count, "splay_deg": splay_deg, "top": top, "foot": foot},
    }


def apron(*, length: float, height: float = 70.0, thickness: float = 19.0, material: str = "walnut") -> dict[str, Any]:
    solid = Box(length, thickness, height)
    return {
        "solid": solid,
        "parts": [part("apron", solid, material=material, qty=1, name="Apron")],
        "meta": {"block": "apron"},
    }


def stretcher(*, length: float, width: float = 38.0, thickness: float = 19.0, material: str = "walnut") -> dict[str, Any]:
    solid = Box(length, thickness, width)
    return {
        "solid": solid,
        "parts": [part("stretcher", solid, material=material, qty=1, name="Stretcher")],
        "meta": {"block": "stretcher"},
    }


TIER1_BLOCKS = {
    "divider": divider,
    "top": top_panel,
    "top_panel": top_panel,
    "drawer_box": drawer_box,
    "drawer_front": drawer_front,
    "door": door,
    "face_frame": face_frame,
    "leg_set": leg_set,
    "apron": apron,
    "stretcher": stretcher,
}
