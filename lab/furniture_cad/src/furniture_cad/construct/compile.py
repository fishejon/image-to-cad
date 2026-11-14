"""Compile furniture_ir.v1/v2 → build123d assembly + derived parts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from build123d import Box, Compound, Pos

from furniture_cad.construct.blocks import divider as divider_block
from furniture_cad.construct.blocks import drawer_box, drawer_front, leg_set, top_panel
from furniture_cad.construct.blocks.flared_leg import leg_set_flared
from furniture_cad.construct.blocks.swept_shell import swept_shell
from furniture_cad.construct.validate_ir import validate_ir
from furniture_cad.derive import part
from furniture_cad.derive_allowance import lists_with_allowances


def load_ir(path: Path | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(path, dict):
        return path
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _p(params: dict[str, float], key: str, default: float) -> float:
    return float(params.get(key, default))


def ir_hash(ir: dict[str, Any]) -> str:
    blob = json.dumps(ir, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _compile_casegood_v1(ir: dict[str, Any]) -> dict[str, Any]:
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
        "meta": {"compiler": "furniture_ir.v1", "W": W, "D": D, "H": H, "type": "casegood"},
        "ir": ir,
        "report": {"ok": True, "ir_hash": ir_hash(ir)},
    }


def _compile_v2(ir: dict[str, Any]) -> dict[str, Any]:
    check = validate_ir(ir)
    if not check.get("ok"):
        raise ValueError(f"ir_invalid: {check.get('errors')}")

    params = ir.get("params") or {}
    mat = (ir.get("material") or {}).get("default") or "walnut"
    hidden = (ir.get("material") or {}).get("hidden") or "poplar"
    W = _p(params, "W", 1193.8)
    H = _p(params, "H", 762.0)
    D = _p(params, "D", 304.8)
    carcass = ir.get("carcass") or {}
    outline = carcass.get("outline") or {}
    wall = float(outline.get("wall") or params.get("wall") or 22.225)
    under_z = float(outline.get("under_z") or params.get("under_z") or 495.3)
    lean_deg = float(outline.get("lean_deg") or params.get("lean_deg") or 6.0)
    sweep_r = float(outline.get("sweep_r") or params.get("sweep_r") or 121.92)
    back_t = float(params.get("back_t") or (carcass.get("back") or {}).get("t") or 12.7)

    form = carcass.get("form") or "box"
    # Layout-driven shell sizing: divider setback from the open child, groove depth from back.
    setback = None
    for _c in (ir.get("layout") or {}).get("children") or []:
        if (_c or {}).get("kind") == "open" and (_c or {}).get("setback") is not None:
            setback = float(_c["setback"])
    back_groove = float((carcass.get("back") or {}).get("groove") or 0.0)
    children: list[Any] = []
    parts: list[Any] = []
    features: dict[str, int] = {"drawer": 0, "door": 0, "leg": 0, "shelf": 0, "end_block": 0, "open_cubby": 0}

    if form == "swept_shell":
        shell = swept_shell(
            W=W,
            H=H,
            D=D,
            wall=wall,
            lean_deg=lean_deg,
            sweep_r=sweep_r,
            under_z=under_z,
            back_t=back_t,
            open_front=bool(carcass.get("open_front", True)),
            front_setback=setback,
            back_groove=back_groove,
            material=mat,
        )
        children.append(shell["assembly"])
        parts.extend(shell["parts"])
        for k, v in (shell.get("features") or {}).items():
            features[k] = features.get(k, 0) + int(v)
        meta_shell = shell["meta"]
        div_z = float(meta_shell.get("div_z") or (under_z + wall + 80))
        case_h = float(meta_shell.get("case_h") or (H - under_z))
        void_h = float(meta_shell.get("void_h") or (case_h - 2 * wall))
    else:
        raise ValueError("geometry_failed: only swept_shell implemented for v2 in P1")

    # Layout: drawer bank under open cubby
    layout = ir.get("layout") or {}
    for child in layout.get("children") or []:
        kind = (child or {}).get("kind")
        if kind == "drawer_bank":
            cols = int((child or {}).get("cols") or 2)
            features["drawer"] += cols
            front = (child or {}).get("front") or {}
            ft = float(front.get("t") or 19.05)
            bay_w = (W - 2 * wall) / cols
            drawer_h = max(40.0, (div_z - under_z - wall) * 0.85)
            for i in range(cols):
                cx = -W / 2 + wall + bay_w * (i + 0.5)
                z = under_z + wall + drawer_h / 2 + 8
                box = drawer_box(W=bay_w * 0.9, D=D * 0.82, H=drawer_h * 0.75, material=hidden, front_applied=True)
                children.append(Pos(cx, 0, z) * box["assembly"])
                if i == 0:
                    for p in box["parts"]:
                        p.qty = p.qty * cols
                        # map to hand-list-ish ids
                        if p.id == "drawer_side":
                            p.id = "DS1"
                        elif p.id == "drawer_fb":
                            p.id = "DB1"
                        elif p.id == "drawer_bottom":
                            p.id = "DBT1"
                        parts.append(p)
                fr = drawer_front(W=bay_w * 0.94, H=drawer_h * 0.9, t=ft, material=mat)
                fr["parts"][0].id = "DF1"
                fr["parts"][0].name = "Drawer front"
                children.append(Pos(cx, D / 2 - ft / 2, z) * fr["solid"])
                if i == 0:
                    fr["parts"][0].qty = cols
                    parts.append(fr["parts"][0])
        elif kind == "open":
            features["open_cubby"] = max(features.get("open_cubby", 0), 1)

    # Legs
    legs_spec = ir.get("legs") or {}
    if legs_spec:
        leg_h = float(under_z)  # legs reach underside
        # Hand list envelope length ~520 includes tenon; use under_z as visible height
        height = max(50.0, leg_h)
        legs = leg_set_flared(
            count=int(legs_spec.get("count") or 4),
            height=height,
            top=list(legs_spec.get("top") or [76.2, 50.8]),
            foot=list(legs_spec.get("foot") or [28.0, 25.4]),
            flare_r=list(legs_spec.get("flare_r") or [25.4, 50.8, 25.4]),
            material=mat,
        )
        features["leg"] = int(legs_spec.get("count") or 4)
        inset = legs_spec.get("inset") or [45, 40]
        ix, iy = float(inset[0]), float(inset[1])
        lx = float((legs_spec.get("top") or [76.2, 50.8])[0])
        ly = float((legs_spec.get("top") or [76.2, 50.8])[1])
        # Lofted leg already spans z=0..height (not centered) — place on the floor
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            children.append(
                Pos(sx * (W / 2 - ix - lx / 2), sy * (D / 2 - iy - ly / 2), 0) * legs["solid"]
            )
        parts.extend(legs["parts"])

    # Joinery / secondary blanks from hand plan (sized; not fully posed)
    parts.extend(
        [
            part("LT", Box(9.525, 25.4, 279.4), material="hard_maple", qty=2, name="Loose tongue"),
            part("W1", Box(4.7625, 15.875, 63.5), material="hardwood", qty=8, name="Wedge (kusabi)"),
            part("R1", Box(9.525, 19.05, 266.7), material="hard_maple", qty=4, name="Drawer runner"),
        ]
    )

    assembly = Compound(children=children)
    cut_v2 = lists_with_allowances(parts)
    return {
        "assembly": assembly,
        "parts": parts,
        "cut_list_v2": cut_v2,
        "features": features,
        "meta": {
            "compiler": "furniture_ir.v2",
            "W": W,
            "D": D,
            "H": H,
            "form": form,
            "under_z": under_z,
        },
        "ir": ir,
        "report": {"ok": True, "ir_hash": ir_hash(ir), "validate": check},
    }


def compile_ir(ir: dict[str, Any] | Path | str) -> dict[str, Any]:
    data = load_ir(ir)
    schema = data.get("schema")
    if schema == "furniture_ir.v2":
        return _compile_v2(data)
    if schema != "furniture_ir.v1":
        raise ValueError(f"expected furniture_ir.v1 or v2, got {schema!r}")
    root = data.get("root") or {}
    rtype = root.get("type") or "casegood"
    if rtype == "casegood":
        return _compile_casegood_v1(data)
    raise ValueError(f"IR root.type {rtype!r} not supported yet")
