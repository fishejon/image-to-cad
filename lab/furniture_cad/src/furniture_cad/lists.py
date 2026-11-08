"""Cut list + material / board-feet builder from PartRecords (Phase 1).

Ported in spirit from src/core/units.js + checks.js cutList — lab-side, offline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from furniture_cad.parts import PartRecord, load_parts, total_qty

MM_PER_IN = 25.4
KERF_IN = 1 / 8
BOARD_LENS_IN = (96, 120, 144)  # 8′, 10′, 12′

DIM_LUMBER = [
    {"nom": "1×2", "t": 0.75, "w": 1.5},
    {"nom": "1×3", "t": 0.75, "w": 2.5},
    {"nom": "1×4", "t": 0.75, "w": 3.5},
    {"nom": "1×6", "t": 0.75, "w": 5.5},
    {"nom": "1×8", "t": 0.75, "w": 7.25},
    {"nom": "1×10", "t": 0.75, "w": 9.25},
    {"nom": "1×12", "t": 0.75, "w": 11.25},
    {"nom": "2×2", "t": 1.5, "w": 1.5},
    {"nom": "2×4", "t": 1.5, "w": 3.5},
    {"nom": "2×6", "t": 1.5, "w": 5.5},
]
HARDWOOD_THICK = [
    {"nom": "4/4", "t": 13 / 16},
    {"nom": "5/4", "t": 1 + 1 / 16},
    {"nom": "6/4", "t": 1 + 5 / 16},
    {"nom": "8/4", "t": 1.75},
]
SHEET_STOCK = [
    {"nom": "¼″ ply", "t": 0.25},
    {"nom": "⅜″ ply", "t": 0.375},
    {"nom": "½″ ply", "t": 0.5},
    {"nom": "¾″ ply", "t": 0.75},
]


def mm_to_in(mm: float) -> float:
    return float(mm) / MM_PER_IN


def board_feet(t_mm: float, w_mm: float, L_mm: float, qty: int = 1) -> float:
    """Nominal board feet from blank size (inches formula)."""
    t, w, L = mm_to_in(t_mm), mm_to_in(w_mm), mm_to_in(L_mm)
    return (t * w * L / 12.0) * qty


def cut_rows(parts: list[PartRecord]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in parts:
        ft, fw, fl = p.finished_twl()
        bt, bw, bl = p.blank_twl()
        rows.append(
            {
                "id": p.id,
                "name": p.name,
                "qty": p.qty,
                "material": p.material,
                "how_made": p.how_made,
                "grain": p.grain,
                "curved": p.curved,
                "finished_mm": [round(ft, 3), round(fw, 3), round(fl, 3)],
                "blank_mm": [round(bt, 3), round(bw, 3), round(bl, 3)],
                "board_feet": round(board_feet(bt, bw, bl, p.qty), 3),
                "notes": p.notes,
                "estimate_flag": getattr(p, "estimate_flag", None) or "Guessed",
                "fill_ratio": getattr(p, "fill_ratio", None),
            }
        )
    return rows


def _fit_thickness(t_in: float, catalog: list[dict[str, Any]]) -> dict[str, Any] | None:
    pad = 1 / 16
    best = None
    for s in catalog:
        if s["t"] + 1e-6 >= t_in - pad:
            waste = s["t"] - t_in
            if best is None or waste < best["waste"]:
                best = {"nom": s["nom"], "t": s["t"], "waste": waste}
    return best


def _fit_dim(t_mm: float, w_mm: float) -> dict[str, Any] | None:
    ti, wi = mm_to_in(t_mm), mm_to_in(w_mm)
    pad = 1 / 16
    best = None
    for s in DIM_LUMBER:
        for tt, ww, swapped in ((s["t"], s["w"], False), (s["w"], s["t"], True)):
            if tt + 1e-6 >= ti - pad and ww + 1e-6 >= wi - pad:
                waste = (tt - ti) + (ww - wi)
                if best is None or waste < best["waste"]:
                    best = {"nom": s["nom"], "t": tt, "w": ww, "waste": waste, "swapped": swapped}
    return best


def stock_for_blank(t_mm: float, w_mm: float, L_mm: float, material: str) -> dict[str, Any]:
    name = (material or "").lower()
    is_sheet = any(k in name for k in ("ply", "mdf", "osb", "sheet", "veneer"))
    if is_sheet:
        th = _fit_thickness(mm_to_in(t_mm), SHEET_STOCK) or _fit_thickness(mm_to_in(t_mm), HARDWOOD_THICK)
        return {
            "kind": "sheet",
            "stock": th["nom"] if th else f'{mm_to_in(t_mm):.3f}" sheet',
            "T_in": th["t"] if th else mm_to_in(t_mm),
            "W_in": mm_to_in(w_mm),
            "L_in": mm_to_in(L_mm),
            "note": "sheet good",
        }
    soft = _fit_dim(t_mm, w_mm)
    if soft and soft["waste"] < 2.5:
        return {
            "kind": "dim",
            "stock": soft["nom"],
            "T_in": soft["t"],
            "W_in": soft["w"],
            "L_in": mm_to_in(L_mm),
            "note": "rotate blank" if soft["swapped"] else "",
        }
    ht = _fit_thickness(min(mm_to_in(t_mm), mm_to_in(w_mm)), HARDWOOD_THICK)
    face = max(mm_to_in(t_mm), mm_to_in(w_mm))
    return {
        "kind": "hardwood",
        "stock": f"{ht['nom'] if ht else '?'} × ≥{face:.3f}\"",
        "T_in": ht["t"] if ht else min(mm_to_in(t_mm), mm_to_in(w_mm)),
        "W_in": face,
        "L_in": mm_to_in(L_mm),
        "note": "hardwood / random width",
    }


def _pack_boards(cuts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = sorted(cuts, key=lambda c: -c["len_in"])
    bins: list[dict[str, Any]] = []
    for it in items:
        placed = False
        for b in bins:
            need = it["len_in"] + (KERF_IN if b["cuts"] else 0)
            if b["used"] + need <= 144 + 1e-6:
                b["cuts"].append(it)
                b["used"] += need
                placed = True
                break
        if not placed:
            bins.append({"cuts": [it], "used": it["len_in"]})
    out = []
    for i, b in enumerate(bins, 1):
        buy = next((L for L in BOARD_LENS_IN if b["used"] <= L + 1e-6), int((b["used"] + 11) // 12) * 12)
        out.append({"n": i, "used_in": round(b["used"], 3), "buy_in": buy, "buy_ft": f"{buy // 12}′", "cuts": b["cuts"]})
    return out


def material_plan(parts: list[PartRecord]) -> dict[str, Any]:
    blanks: list[dict[str, Any]] = []
    for p in parts:
        bt, bw, bl = p.blank_twl()
        st = stock_for_blank(bt, bw, bl, p.material)
        for _ in range(p.qty):
            blanks.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "material": p.material,
                    "finished_mm": list(p.finished_twl()),
                    "blank_mm": [bt, bw, bl],
                    "stock": st["stock"],
                    "kind": st["kind"],
                    "note": st.get("note") or "",
                    "len_in": st["L_in"],
                    "board_feet": round(board_feet(bt, bw, bl, 1), 3),
                }
            )

    groups: dict[str, dict[str, Any]] = {}
    for b in blanks:
        key = f"{b['kind']}|{b['stock']}|{b['material']}"
        g = groups.setdefault(key, {"kind": b["kind"], "stock": b["stock"], "material": b["material"], "note": b["note"], "blanks": []})
        g["blanks"].append(b)

    boards: list[dict[str, Any]] = []
    for g in groups.values():
        if g["kind"] == "sheet":
            # One 4×8 sheet per group for v0 (area check later).
            boards.append(
                {
                    "kind": "sheet",
                    "stock": g["stock"],
                    "material": g["material"],
                    "buy": "4×8 sheet",
                    "qty_boards": 1,
                    "pieces": len(g["blanks"]),
                    "cuts": [{"id": b["id"], "name": b["name"]} for b in g["blanks"]],
                    "note": g["note"],
                }
            )
            continue
        packed = _pack_boards(g["blanks"])
        for p in packed:
            boards.append(
                {
                    "kind": g["kind"],
                    "stock": g["stock"],
                    "material": g["material"],
                    "buy": p["buy_ft"],
                    "buy_in": p["buy_in"],
                    "used_in": p["used_in"],
                    "qty_boards": 1,
                    "pieces": len(p["cuts"]),
                    "cuts": [{"id": c["id"], "name": c["name"], "len_in": c["len_in"]} for c in p["cuts"]],
                    "note": g["note"],
                }
            )

    # Collapse identical buy lines
    summary_map: dict[str, dict[str, Any]] = {}
    for b in boards:
        key = f"{b['kind']}|{b['stock']}|{b.get('buy')}|{b['material']}"
        s = summary_map.setdefault(
            key,
            {
                "kind": b["kind"],
                "stock": b["stock"],
                "material": b["material"],
                "buy": b.get("buy"),
                "qty": 0,
                "pieces": 0,
                "note": b.get("note") or "",
            },
        )
        s["qty"] += b.get("qty_boards", 1)
        s["pieces"] += b.get("pieces", 0)

    summary = []
    for s in summary_map.values():
        if s["kind"] == "sheet":
            line = f"{s['qty']}× {s['stock']} (4×8 sheet)"
        else:
            line = f"{s['qty']}× {s['stock']} × {s['buy']}"
        summary.append({**s, "buy_line": line})

    total_bf = round(sum(b["board_feet"] for b in blanks), 3)
    waste_ratio = None
    buy_bf_est = 0.0
    for s in summary:
        if s["kind"] == "sheet":
            continue
        # rough: board cross-section unknown for hardwood; skip precise waste
        buy_bf_est += s["qty"]  # placeholder count of boards, not bf
    return {
        "cut_list": cut_rows(parts),
        "blanks": blanks,
        "boards": boards,
        "summary": sorted(summary, key=lambda x: (x["kind"], x["stock"])),
        "totals": {
            "part_types": len(parts),
            "piece_count": total_qty(parts),
            "blank_board_feet": total_bf,
            "board_lines": len(summary),
        },
        "kerf_in": KERF_IN,
    }


def compare_qty(parts: list[PartRecord], expected: dict[str, int]) -> list[str]:
    """Return list of mismatch strings. expected maps part id → qty."""
    got = {p.id: p.qty for p in parts}
    errs: list[str] = []
    for pid, q in expected.items():
        if got.get(pid) != q:
            errs.append(f"{pid}: got {got.get(pid)} want {q}")
    for pid in got:
        if pid not in expected:
            errs.append(f"{pid}: unexpected part")
    return errs


def within_size_pct(a_mm: float, b_mm: float, pct: float = 5.0) -> bool:
    if b_mm == 0:
        return a_mm == 0
    return abs(a_mm - b_mm) / abs(b_mm) * 100.0 <= pct


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="furniture_cad lists — cut/material from parts.json")
    p.add_argument("--parts", type=Path, required=True, help="parts.json (PartRecord list)")
    p.add_argument("--out", type=Path, default=None, help="Write plan JSON here")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    parts = load_parts(args.parts)
    plan = material_plan(parts)
    text = json.dumps(plan, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    t = plan["totals"]
    print(f"parts={t['part_types']} pieces={t['piece_count']} blank_bf={t['blank_board_feet']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
