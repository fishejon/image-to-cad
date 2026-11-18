"""Build furniture_ir.v2 from Perceive observation + Dimension (no answer-key seed)."""

from __future__ import annotations

from typing import Any

from furniture_cad.construct.layout_build import build_layout_children
from furniture_cad.perceive import feature_counts_from_observation


def _overall_mm(dims: dict[str, Any]) -> dict[str, float]:
    overall = dims.get("overall_mm") or {}
    out: dict[str, float] = {}
    for letter, key in (("W", "w"), ("D", "d"), ("H", "h")):
        entry = overall.get(letter) or {}
        if entry.get("v") is not None:
            out[letter] = float(entry["v"])
        elif dims.get(key) is not None:
            out[letter] = float(dims[key])
    return out


def _stock_priors(cls: str, *, swept: bool) -> dict[str, Any]:
    """Class stock / overhang priors when Dimension does not supply panel thickness.

    Overall W×D is the AABB footprint (top included). Overhang shrinks the carcass
    under a flush-to-overall top: [front, side, back] mm.
    """
    c = (cls or "").lower()
    if "nightstand" in c:
        return {"wall": 18.0, "top_t": 25.4, "back_t": 0.0, "overhang": [0.0, 0.0, 0.0]}
    if "bookcase" in c:
        return {"wall": 18.0, "top_t": 34.0, "back_t": 0.0, "overhang": [0.0, 0.0, 0.0]}
    if "console" in c or swept:
        return {"wall": 22.225, "top_t": 22.225, "back_t": 12.7, "overhang": [0.0, 0.0, 0.0]}
    if "sideboard" in c:
        # Synthetic / typical flat sideboard: 3/4 wall, 5/4 top, 3/4 overhang F+S
        return {"wall": 19.05, "top_t": 25.4, "back_t": 6.35, "overhang": [19.05, 19.05, 0.0]}
    if "credenza" in c:
        return {"wall": 20.0, "top_t": 22.0, "back_t": 6.0, "overhang": [0.0, 0.0, 0.0]}
    # Generic freestanding casegood — small plank overhang
    return {"wall": 19.05, "top_t": 22.0, "back_t": 6.0, "overhang": [12.0, 12.0, 0.0]}


