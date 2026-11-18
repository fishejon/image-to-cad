"""Compile furniture_ir.v1/v2 → build123d assembly + derived parts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from build123d import Box, Compound, Pos

from furniture_cad.construct.blocks import divider as divider_block
from furniture_cad.construct.blocks import door as door_block
from furniture_cad.construct.blocks import drawer_box, drawer_front, leg_set, top_panel
from furniture_cad.construct.blocks.casegood import fixed_shelf
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


def _compile_bookcase_frame(ir: dict[str, Any], *, check: dict[str, Any]) -> dict[str, Any]:
    """Rectilinear bookcase: 4 stiles, N shelves, mid inset cabinet with doors."""
    params = ir.get("params") or {}
    mat = (ir.get("material") or {}).get("default") or "walnut"
    W = _p(params, "W", 1200.0)
    H = _p(params, "H", 2000.0)
    D = _p(params, "D", 380.0)
    attrs = ir.get("attrs") or {}
    layout = ir.get("layout") or {}
    node = next(
        (c for c in (layout.get("children") or []) if (c or {}).get("kind") == "bookcase"),
        {},
    )
    stile_t = float(node.get("stile_t") or 52.0)
    stile_w = float(node.get("stile_w") or 46.0)
    shelf_t = float(node.get("shelf_t") or 34.0)
    shelf_zs = list(node.get("shelf_z_mm") or attrs.get("shelf_z_mm") or [])
    n_shelf = int(node.get("shelf_count") or max(len(shelf_zs), 5))
    if not shelf_zs:
        # Evenly space shelves from near floor to near top
        shelf_zs = [H * (i + 1) / (n_shelf + 1) for i in range(n_shelf)]
    while len(shelf_zs) < n_shelf:
        shelf_zs.append(H * (len(shelf_zs) + 1) / (n_shelf + 1))
    cab_z0 = float(node.get("cabinet_z0_mm") or attrs.get("cabinet_z0_mm") or H * 0.25)
    cab_z1 = float(node.get("cabinet_z1_mm") or attrs.get("cabinet_z1_mm") or H * 0.42)
    door_n = max(1, int((node.get("door") or {}).get("leaf_count") or node.get("doors") or 2))

    children: list[Any] = []
    parts: list[Any] = []
    features: dict[str, int] = {"drawer": 0, "door": 0, "leg": 4, "shelf": 0, "end_block": 0, "open_cubby": 0}

    stile = Box(stile_t, stile_w, H)
    parts.append(part("ST1", stile, material=mat, qty=4, name="Stile", make="shaped", blank_pad_mm=6.0))
    inset_x = W / 2 - stile_t / 2
    inset_y = D / 2 - stile_w / 2
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        children.append(Pos(sx * inset_x, sy * inset_y, H / 2) * stile)

    shelf_len = max(40.0, W - 2 * stile_t + 20.0)  # tenon projection allowance
    shelf_d = max(40.0, D - 4.0)
    sh_solid = Box(shelf_len, shelf_d, shelf_t)
    parts.append(part("SH1", sh_solid, material=mat, qty=n_shelf, name="Shelf with integral tenons"))
    for z in shelf_zs[:n_shelf]:
        children.append(Pos(0, 0, float(z)) * sh_solid)
    features["shelf"] = n_shelf
    features["open_cubby"] = max(1, n_shelf - 1)

    # Mid cabinet box between stiles
    cab_h = max(40.0, cab_z1 - cab_z0)
    cab_w = max(40.0, W - 2 * stile_t - 10.0)
    cab_d = max(40.0, D - stile_w - 10.0)
    panel_t = 18.0
    gable = Box(panel_t, cab_d, cab_h)
    parts.append(part("CG1", gable, material=mat, qty=2, name="Cabinet gable"))
    children.append(Pos(-cab_w / 2 + panel_t / 2, 0, (cab_z0 + cab_z1) / 2) * gable)
    children.append(Pos(cab_w / 2 - panel_t / 2, 0, (cab_z0 + cab_z1) / 2) * gable)
    bottom = Box(cab_w, cab_d, panel_t)
    top = Box(cab_w, cab_d, panel_t)
    parts.append(part("CB1", bottom, material=mat, qty=1, name="Cabinet bottom"))
    parts.append(part("CT1", top, material=mat, qty=1, name="Cabinet top"))
    children.append(Pos(0, 0, cab_z0 + panel_t / 2) * bottom)
    children.append(Pos(0, 0, cab_z1 - panel_t / 2) * top)
    back = Box(cab_w - 12.0, panel_t, cab_h - 12.0)
    parts.append(part("BK1", back, material=mat, qty=1, make="sheet", name="Cabinet back panel"))
    children.append(Pos(0, -cab_d / 2 + panel_t / 2, (cab_z0 + cab_z1) / 2) * back)

    door_w = max(40.0, (cab_w - 3 * 3.0) / door_n)
    door_h = max(40.0, cab_h - 2 * 3.0)
    d = door_block(W=door_w, H=door_h, t=panel_t, style="hinged", material=mat)
    d["parts"][0].qty = door_n
    parts.append(d["parts"][0])
    for i in range(door_n):
        cx = -cab_w / 2 + 3.0 + door_w * (i + 0.5) + i * 3.0
        children.append(Pos(cx, cab_d / 2 - panel_t / 2, (cab_z0 + cab_z1) / 2) * d["solid"])
    features["door"] = door_n

    assembly = Compound(children=children)
    cut_v2 = lists_with_allowances(parts)
    return {
        "assembly": assembly,
        "parts": parts,
        "cut_list_v2": cut_v2,
        "features": features,
        "meta": {"compiler": "furniture_ir.v2", "form": "bookcase_frame", "W": W, "D": D, "H": H},
        "ir": ir,
        "report": {"ok": True, "ir_hash": ir_hash(ir), "validate": check},
    }


def _compile_frame_nightstand(ir: dict[str, Any], *, check: dict[str, Any]) -> dict[str, Any]:
    """Nightstand frame: full-height legs, top, aprons, lower shelf, one drawer + optional SR1."""
    params = ir.get("params") or {}
    mat = (ir.get("material") or {}).get("default") or "cherry"
    hidden = (ir.get("material") or {}).get("hidden") or "poplar"
    W = _p(params, "W", 584.2)
    H = _p(params, "H", 584.2)
    D = _p(params, "D", 457.2)
    carcass = ir.get("carcass") or {}
    top_t = float((carcass.get("top") or {}).get("t") or 25.4)
    wall = float((carcass.get("outline") or {}).get("wall") or params.get("wall") or 18.0)
    under_z = float((carcass.get("outline") or {}).get("under_z") or params.get("under_z") or H * 0.55)
    legs_spec = ir.get("legs") or {}
    leg_xy = float((legs_spec.get("top") or [30.0, 30.0])[0])
    leg_h = max(50.0, H - top_t)

    children: list[Any] = []
    parts: list[Any] = []
    features: dict[str, int] = {"drawer": 0, "door": 0, "leg": 4, "shelf": 0, "end_block": 0, "open_cubby": 0}

    legs = leg_set(
        count=int(legs_spec.get("count") or 4),
        height=leg_h,
        top=[leg_xy, leg_xy],
        foot=[leg_xy, leg_xy],
        material=mat,
    )
    for p in legs["parts"]:
        p.id = "L1"
        p.name = "Leg"
    parts.extend(legs["parts"])
    half_span_x = (W - leg_xy) / 2
    half_span_y = (D - leg_xy) / 2
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        children.append(Pos(sx * half_span_x, sy * half_span_y, leg_h / 2) * legs["solid"])

    top = Box(W, D, top_t)
    parts.append(part("T1", top, material=mat, qty=1, name="Top panel"))
    children.append(Pos(0, 0, H - top_t / 2) * top)

    # Three aprons (front lower, rear lower, rear upper)
    apron_t = 18.0
    apron_len = max(40.0, W - 2 * leg_xy + 10.0)
    apron_solid = Box(apron_len, apron_t, apron_t)
    parts.append(part("A1", apron_solid, material=mat, qty=3, name="Apron / cross rail"))
    z_low = under_z
    z_up = H - top_t - 40.0
    children.append(Pos(0, D / 2 - leg_xy / 2 - apron_t / 2, z_low) * apron_solid)
    children.append(Pos(0, -D / 2 + leg_xy / 2 + apron_t / 2, z_low) * apron_solid)
    children.append(Pos(0, -D / 2 + leg_xy / 2 + apron_t / 2, z_up) * apron_solid)

    # Lower shelf
    sh_w = max(40.0, W - 2 * leg_xy)
    sh_d = max(40.0, D - 2 * leg_xy)
    sh = fixed_shelf(W=sh_w, D=sh_d, t=wall, material=mat)
    children.append(Pos(0, 0, under_z) * sh["solid"])
    parts.append(sh["parts"][0])
    features["shelf"] = 1
    features["open_cubby"] = 1

    # Single top drawer
    layout = ir.get("layout") or {}
    bank = None
    for c in layout.get("children") or []:
        if (c or {}).get("kind") == "bay":
            for s in c.get("stack") or []:
                if (s or {}).get("kind") == "drawer_bank":
                    bank = s
                    break
        elif (c or {}).get("kind") == "drawer_bank":
            bank = c
    front = (bank or {}).get("front") or {}
    ft = float(front.get("t") or 19.0)
    reveal = float(front.get("reveal") or 1.5)
    bank_frac = float((bank or {}).get("bank_frac") or 0.25)
    case_clear = max(60.0, H - top_t - under_z)
    front_h = max(40.0, bank_frac * case_clear - 2 * reveal)
    if bank_frac and case_clear:
        front_h = max(40.0, (bank_frac * (H - top_t) - 2 * reveal))
    front_w = max(40.0, W - 2 * leg_xy - 2 * reveal)
    box_d = max(60.0, D - 2 * leg_xy - ft - 10.0)
    box_h = max(25.0, front_h - 20.0)
    box_w = max(40.0, front_w - 2 * 12.7)
    z_drawer = H - top_t - reveal - front_h / 2
    box = drawer_box(W=box_w, D=box_d, H=box_h, material=hidden, front_applied=True)
    children.append(Pos(0, 0, z_drawer) * box["assembly"])
    for p in box["parts"]:
        if p.id == "drawer_side":
            p.id = "DS1"
        elif p.id == "drawer_fb":
            p.id = "DB1"
        elif p.id == "drawer_bottom":
            p.id = "DBT1"
        parts.append(p)
    fr = drawer_front(W=front_w, H=front_h, t=ft, material=mat)
    fr["parts"][0].id = "DF1"
    fr["parts"][0].name = "Drawer front"
    parts.append(fr["parts"][0])
    children.append(Pos(0, D / 2 - leg_xy / 2 - ft / 2, z_drawer) * fr["solid"])
    features["drawer"] = 1

    # Optional slide-rail blanks from IR joinery
    for blank in ((ir.get("joinery") or {}).get("blanks") or []):
        bid = str(blank.get("id") or "blank")
        parts.append(
            part(
                bid,
                Box(float(blank["thickness_mm"]), float(blank["width_mm"]), float(blank["length_mm"])),
                material=str(blank.get("material") or mat),
                qty=int(blank.get("qty") or 1),
                name=str(blank.get("name") or bid),
                make="shaped",
                blank_pad_mm=2.0,
            )
        )

    assembly = Compound(children=children)
    cut_v2 = lists_with_allowances(parts)
    return {
        "assembly": assembly,
        "parts": parts,
        "cut_list_v2": cut_v2,
        "features": features,
        "meta": {"compiler": "furniture_ir.v2", "form": "frame_nightstand", "W": W, "D": D, "H": H},
        "ir": ir,
        "report": {"ok": True, "ir_hash": ir_hash(ir), "validate": check},
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

    def _first(*vals: Any, default: float) -> float:
        # 0 is a real value (straight ends, square corners), not "missing"
        return float(next((v for v in vals if v is not None), default))

    lean_deg = _first(outline.get("lean_deg"), params.get("lean_deg"), default=6.0)
    sweep_r = _first(outline.get("sweep_r"), params.get("sweep_r"), default=121.92)
    back_t = float(params.get("back_t") or (carcass.get("back") or {}).get("t") or 12.7)

    form = carcass.get("form") or "box"
    layout = ir.get("layout") or {}
    layout_children = list(layout.get("children") or [])
    bay_based = any((c or {}).get("kind") in ("bay", "divider") for c in layout_children)
    bookcase_node = next((c for c in layout_children if (c or {}).get("kind") == "bookcase"), None)

    def _walk_setback(nodes: list[Any]) -> float | None:
        found = None
        for _c in nodes:
            kind = (_c or {}).get("kind")
            if kind == "open" and (_c or {}).get("setback") is not None:
                found = float(_c["setback"])
            if kind == "bay":
                nested = _walk_setback(list((_c or {}).get("stack") or []))
                if nested is not None:
                    found = nested
        return found

    def _walk_bank_frac(nodes: list[Any]) -> float | None:
        found = None
        for _c in nodes:
            kind = (_c or {}).get("kind")
            if kind == "drawer_bank" and (_c or {}).get("bank_frac") is not None:
                found = float(_c["bank_frac"])
            if kind == "bay":
                nested = _walk_bank_frac(list((_c or {}).get("stack") or []))
                if nested is not None:
                    found = nested
        return found

    setback = _walk_setback(layout_children)
    back_groove = float((carcass.get("back") or {}).get("groove") or 0.0)
    bank_frac = _walk_bank_frac(layout_children)
    bank_open_h = None if bank_frac is None else float(bank_frac) * max(40.0, H - under_z)
    top_t = float((carcass.get("top") or {}).get("t") or wall)
    top_oh = list((carcass.get("top") or {}).get("overhang") or [0.0, 0.0, 0.0])
    end_profile = (carcass.get("end_profile") or {}).get("kind") or ""
    end_bottom_r = float((carcass.get("end_profile") or {}).get("r") or 0.0)
    children: list[Any] = []
    parts: list[Any] = []
    features: dict[str, int] = {"drawer": 0, "door": 0, "leg": 0, "shelf": 0, "end_block": 0, "open_cubby": 0}

    if form == "bookcase_frame" or bookcase_node is not None:
        return _compile_bookcase_frame(ir, check=check)

    if form == "frame_nightstand":
        return _compile_frame_nightstand(ir, check=check)

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
            bank_open_h=bank_open_h,
            material=mat,
            top_t=top_t,
            include_horizontal_divider=not bay_based,
            end_bottom_r=end_bottom_r if "round" in str(end_profile) else 0.0,
            overhang=top_oh,
        )
        children.append(shell["assembly"])
        parts.extend(shell["parts"])
        for k, v in (shell.get("features") or {}).items():
            features[k] = features.get(k, 0) + int(v)
        meta_shell = shell["meta"]
        div_z = float(meta_shell.get("div_z") or (under_z + wall + 80))
        case_h = float(meta_shell.get("case_h") or (H - under_z))
        void_h = float(meta_shell.get("void_h") or (case_h - 2 * wall))
        Wc = float(meta_shell.get("Wc") or W)
        Dc = float(meta_shell.get("Dc") or D)
        cy = float(meta_shell.get("cy") or 0.0)
    else:
        raise ValueError("geometry_failed: unsupported carcass.form for v2")

    z_int = under_z + wall
    z_top = under_z + case_h - float(meta_shell.get("top_t") or top_t)
    clear_h = max(10.0, z_top - z_int)

    def _merge_part(plist: list[Any], new_p: Any) -> None:
        for existing in plist:
            if existing.id == new_p.id:
                existing.qty = int(existing.qty) + int(new_p.qty)
                return
        plist.append(new_p)

    def _place_drawer_bank(
        child: dict[str, Any],
        *,
        x0: float,
        x1: float,
        z0: float,
        z1: float,
    ) -> None:
        cols = max(1, int(child.get("cols") or 1))
        rows = max(1, int(child.get("rows") or 1))
        features["drawer"] += cols * rows
        front = child.get("front") or {}
        ft = float(front.get("t") or 19.05)
        reveal = float(front.get("reveal") or 1.6)
        align = str(child.get("align") or "fill")
        bay_w = max(20.0, x1 - x0)
        col_w = bay_w / cols
        # Box depth: interior depth minus front thickness and slide/back clearance
        box_d = max(60.0, Dc - ft - max(back_t, 3.175) - 3.175)
        slide_gap = 12.7  # per-side clearance for side-mount slides
        span_avail = max(20.0, z1 - z0)
        if child.get("bank_frac") is not None:
            span = max(20.0, min(float(child["bank_frac"]) * case_h, span_avail))
        elif bank_open_h is not None and not bay_based:
            span = max(20.0, min(bank_open_h, span_avail))
        else:
            span = span_avail * (0.92 if rows > 1 else 0.85)
        # Per-row front height from the bank span
        front_h = max(30.0, (span - (rows + 1) * reveal) / rows)
        box_h = max(25.0, front_h - 25.4)
        if align == "top":
            bank_top = z1
            bank_bot = bank_top - span
        elif align == "bottom":
            bank_bot = z0
            bank_top = bank_bot + span
        else:
            bank_bot = z0
            bank_top = z0 + span
        n_drawers = cols * rows
        front_y = cy + Dc / 2 - ft / 2
        for r in range(rows):
            z_front0 = bank_bot + reveal + r * (front_h + reveal)
            z = z_front0 + front_h / 2
            for c in range(cols):
                cx = x0 + col_w * (c + 0.5)
                box_w = max(40.0, col_w - 2 * slide_gap)
                box = drawer_box(W=box_w, D=box_d, H=box_h, material=hidden, front_applied=True)
                children.append(Pos(cx, cy, z) * box["assembly"])
                fr = drawer_front(W=max(20.0, col_w - 2 * reveal), H=front_h, t=ft, material=mat)
                children.append(Pos(cx, front_y, z) * fr["solid"])
                if r == 0 and c == 0:
                    for p in box["parts"]:
                        p.qty = int(p.qty) * n_drawers
                        if p.id == "drawer_side":
                            p.id = "DS1"
                        elif p.id == "drawer_fb":
                            p.id = "DB1"
                        elif p.id == "drawer_bottom":
                            p.id = "DBT1"
                        parts.append(p)
                    fr["parts"][0].id = "DF1"
                    fr["parts"][0].name = "Drawer front"
                    fr["parts"][0].qty = n_drawers
                    parts.append(fr["parts"][0])

    def _place_bay_stack(stack: list[Any], *, x0: float, x1: float, count_open: bool = True) -> None:
        # Partition vertical clear height among stack items.
        items = [s for s in stack if s]
        if not items:
            return
        # Place from top when a bank is align=top, else bottom-up.
        cursor_top = z_top
        cursor_bot = z_int
        for s in items:
            kind = s.get("kind")
            if kind == "drawer_bank":
                frac = float(s["bank_frac"]) if s.get("bank_frac") is not None else (
                    0.5 if any(i.get("kind") == "open" for i in items) else 1.0
                )
                span = max(20.0, min(clear_h * frac, clear_h - 10.0))
                align = str(s.get("align") or "fill")
                if align == "top":
                    _place_drawer_bank(s, x0=x0, x1=x1, z0=cursor_top - span, z1=cursor_top)
                    cursor_top -= span
                else:
                    _place_drawer_bank(s, x0=x0, x1=x1, z0=cursor_bot, z1=cursor_bot + span)
                    cursor_bot += span
            elif kind == "shelf":
                setback_s = float(s.get("setback") or wall)
                sh_d = max(20.0, Dc - back_t - setback_s)
                sh_w = max(20.0, x1 - x0 - 2.0)
                sh = fixed_shelf(W=sh_w, D=sh_d, t=wall, material=mat)
                # Mid of remaining clear (or bottom-aligned)
                if str(s.get("align") or "") == "bottom":
                    z_s = cursor_bot + wall / 2
                    cursor_bot += wall
                else:
                    z_s = (cursor_bot + cursor_top) / 2
                children.append(Pos((x0 + x1) / 2, cy - Dc / 2 + back_t + sh_d / 2, z_s) * sh["solid"])
                _merge_part(parts, sh["parts"][0])
                features["shelf"] = features.get("shelf", 0) + 1
            elif kind == "open" and count_open:
                features["open_cubby"] = features.get("open_cubby", 0) + 1

    def _place_door_on_bay(door_spec: dict[str, Any], *, x0: float, x1: float) -> None:
        leaf_n = max(1, int(door_spec.get("leaf_count") or 1))
        ft = float(door_spec.get("t") or 19.0)
        reveal = float(door_spec.get("reveal") or 3.0)
        style = str(door_spec.get("type") or "hinged")
        door_h = max(40.0, clear_h - 2 * reveal)
        door_w = max(40.0, (x1 - x0 - (leaf_n + 1) * reveal) / leaf_n)
        # Sliding leaves can be wider than the bay (overlap the divider).
        if style == "sliding":
            door_w = max(door_w, (x1 - x0) * 1.05)
        z = z_int + reveal + door_h / 2
        door_y = cy + Dc / 2 - ft / 2
        for i in range(leaf_n):
            cx = x0 + reveal + door_w * (i + 0.5) + i * reveal
            # Keep door inside carcass width
            cx = max(-Wc / 2 + wall + door_w / 2, min(Wc / 2 - wall - door_w / 2, cx))
            d = door_block(W=door_w, H=door_h, t=ft, style=style, material=mat)
            children.append(Pos(cx, door_y, z) * d["solid"])
            if i == 0:
                d["parts"][0].qty = leaf_n
                _merge_part(parts, d["parts"][0])
        features["door"] = features.get("door", 0) + leaf_n

    # Layout: bay-based (multi-bay) or flat console children
    if bay_based:
        int_w = max(20.0, Wc - 2 * wall)
        div_ts = [float((c or {}).get("t") or wall) for c in layout_children if (c or {}).get("kind") == "divider"]
        rem = max(20.0, int_w - sum(div_ts))
        bay_nodes = [c for c in layout_children if (c or {}).get("kind") == "bay"]
        # Prefer explicit w_mm; else distribute by w_frac; else equal flex
        frac_sum = sum(float(b.get("w_frac") or 0.0) for b in bay_nodes)
        explicit = [float(b["w_mm"]) for b in bay_nodes if b.get("w_mm") is not None]
        n_flex = len(bay_nodes) - len(explicit)
        flex_w = max(20.0, (rem - sum(explicit)) / max(1, n_flex))

        def _bay_width(b: dict[str, Any]) -> float:
            if b.get("w_mm") is not None:
                return float(b["w_mm"])
            if frac_sum > 0 and b.get("w_frac") is not None:
                return max(20.0, rem * float(b["w_frac"]) / frac_sum)
            return flex_w

        x_cursor = -Wc / 2 + wall
        for child in layout_children:
            kind = (child or {}).get("kind")
            if kind == "divider":
                t = float((child or {}).get("t") or wall)
                div_h = clear_h
                div_d = max(20.0, Dc - back_t)
                d = divider_block(width=div_d, height=div_h, thickness=t, material=mat)
                children.append(
                    Pos(x_cursor + t / 2, cy - Dc / 2 + back_t + div_d / 2, z_int + div_h / 2) * d["solid"]
                )
                _merge_part(parts, d["parts"][0])
                x_cursor += t
            elif kind == "bay":
                bw = _bay_width(child)
                x0, x1 = x_cursor, x_cursor + bw
                has_door = bool(child.get("door"))
                if has_door:
                    _place_door_on_bay(child["door"], x0=x0, x1=x1)
                # Door bays are closed voids, not open cubbies.
                _place_bay_stack(list(child.get("stack") or []), x0=x0, x1=x1, count_open=not has_door)
                x_cursor = x1
    else:
        for child in layout_children:
            kind = (child or {}).get("kind")
            if kind == "drawer_bank":
                # Legacy: full interior width, bottom of case
                x0, x1 = -Wc / 2 + wall, Wc / 2 - wall
                # Prefer measured bank height against the shell divider
                z1 = div_z - wall / 2 if bank_open_h is not None else z_int + (div_z - under_z - wall) * 0.85
                _place_drawer_bank(child, x0=x0, x1=x1, z0=z_int, z1=max(z_int + 40.0, z1))
            elif kind == "open":
                features["open_cubby"] = max(features.get("open_cubby", 0), 1)

    # Legs
    legs_spec = ir.get("legs") or {}
    if legs_spec:
        height_mode = str(legs_spec.get("height_mode") or "")
        if height_mode == "full_minus_top":
            height = max(50.0, H - top_t)
        else:
            height = max(50.0, float(under_z))
        style = str(legs_spec.get("style") or "")
        if "flared" in style or "two_profile" in style:
            legs = leg_set_flared(
                count=int(legs_spec.get("count") or 4),
                height=height,
                top=list(legs_spec.get("top") or [76.2, 50.8]),
                foot=list(legs_spec.get("foot") or [28.0, 25.4]),
                flare_r=list(legs_spec.get("flare_r") or [25.4, 50.8, 25.4]),
                material=mat,
            )
        else:
            legs = leg_set(
                count=int(legs_spec.get("count") or 4),
                height=height,
                top=list(legs_spec.get("top") or [38.0, 38.0]),
                foot=list(legs_spec.get("foot") or [38.0, 38.0]),
                splay_deg=float(legs_spec.get("splay_deg") or 0.0),
                material=mat,
            )
            # Remap generic leg id → L1 for hand-list matching
            for p in legs["parts"]:
                p.id = "L1"
                p.name = "Leg, tapered" if "taper" in style else "Leg"
        features["leg"] = int(legs_spec.get("count") or 4)
        inset = legs_spec.get("inset") or [45, 40]
        ix, iy = float(inset[0]), float(inset[1])
        lx = float((legs_spec.get("top") or [76.2, 50.8])[0])
        ly = float((legs_spec.get("top") or [76.2, 50.8])[1])
        # Place relative to carcass footprint when overhang shrinks the case
        half_w, half_d = Wc / 2, Dc / 2
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            children.append(
                Pos(sx * (half_w - ix - lx / 2), cy + sy * (half_d - iy - ly / 2), 0) * legs["solid"]
            )
        parts.extend(legs["parts"])

    # Optional joinery blanks (golden / hand IR only — not invented by generic Construct)
    for blank in ((ir.get("joinery") or {}).get("blanks") or []):
        bid = str(blank.get("id") or "blank")
        t = float(blank["thickness_mm"])
        w = float(blank["width_mm"])
        L = float(blank["length_mm"])
        qty = int(blank.get("qty") or 1)
        parts.append(
            part(
                bid,
                Box(t, w, L),
                material=str(blank.get("material") or mat),
                qty=qty,
                name=str(blank.get("name") or bid),
            )
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
            "bay_based": bay_based,
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
