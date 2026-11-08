"""Joinery / blank allowances → PartRecord v2-shaped dicts (Phase 1)."""

from __future__ import annotations

from typing import Any

from furniture_cad.parts import PartRecord

# Default mm pads by how_made
DEFAULT_ALLOWANCE = {
    "solid": {"thickness": 0.0, "width": 0.0, "length": 0.0, "joinery_ends": 0.0},
    "shaped": {"thickness": 3.0, "width": 3.0, "length": 10.0, "joinery_ends": 0.0},
    "sheet": {"thickness": 0.0, "width": 2.0, "length": 2.0, "joinery_ends": 0.0},
    "panel": {"thickness": 0.0, "width": 2.0, "length": 2.0, "joinery_ends": 0.0},
}


def allowance_for(how_made: str, *, joinery_ends_mm: float = 0.0) -> dict[str, float]:
    base = dict(DEFAULT_ALLOWANCE.get(how_made) or DEFAULT_ALLOWANCE["solid"])
    if joinery_ends_mm:
        base["joinery_ends"] = float(joinery_ends_mm)
        base["length"] = float(base["length"]) + float(joinery_ends_mm)
    return base


def part_record_v2(
    rec: PartRecord,
    *,
    frame: dict[str, Any] | None = None,
    joints: list[dict[str, Any]] | None = None,
    hardware: list[dict[str, Any]] | None = None,
    stock: str | None = None,
    joinery_ends_mm: float = 0.0,
    prov: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Serialize PartRecord + local-frame / allowance fields (PartRecord v2 shape)."""
    how = rec.how_made or "solid"
    allow = allowance_for(how, joinery_ends_mm=joinery_ends_mm)
    t, w, L = rec.finished_twl()
    blank_t = (rec.blank_thickness_mm if rec.blank_thickness_mm is not None else t) + allow["thickness"]
    blank_w = (rec.blank_width_mm if rec.blank_width_mm is not None else w) + allow["width"]
    blank_L = (rec.blank_length_mm if rec.blank_length_mm is not None else L) + allow["length"]
    return {
        "id": rec.id,
        "name": rec.name,
        "qty": rec.qty,
        "material": rec.material,
        "frame": frame or {"origin": [0, 0, 0], "axes": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
        "finished_mm": [round(t, 2), round(w, 2), round(L, 2)],
        "blank_mm": [round(blank_t, 2), round(blank_w, 2), round(blank_L, 2)],
        "allowance": allow,
        "grain": rec.grain,
        "stock": stock or rec.material,
        "joints": joints or [],
        "hardware": hardware or [],
        "estimate_flag": rec.estimate_flag,
        "prov": prov or {"dims": "solid", "conf": 0.9 if rec.estimate_flag == "Measured" else 0.5},
    }


def lists_with_allowances(parts: list[PartRecord]) -> dict[str, Any]:
    rows = [part_record_v2(p) for p in parts]
    return {"schema": "cut_list.v2", "parts": rows, "count": len(rows)}
