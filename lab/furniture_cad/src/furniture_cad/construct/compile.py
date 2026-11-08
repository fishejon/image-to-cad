"""Compile furniture_ir.v1 → build123d assembly + derived parts (Phase 1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from build123d import Box, Compound, Pos

from furniture_cad.construct.blocks import divider as divider_block
from furniture_cad.construct.blocks import drawer_box, drawer_front, leg_set, top_panel
from furniture_cad.derive import part
from furniture_cad.derive_allowance import lists_with_allowances


def load_ir(path: Path | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(path, dict):
        return path
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _p(params: dict[str, float], key: str, default: float) -> float:
    return float(params.get(key, default))


def _compile_casegood(ir: dict[str, Any]) -> dict[str, Any]:
    params = ir.get("params") or {}
    root = ir.get("root") or {}
    mat = (ir.get("material") or {}).get("default") or "walnut"
    W = _p(params, "W", 1194)
    H = _p(params, "H", 762)
    D = _p(params, "D", 305)
    t = _p(params, "t", 19)
    leg_h = _p(params, "leg_h", 165)

    case_h = max(50.0, H - leg_h)
    side = Box(t, D, case_h)
    bottom = Box(W, D, t)
    back_t = 6.0
    back = Box(W - 2 * t, back_t, case_h - 2 * t)

    top_oh = ((root.get("carcass") or {}).get("top") or {}).get("overhang") or [0, 0, 0]
    top_blk = top_panel(W=W, D=D, t=t, overhang=list(top_oh), material=mat)

    children: list[Any] = [
        Pos(-W / 2 + t / 2, 0, leg_h + case_h / 2) * side,
        Pos(W / 2 - t / 2, 0, leg_h + case_h / 2) * side,
        Pos(0, 0, H - t / 2) * top_blk["solid"],
        Pos(0, 0, leg_h + t / 2) * bottom,
        Pos(0, -D / 2 + back_t / 2, leg_h + case_h / 2) * back,
    ]

    parts = [
        part("side", side, material=mat, qty=2, name="Side"),
        *top_blk["parts"],
        part("bottom", bottom, material=mat, qty=1, name="Bottom"),
        part("back", back, material="ply", qty=1, make="sheet", name="Back"),
    ]

    features: dict[str, int] = {"drawer": 0, "door": 0, "leg": 0, "shelf": 0}

    div_t = 0.0
    if root.get("divider"):
        div_t = float((root["divider"] or {}).get("t") or t)
        div = divider_block(width=D - back_t - 4, height=case_h - 2 * t, thickness=div_t, material=mat)
        children.append(Pos(0, 0, leg_h + case_h / 2) * div["solid"])
        parts.extend(div["parts"])

    legs_spec = root.get("legs") or {}
    if legs_spec:
        legs = leg_set(
            count=int(legs_spec.get("count") or 4),
            top=list(legs_spec.get("top") or [38, 38]),
            foot=list(legs_spec.get("foot") or legs_spec.get("top") or [38, 38]),
            height=leg_h,
            splay_deg=float(legs_spec.get("splay_deg") or 0),
            material=mat,
        )
        features["leg"] = int(legs["meta"]["count"])
        inset = legs_spec.get("inset") or [45, 45]
        ix, iy = float(inset[0]), float(inset[1])
        lx = float((legs_spec.get("top") or [38, 38])[0])
        ly = float((legs_spec.get("top") or [38, 38])[1])
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            children.append(
                Pos(sx * (W / 2 - ix - lx / 2), sy * (D / 2 - iy - ly / 2), leg_h / 2) * legs["solid"]
            )
        parts.extend(legs["parts"])

    bays = root.get("bays") or []
    n_bays = max(1, len(bays))
    bay_w = (W - 2 * t - div_t) / n_bays
    x0 = -W / 2 + t
    for i, bay in enumerate(bays):
        kind = (bay or {}).get("kind") or "open"
        cx = x0 + bay_w * (i + 0.5) + (div_t / 2 if div_t and i >= 1 else 0)
        if kind == "drawer_bank":
            n = int((bay or {}).get("n") or 2)
            features["drawer"] += n
            dh = (case_h - 2 * t) / n
            front_spec = (bay or {}).get("front") or {}
            ft = float(front_spec.get("t") or t)
            for j in range(n):
                z = leg_h + t + dh * (j + 0.5)
                box = drawer_box(W=bay_w * 0.88, D=D * 0.85, H=dh * 0.75, material="maple")
                children.append(Pos(cx, 0, z) * box["assembly"])
                # Only count parts once per bank size (qty via n) — keep first box parts×n
                if j == 0:
                    for p in box["parts"]:
                        p.qty = p.qty * n
                        parts.append(p)
                front = drawer_front(W=bay_w * 0.92, H=dh * 0.85, t=ft, material=mat)
                children.append(Pos(cx, D / 2 - ft / 2, z) * front["solid"])
                if j == 0:
                    fr = front["parts"][0]
                    fr.qty = n
                    parts.append(fr)
        elif kind == "open" and (bay or {}).get("shelf"):
            features["shelf"] += 1

    assembly = Compound(children=children)
    cut_v2 = lists_with_allowances(parts)
    return {
        "assembly": assembly,
        "parts": parts,
        "cut_list_v2": cut_v2,
        "features": features,
        "meta": {"compiler": "furniture_ir.v1.phase1", "W": W, "D": D, "H": H, "type": "casegood"},
        "ir": ir,
    }


def compile_ir(ir: dict[str, Any] | Path | str) -> dict[str, Any]:
    data = load_ir(ir)
    if data.get("schema") != "furniture_ir.v1":
        raise ValueError(f"expected furniture_ir.v1, got {data.get('schema')!r}")
    root = data.get("root") or {}
    rtype = root.get("type") or "casegood"
    if rtype == "casegood":
        return _compile_casegood(data)
    raise ValueError(f"IR root.type {rtype!r} not supported yet (Phase 1: casegood only)")
