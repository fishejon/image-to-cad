"""Compile furniture_ir.v1 → build123d assembly + derived parts (Phase 0/1 stub)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from build123d import Box, Compound, Pos

from furniture_cad.derive import part


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

    # Carcass box above legs
    case_h = max(50.0, H - leg_h)
    side = Box(t, D, case_h)
    top = Box(W, D, t)
    bottom = Box(W, D, t)
    back_t = 6.0
    back = Box(W - 2 * t, back_t, case_h - 2 * t)

    children: list[Any] = [
        Pos(-W / 2 + t / 2, 0, leg_h + case_h / 2) * side,
        Pos(W / 2 - t / 2, 0, leg_h + case_h / 2) * side,
        Pos(0, 0, H - t / 2) * top,
        Pos(0, 0, leg_h + t / 2) * bottom,
        Pos(0, -D / 2 + back_t / 2, leg_h + case_h / 2) * back,
    ]

    div_t = float((root.get("divider") or {}).get("t") or t) if root.get("divider") else 0.0
    if root.get("divider"):
        children.append(Pos(0, 0, leg_h + case_h / 2) * Box(div_t, D - back_t - 4, case_h - 2 * t))

    # Legs
    legs_spec = root.get("legs") or {}
    leg_top = legs_spec.get("top") or [38, 38]
    lx, ly = float(leg_top[0]), float(leg_top[1])
    inset = legs_spec.get("inset") or [45, 45]
    ix, iy = float(inset[0]), float(inset[1])
    leg = Box(lx, ly, leg_h)
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        children.append(
            Pos(sx * (W / 2 - ix - lx / 2), sy * (D / 2 - iy - ly / 2), leg_h / 2) * leg
        )

    # Drawer bank / open bay volumes as placeholder boxes (visual mass for silhouette)
    bays = root.get("bays") or []
    n_bays = max(1, len(bays))
    bay_w = (W - 2 * t - div_t) / n_bays
    x0 = -W / 2 + t
    for i, bay in enumerate(bays):
        kind = (bay or {}).get("kind") or "open"
        cx = x0 + bay_w * (i + 0.5) + (div_t / 2 if div_t and i >= 1 else 0)
        if kind == "drawer_bank":
            n = int((bay or {}).get("n") or 2)
            dh = (case_h - 2 * t) / n
            for j in range(n):
                children.append(
                    Pos(cx, D / 2 - t, leg_h + t + dh * (j + 0.5)) * Box(bay_w * 0.92, t, dh * 0.85)
                )
        # open bay: leave void (no fill)

    assembly = Compound(children=children)
    parts = [
        part("side", side, material=mat, qty=2, name="Side"),
        part("top", top, material=mat, qty=1, name="Top"),
        part("bottom", bottom, material=mat, qty=1, name="Bottom"),
        part("back", back, material="ply", qty=1, make="sheet", name="Back"),
        part("leg", leg, material=mat, qty=4, name="Leg", make="shaped"),
    ]
    if root.get("divider"):
        parts.append(
            part("divider", Box(div_t, D - back_t - 4, case_h - 2 * t), material=mat, qty=1, name="Divider")
        )
    return {
        "assembly": assembly,
        "parts": parts,
        "meta": {"compiler": "furniture_ir.v1.stub", "W": W, "D": D, "H": H, "type": "casegood"},
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
    raise ValueError(f"IR root.type {rtype!r} not supported yet (Phase 0/1: casegood only)")
