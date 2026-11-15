#!/usr/bin/env python3
"""Generate the SYNTHETIC sideboard_01 ground truth.

This is a designed piece, not a measured one: nobody built it and there is no real photo.
It exists to test whether the pipeline generalises beyond the console (straight sides, short
tapered legs, three STACKED drawers between two doors). It uses only build123d, never the
furniture_cad compile code, so the answer key is not produced by the code under test.

Usage (from the repo root):
    python evals/photos/cases/sideboard_01/make_synthetic_gt.py

Writes next to this file: sideboard_01.step, cut_list.hand.json, known_sizes.json,
features.json, proportions.json, views.json, README.md and a front render PNG (gitignored).
All sizes are millimetres. X is centred, Y runs back (0) to front (D), Z runs floor to top.
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

from build123d import Box, BuildPart, BuildSketch, Compound, Location, Locations, Plane, Rectangle, export_step, loft

HERE = Path(__file__).resolve().parent
IN = 25.4

# ---- design (inches in the comments) ---------------------------------------------------------
W, D, H = 1524.0, 457.2, 812.8  # 60 x 18 x 32
LEG_H = 177.8  # 7
TOP_T = 25.4  # 1
WALL = 19.05  # 3/4
BACK_T = 6.35  # 1/4
REVEAL = 3.175  # 1/8
OVERHANG = 19.05  # top overhangs the carcass at both ends and the front; back is flush
BANK_W = 482.6  # 19 clear width of the drawer bank
SLIDE_GAP = 12.7  # per side, side-mount slides
DRAWER_SIDE_T = 12.7
DRAWER_BOTTOM_T = 6.35

WC = W - 2 * OVERHANG  # carcass width
DC = D - OVERHANG  # carcass depth
HC = H - LEG_H - TOP_T  # carcass height (under the top plank)
CI = HC - WALL  # interior clear height (bottom panel to underside of the top plank)
INT_W = WC - 2 * WALL  # interior clear width
DOOR_BAY_W = (INT_W - 2 * WALL - BANK_W) / 2
DEPTH_IN = DC - BACK_T  # interior depth (front of carcass to the back panel)
FRONT_H = round((CI - 4 * REVEAL) / 3, 2)  # three stacked drawer fronts, four reveals
BOX_H = round(FRONT_H - 25.4, 2)
BOX_D = 16 * IN
BOX_W = BANK_W - 2 * SLIDE_GAP

Z0 = LEG_H  # underside of the carcass
Z_INT = Z0 + WALL  # top of the bottom panel
Z_TOP_CARCASS = Z0 + HC

STOCKS = {"walnut_4/4": 1.0, "walnut_5/4": 1.25, "walnut_8/4": 2.0, "maple_4/4": 1.0}


def box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Box:
    return Location(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)) * Box(x1 - x0, y1 - y0, z1 - z0)


def leg_solid(cx: float, cy: float):
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            Rectangle(25.4, 25.4)
        with BuildSketch(Plane.XY.offset(LEG_H)):
            Rectangle(44.45, 44.45)
        loft(ruled=True)
    return Location((cx, cy, 0)) * bp.part


def build() -> tuple[Compound, list[dict]]:
    """Return the assembled compound and one finished-size record per part type."""
    solids: list = []
    parts: list[dict] = []

    def add(pid, name, qty, t, w, l, cls, material, stock, solid_list, grain="length", sheet=False):  # noqa: E741
        solids.extend(solid_list)
        parts.append(
            {
                "id": pid,
                "name": name,
                "qty": qty,
                "t": t,
                "w": w,
                "l": l,
                "class": cls,
                "material": material,
                "stock": stock,
                "grain": grain,
                "sheet": sheet,
            }
        )

    # top plank
    add("T1", "Top plank", 1, TOP_T, D, W, "visible", "walnut", "walnut_5/4",
        [box(-W / 2, W / 2, 0, D, H - TOP_T, H)])
    # ends
    add("E1", "End panel", 2, WALL, DC, HC, "visible", "walnut", "walnut_4/4",
        [box(-WC / 2, -WC / 2 + WALL, 0, DC, Z0, Z0 + HC), box(WC / 2 - WALL, WC / 2, 0, DC, Z0, Z0 + HC)],
        grain="vertical")
    # bottom
    add("B1", "Bottom panel", 1, WALL, DEPTH_IN, INT_W, "construction", "walnut", "walnut_4/4",
        [box(-INT_W / 2, INT_W / 2, BACK_T, DC, Z0, Z0 + WALL)])
    # vertical dividers beside the drawer bank
    xd = BANK_W / 2
    add("V1", "Vertical divider", 2, WALL, DEPTH_IN, CI, "construction", "walnut", "walnut_4/4",
        [box(-xd - WALL, -xd, BACK_T, DC, Z_INT, Z_TOP_CARCASS), box(xd, xd + WALL, BACK_T, DC, Z_INT, Z_TOP_CARCASS)],
        grain="vertical")
    # back (sheet, floating)
    add("BK1", "Back panel", 1, BACK_T, CI, INT_W, "construction", "birch_ply", "ply_1/4", 
        [box(-INT_W / 2, INT_W / 2, 0, BACK_T, Z_INT, Z_TOP_CARCASS)], sheet=True)
    # fixed shelves, one per door bay, set back for the door
    sh_depth = DEPTH_IN - WALL
    zs = Z_INT + CI / 2
    xl0, xl1 = -INT_W / 2, -xd - WALL
    xr0, xr1 = xd + WALL, INT_W / 2
    add("SH1", "Fixed shelf", 2, WALL, sh_depth, DOOR_BAY_W, "construction", "walnut", "walnut_4/4",
        [box(xl0, xl1, BACK_T, BACK_T + sh_depth, zs - WALL / 2, zs + WALL / 2),
         box(xr0, xr1, BACK_T, BACK_T + sh_depth, zs - WALL / 2, zs + WALL / 2)])
    # doors, inset flush with the carcass front
    door_w = DOOR_BAY_W - 2 * REVEAL
    door_h = CI - 2 * REVEAL
    add("DR1", "Door", 2, WALL, door_h, door_w, "visible", "walnut", "walnut_4/4",
        [box(xl0 + REVEAL, xl1 - REVEAL, DC - WALL, DC, Z_INT + REVEAL, Z_INT + REVEAL + door_h),
         box(xr0 + REVEAL, xr1 - REVEAL, DC - WALL, DC, Z_INT + REVEAL, Z_INT + REVEAL + door_h)],
        grain="vertical")
    # three stacked drawers
    fronts, sides, backs, bottoms = [], [], [], []
    fw = BANK_W - 2 * REVEAL
    for i in range(3):
        zf0 = Z_INT + REVEAL + i * (FRONT_H + REVEAL)
        zc = zf0 + FRONT_H / 2
        fronts.append(box(-fw / 2, fw / 2, DC - WALL, DC, zf0, zf0 + FRONT_H))
        y1 = DC - WALL  # box starts behind the applied front
        y0 = y1 - BOX_D
        z0b, z1b = zc - BOX_H / 2, zc + BOX_H / 2
        for sx in (-1, 1):
            xa = sx * (BOX_W / 2 - DRAWER_SIDE_T / 2)
            sides.append(box(xa - DRAWER_SIDE_T / 2, xa + DRAWER_SIDE_T / 2, y0, y1, z0b, z1b))
        backs.append(box(-(BOX_W - 2 * DRAWER_SIDE_T) / 2, (BOX_W - 2 * DRAWER_SIDE_T) / 2, y0, y0 + DRAWER_SIDE_T, z0b, z1b))
        bw = BOX_W - 2 * DRAWER_SIDE_T + 12.7
        bottoms.append(box(-bw / 2, bw / 2, y0 + 3.0, y1 - 3.0, z0b + 12.7, z0b + 12.7 + DRAWER_BOTTOM_T))
    add("DF1", "Drawer front", 3, WALL, FRONT_H, fw, "visible", "walnut", "walnut_4/4", fronts)
    add("DS1", "Drawer side", 6, DRAWER_SIDE_T, BOX_H, BOX_D, "construction", "maple", "maple_4/4", sides)
    add("DB1", "Drawer back", 3, DRAWER_SIDE_T, BOX_H, BOX_W - 2 * DRAWER_SIDE_T, "construction", "maple", "maple_4/4", backs)
    bw = BOX_W - 2 * DRAWER_SIDE_T + 12.7
    add("DBT1", "Drawer bottom", 3, DRAWER_BOTTOM_T, BOX_D - 6.0, bw, "construction", "birch_ply", "ply_1/4", bottoms, sheet=True)
    # legs
    lx = WC / 2 - 50.8 - 22.225
    ly0, ly1 = 50.8 + 22.225, DC - 50.8 - 22.225
    add("L1", "Leg, tapered", 4, 44.45, 44.45, LEG_H, "visible", "walnut", "walnut_8/4",
        [leg_solid(sx * lx, y) for sx in (-1, 1) for y in (ly0, ly1)])
    return Compound(children=solids), parts


def check(parts: list[dict], compound: Compound) -> None:
    bb = compound.bounding_box()
    assert abs(bb.size.X - W) < 0.01 and abs(bb.size.Y - D) < 0.01 and abs(bb.size.Z - H) < 0.01, bb.size
    # every part type is represented by its solids: bbox of the first solid sorted == finished sorted
    solids = list(compound.solids())
    i = 0
    for p in parts:
        n = p["qty"]
        grp = solids[i : i + n]
        i += n
        assert len(grp) == n, (p["id"], len(grp), n)
        want = sorted([p["t"], p["w"], p["l"]])
        for s in grp:
            b = s.bounding_box()
            got = sorted([b.size.X, b.size.Y, b.size.Z])
            assert all(abs(a - b2) < 0.02 for a, b2 in zip(got, want)), (p["id"], got, want)
    assert i == len(solids)


def write_files(parts: list[dict]) -> None:
    out_parts = []
    stock_t: dict[str, float] = {}
    for p in parts:
        t, w, l = p["t"], p["w"], p["l"]  # noqa: E741
        row = {
            "id": p["id"],
            "name": p["name"],
            "qty": p["qty"],
            "finished_in": {"t": round(t / IN, 4), "w": round(w / IN, 4), "l": round(l / IN, 4)},
            "thickness_mm": round(t, 3),
            "width_mm": round(w, 3),
            "length_mm": round(l, 3),
            "class": p["class"],
            "stock": p["stock"],
            "material": p["material"],
            "grain": p["grain"],
        }
        if not p["sheet"]:
            nominal = STOCKS[p["stock"]]
            blank = {"t": nominal, "w": round(w / IN + 0.25, 3), "l": round(l / IN + 0.5, 3)}
            row["blank_in"] = blank
            stock_t[p["stock"]] = stock_t.get(p["stock"], 0.0) + blank["t"] * blank["w"] * blank["l"] / 144.0 * p["qty"]
        else:
            row["sheet"] = True
        out_parts.append(row)
    stock_buy = []
    for stock, bf in sorted(stock_t.items()):
        ids = [p["id"] for p in parts if p["stock"] == stock]
        stock_buy.append({"stock": stock, "parts": ids, "net_bf": round(bf, 1), "with_25pct_bf": round(bf * 1.25, 1)})
    hand = {
        "schema": "hand_cut_list.v1",
        "id": "sideboard_01",
        "title": "Sideboard (synthetic design)",
        "date": date.today().isoformat(),
        "author": "generated by make_synthetic_gt.py (no human builder)",
        "synthetic": True,
        "dims_in": {"w": W / IN, "d": D / IN, "h": H / IN},
        "dims_mm": {"w": W, "d": D, "h": H},
        "dims_from": "design script",
        "status": "synthetic_design",
        "units_source": "inches",
        "notes": [
            "SYNTHETIC: designed to stress the pipeline on a different form, not built or measured.",
            "Straight 3/4 in ends, 7 in tapered legs, top overhangs sides and front by 3/4 in.",
            "Three stacked drawers between two doors, inset flush; 1/8 in reveals.",
            "Blank thickness is the nominal stock thickness; sheet goods carry no blank.",
        ],
        "parts": out_parts,
        "stock_buy": stock_buy,
        "joinery": [
            {"joint": "ends to bottom, dividers to bottom", "method": "dado 1/4 deep"},
            {"joint": "back panel", "method": "floating in grooves"},
            {"joint": "top to carcass", "method": "figure-8 fasteners (slotted)"},
            {"joint": "legs to carcass", "method": "corner blocks, screws"},
        ],
    }
    (HERE / "cut_list.hand.json").write_text(json.dumps(hand, indent=2) + "\n")
    (HERE / "known_sizes.json").write_text(
        json.dumps(
            {
                "schema": "known_sizes.v1",
                "id": "sideboard_01",
                "units": "mm",
                "overall": {
                    "w": {"v": W, "src": "design", "in": W / IN},
                    "d": {"v": D, "src": "design", "in": D / IN},
                    "h": {"v": H, "src": "design", "in": H / IN},
                },
                "anchor": "w",
                "notes": "Synthetic design sizes.",
            },
            indent=2,
        )
        + "\n"
    )
    (HERE / "features.json").write_text(
        json.dumps(
            {
                "schema": "features.v1",
                "id": "sideboard_01",
                "counts": {"drawer": 3, "door": 2, "shelf": 2, "leg": 4, "open_cubby": 0, "pull": 0},
                "attrs": {"end_form": "flat", "leg_style": "tapered", "drawer_layout": "stacked_center"},
                "notes": "Counts read off the design.",
            },
            indent=2,
        )
        + "\n"
    )
    case_h = H - LEG_H
    span = 3 * FRONT_H + 2 * REVEAL
    (HERE / "proportions.json").write_text(
        json.dumps(
            {
                "schema": "proportions.v1",
                "id": "sideboard_01",
                "proportions": {"under_z_frac": round(LEG_H / H, 4), "drawer_bank_frac": round(span / case_h, 4)},
                "derivation": {
                    "under_z_frac": "leg height 177.8 mm / overall height 812.8 mm",
                    "drawer_bank_frac": "(3 stacked fronts + 2 reveals) / (overall height - leg height)",
                },
                "known_mm_assist": {"leg": LEG_H, "drawer_front": FRONT_H},
                "tolerance": 0.05,
            },
            indent=2,
        )
        + "\n"
    )
    (HERE / "views.json").write_text(
        json.dumps(
            {
                "schema": "views.v1",
                "id": "sideboard_01",
                "photos": ["sideboard_01_front_render.png"],
                "synthetic": True,
                "needed": [],
                "notes": "Orthographic shaded render of the design (gitignored). Not a photograph.",
            },
            indent=2,
        )
        + "\n"
    )
    (HERE / "README.md").write_text(
        "# sideboard_01 — SYNTHETIC ground truth\n\n"
        "Designed by `make_synthetic_gt.py`, not built or measured, and there is no real photo. "
        "Treat it as a generalisation stress test (straight ends, short tapered legs, three stacked "
        "drawers between two doors), not as real-world evidence like `console_01`.\n\n"
        "Regenerate: `python evals/photos/cases/sideboard_01/make_synthetic_gt.py`.\n\n"
        "To replace it with a real piece, put a Fusion export at `sideboard_01.step`, rewrite "
        "`cut_list.hand.json` from your plan, and set its `status` to `authoritative_hand_plan`.\n"
    )


def render_front(compound: Compound, path: Path, px_mm: float = 1.5) -> None:
    """Orthographic front render (looking along -Y): flat Lambert shading, painter's algorithm."""
    import numpy as np
    from PIL import Image, ImageDraw

    tris = []
    palette = [(150, 98, 60), (138, 90, 55), (160, 106, 66), (128, 84, 52), (146, 96, 58)]
    for si, solid in enumerate(compound.solids()):
        verts, faces = solid.tessellate(0.5)
        v = np.array([[p.X, p.Y, p.Z] for p in verts])
        base = palette[si % len(palette)]
        for f in faces:
            a, b, c = v[f[0]], v[f[1]], v[f[2]]
            n = np.cross(b - a, c - a)
            ln = np.linalg.norm(n)
            if ln < 1e-9:
                continue
            n = n / ln
            if n[1] <= 0.05:  # facing away from the camera
                continue
            light = 0.55 + 0.45 * max(0.0, float(n @ np.array([0.2, 0.6, 0.77])))
            col = tuple(int(min(255, ch * light)) for ch in base)
            tris.append((float((a[1] + b[1] + c[1]) / 3), [a, b, c], col))
    tris.sort(key=lambda t: t[0])  # far first
    pad = 40
    wpx, hpx = int(W / px_mm) + 2 * pad, int(H / px_mm) + 2 * pad
    img = Image.new("RGB", (wpx, hpx), (232, 230, 226))
    d = ImageDraw.Draw(img)
    for _, pts, col in tris:
        d.polygon([(pad + (p[0] + W / 2) / px_mm, hpx - pad - p[2] / px_mm) for p in pts], fill=col)
    # thin outline on every front-flush panel so door / drawer boundaries read like a photo
    for solid in compound.solids():
        b = solid.bounding_box()
        if b.max.Y < DC - 1.0 or b.size.Y > 60:  # only thin panels at the front plane
            continue
        x0, x1 = pad + (b.min.X + W / 2) / px_mm, pad + (b.max.X + W / 2) / px_mm
        y0, y1 = hpx - pad - b.max.Z / px_mm, hpx - pad - b.min.Z / px_mm
        d.rectangle([x0, y0, x1, y1], outline=(70, 42, 26), width=2)
    img.save(path)


def main() -> None:
    compound, parts = build()
    check(parts, compound)
    export_step(compound, str(HERE / "sideboard_01.step"))
    write_files(parts)
    render_front(compound, HERE / "sideboard_01_front_render.png")
    n = sum(p["qty"] for p in parts)
    print(f"sideboard_01: {len(parts)} part types, {n} pieces, {W:.0f} x {D:.0f} x {H:.0f} mm")
    print(f"drawer front {FRONT_H} mm, door bay {DOOR_BAY_W:.2f} mm, interior {INT_W:.1f} x {CI:.1f} mm")


if __name__ == "__main__":
    main()
