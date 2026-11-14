"""Build furniture_ir.v2 from Perceive observation + Dimension (no answer-key seed)."""

from __future__ import annotations

from typing import Any

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
    stock = dims.get("stock") or {}
    wall = float(stock.get("t_panel") or 19.0)
    back_t = float(stock.get("t_back") or 6.0)

    # Proportions measured by Perceive win; otherwise fall back to a generic prior
    # (case underside ~35% of height for a freestanding casegood), clamped to a sane range.
    props = observation.get("proportions") or {}
    prior_under_z = max(80.0, min(H * 0.35, H - 120.0))
    uz_frac = props.get("under_z_frac")
    extra = dims.get("known_extra_mm") or {}
    if extra.get("leg_h"):
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
    if extra.get("drawer_front_h"):
        # front height = opening - 2 reveals, so opening = front + 2 reveals
        case_h = max(40.0, H - under_z)
        bank_frac = max(0.05, min(0.95, (float(extra["drawer_front_h"]) + 2 * reveal) / case_h))
        bank_src = "user"

    end_form = str(observation.get("end_form") or "").lower()
    leg_style = str(observation.get("leg_style") or "").lower()
    swept = any(x in end_form for x in ("swept", "leaning")) or "console" in (
        str(observation.get("class") or class_hint).lower()
    )

    lean_deg = 6.0 if swept else 0.0
    sweep_r = min(D * 0.4, W * 0.12, 150.0) if swept else 0.0
    # Compiler currently only implements swept_shell for v2.
    form = "swept_shell"
    if not swept:
        lean_deg = 0.0
        sweep_r = max(25.0, min(D * 0.15, 60.0))  # mild ease so shell still compiles

    drawers = max(0, int(counts.get("drawer") or 0))
    open_cubby = max(0, int(counts.get("open_cubby") or 0))
    shelf = max(0, int(counts.get("shelf") or 0))
    legs_n = max(0, int(counts.get("leg") or 0))
    if legs_n == 0 and str(observation.get("class") or class_hint).startswith("casegood"):
        legs_n = 4  # freestanding prior when Perceive omitted legs

    children: list[dict[str, Any]] = []
    if drawers > 0:
        bank: dict[str, Any] = {
            "kind": "drawer_bank",
            "cols": drawers,
            "front": {"t": 19.0, "reveal": reveal, "corner": "follow_outline" if swept else "square"},
        }
        if bank_frac is not None:
            bank["bank_frac"] = float(bank_frac)
        children.append(bank)
    if open_cubby > 0 or shelf > 0:
        children.append({"kind": "open", "setback": wall})
    if not children:
        # Closed case fallback: one open bay so shell has a layout.
        children.append({"kind": "open", "setback": wall})

    flared = "flared" in leg_style or "two_profile" in leg_style or swept
    legs: dict[str, Any] | None = None
    if legs_n > 0:
        if flared:
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
            legs = {
                "style": "square",
                "count": legs_n,
                "top": [38.0, 38.0],
                "foot": [38.0, 38.0],
                "flare_r": [0.0, 0.0, 0.0],
                "splay_deg": 0.0,
                "inset": [40.0, 35.0],
            }

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
        "material": {"default": "walnut", "hidden": "poplar"},
        "carcass": {
            "form": form,
            "outline": {
                "lean_deg": lean_deg,
                "sweep_r": round(sweep_r, 3),
                "wall": wall,
                "under_z": round(under_z, 3),
            },
            "open_front": True,
            "top": {"kind": "plank", "edge_r": 3.0},
            "back": {"t": back_t, "kind": "floating", "groove": min(back_t, 9.5)},
        },
        "layout": {"split": "z", "children": children},
        "notes": [
            "Constructed from Perceive observation + Dimension (generic casegood template).",
            f"class={observation.get('class') or class_hint}",
            f"counts={counts}",
            f"under_z from {under_src}"
            + (" (prior 0.35 H)" if under_src == "prior" else f" ({round(under_z, 1)} mm)"),
            f"drawer bank height from {bank_src}",
        ],
    }
    if legs:
        ir["legs"] = legs
    return ir