def construct_ir_from_observation(
    observation: dict[str, Any],
    dims: dict[str, Any],
    *,
    class_hint: str = "casegood.console",
) -> dict[str, Any]:
    """Generic casegood IR from counts + overall size.

    Uses stock defaults and proportional undercarriage — never copies
    console_01 answer-key geometry (lean/sweep/under_z from Fusion).
    """
    counts = feature_counts_from_observation(observation)
    overall = _overall_mm(dims)
    if not all(k in overall for k in ("W", "D", "H")):
        raise ValueError("construct_requires_W_D_H")

    W, D, H = overall["W"], overall["D"], overall["H"]
    cls = str(observation.get("class") or class_hint)
    end_form = str(observation.get("end_form") or "").lower()
    leg_style = str(observation.get("leg_style") or "").lower()
    swept = any(x in end_form for x in ("swept", "leaning")) or "console" in cls.lower()

    priors = _stock_priors(cls, swept=swept)
    stock = dims.get("stock") or {}
    wall = float(stock.get("t_panel") or priors["wall"])
    back_t = float(stock.get("t_back") or priors["back_t"])
    top_t = float(stock.get("t_top") or priors["top_t"])
    overhang = list(priors["overhang"])
    if stock.get("overhang") is not None:
        oh = stock["overhang"]
        overhang = [float(oh[0]), float(oh[1]), float(oh[2])] if len(oh) >= 3 else overhang

    drawers = max(0, int(counts.get("drawer") or 0))
    doors = max(0, int(counts.get("door") or 0))
    open_cubby = max(0, int(counts.get("open_cubby") or 0))
    shelf = max(0, int(counts.get("shelf") or 0))
    legs_n = max(0, int(counts.get("leg") or 0))
    if legs_n == 0 and cls.startswith("casegood"):
        legs_n = 4  # freestanding prior when Perceive omitted legs

    drawer_layout = str(observation.get("drawer_layout") or "")
    door_style = str(observation.get("door_style") or "")
    layout_facing = str(observation.get("layout_facing") or "")
    joinery_cue = str(observation.get("joinery_cue") or "")
    frame_style = str(observation.get("frame_style") or "")
    stacked = "stack" in drawer_layout.lower() or (doors > 0 and drawers > 1 and "side" not in drawer_layout.lower())
    rows_for_bank = drawers if stacked and drawers > 0 else 1

    is_nightstand = "nightstand" in cls.lower()
    is_bookcase = "bookcase" in cls.lower()

    # Proportions measured by Perceive win; otherwise fall back to a generic prior
    # (case underside ~35% of height for a freestanding casegood), clamped to a sane range.
    props = observation.get("proportions") or {}
    prior_under_z = max(80.0, min(H * 0.35, H - 120.0))
    if is_nightstand:
        # Short case band under the top; legs are full-height posts (H - top_t).
        prior_under_z = max(80.0, min(H * 0.55, H - top_t - 80.0))
    elif is_bookcase:
        prior_under_z = 0.0
    uz_frac = props.get("under_z_frac")
    extra = dims.get("known_extra_mm") or {}
    if is_bookcase:
        under_z = 0.0
        under_src = "bookcase"
    elif is_nightstand and extra.get("leg_h"):
        # Assist leg length is the post; case sits between posts near the top.
        under_z = max(80.0, min(H - top_t - max(80.0, float(extra.get("drawer_front_h") or 120.0) * 1.4), H - 80.0))
        under_src = "nightstand_frame"
    elif extra.get("leg_h") and not is_nightstand:
        under_z = max(80.0, min(float(extra["leg_h"]), H - 120.0))
        under_src = "user"
    elif uz_frac is not None:
        under_z = max(80.0, min(H * float(uz_frac), H - 120.0))
        under_src = "perceive"
    else:
        under_z = prior_under_z
        under_src = "prior"
    bank_frac = props.get("drawer_bank_frac")
    bank_src = "perceive" if bank_frac is not None else "default fractions"
    reveal = 1.5
    case_h = max(40.0, H - under_z - (0.0 if is_bookcase else 0.0))
    if not is_bookcase:
        case_h = max(40.0, H - under_z)
    if extra.get("drawer_front_h") and not is_bookcase:
        front_h = float(extra["drawer_front_h"])
        # Stacked: N fronts + (N+1) reveals fill the bank opening.
        span = rows_for_bank * front_h + (rows_for_bank + 1) * reveal
        bank_frac = max(0.05, min(0.98, span / max(40.0, case_h)))
        bank_src = "user"

    form = "bookcase_frame" if is_bookcase else ("frame_nightstand" if is_nightstand else "swept_shell")
    lean_deg = 6.0 if swept and form == "swept_shell" else 0.0
    sweep_r = min(D * 0.4, W * 0.12, 150.0) if (swept and form == "swept_shell") else 0.0

    children, split = build_layout_children(
        drawers=drawers,
        doors=doors,
        open_cubby=open_cubby,
        shelf=shelf,
        wall=wall,
        reveal=reveal,
        bank_frac=float(bank_frac) if bank_frac is not None else None,
        drawer_layout=drawer_layout,
        door_style=door_style,
        layout_facing=layout_facing,
        form_hint=form,
        proportions=props,
        overall_w=W,
        overall_d=D,
        overall_h=H,
    )

    flared = "flared" in leg_style or "two_profile" in leg_style or swept
    legs: dict[str, Any] | None = None
    if legs_n > 0 and form != "bookcase_frame":
        if is_nightstand:
            legs = {
                "style": "square_rounded",
                "count": legs_n,
                "top": [30.0, 30.0],
                "foot": [30.0, 30.0],
                "flare_r": [0.0, 0.0, 0.0],
                "splay_deg": 0.0,
                "inset": [0.0, 0.0],
                "height_mode": "full_minus_top",
            }
        elif flared:
            legs = {
                "style": "two_profile_flared",
                "count": legs_n,
                "top": [50.0, 40.0],
                "foot": [28.0, 25.0],
                "flare_r": [20.0, 40.0, 20.0],
                "splay_deg": 5.0,
                "inset": [40.0, 35.0],
            }
        else:
            # Tapered square prior (credenza / sideboard)
            top = 42.0 if "taper" in leg_style else 38.0
            foot = 24.0 if "taper" in leg_style else top
            if "credenza" in cls.lower():
                top, foot = 47.0, 32.0
            splay = 4.0 if "splay" in leg_style or "taper" in leg_style else 0.0
            legs = {
                "style": "tapered" if foot != top else "square",
                "count": legs_n,
                "top": [top, top],
                "foot": [foot, foot],
                "flare_r": [0.0, 0.0, 0.0],
                "splay_deg": splay,
                "inset": [50.0, 50.0],
            }

    end_profile = "swept" if swept else ("rounded_bottom" if "round" in end_form else "plain")
    ir: dict[str, Any] = {
        "schema": "furniture_ir.v2",
        "units": "mm",
        "params": {
            "W": W,
            "H": H,
            "D": D,
            "wall": wall,
            "under_z": round(under_z, 3),
            "lean_deg": lean_deg,
            "sweep_r": round(sweep_r, 3),
            "back_t": back_t,
        },
        "material": {
            "default": "cherry" if is_nightstand else "walnut",
            "hidden": "poplar",
        },
        "carcass": {
            "form": form,
            "outline": {
                "lean_deg": lean_deg,
                "sweep_r": round(sweep_r, 3),
                "wall": wall,
                "under_z": round(under_z, 3),
            },
            "open_front": True,
            "top": {
                "kind": "plank",
                "edge_r": 3.0,
                "t": top_t,
                "overhang": [round(float(x), 3) for x in overhang],
            },
            "back": {
                "t": back_t,
                "kind": "floating",
                # Console uses a groove; straight multi-bay pieces usually don't pad the blank.
                "groove": (min(back_t, 9.5) if swept and form == "swept_shell" else 0.0),
            },
            "end_profile": {"kind": end_profile, "r": 45.0 if end_profile == "rounded_bottom" else 0.0},
        },
        "layout": {"split": split, "children": children},
        "notes": [
            "Constructed from Perceive observation + Dimension (generic casegood template).",
            f"class={cls}",
            f"counts={counts}",
            f"layout={drawer_layout or 'default'} door_style={door_style or 'none'} split={split}",
            f"under_z from {under_src}"
            + (" (prior 0.35 H)" if under_src == "prior" else f" ({round(under_z, 1)} mm)"),
            f"drawer bank height from {bank_src}",
            f"stock wall={wall} top_t={top_t} overhang={overhang}",
        ],
    }
    if legs:
        ir["legs"] = legs
    if joinery_cue:
        ir["attrs"] = {"joinery_cue": joinery_cue, "frame_style": frame_style}
        # Slide-rail blanks for nightstand when Perceive/oracle notes them
        if "slide" in joinery_cue.lower() or "rail" in joinery_cue.lower():
            ir.setdefault("joinery", {})["blanks"] = [
                {
                    "id": "SR1",
                    "name": "Drawer slide rail",
                    "qty": 2,
                    "thickness_mm": 14.0,
                    "width_mm": 28.0,
                    "length_mm": max(80.0, D * 0.55),
                    "material": "walnut",
                }
            ]
    if is_bookcase and props.get("cabinet_z0_mm") is not None:
        ir.setdefault("attrs", {})["cabinet_z0_mm"] = float(props["cabinet_z0_mm"])
        ir.setdefault("attrs", {})["cabinet_z1_mm"] = float(props.get("cabinet_z1_mm") or 0)
        if props.get("shelf_z_mm"):
            ir["attrs"]["shelf_z_mm"] = [float(z) for z in props["shelf_z_mm"]]
    return ir
