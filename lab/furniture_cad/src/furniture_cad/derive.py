"""Derive PartRecords from solids (R2) — geometry is the source of truth for blanks."""

from __future__ import annotations

from typing import Any

from furniture_cad.geom_check import bbox_mm_from_solid, solids_bbox_overlap
from furniture_cad.parts import PartRecord

# Estimate flags carried through Lists tab
FLAG_MEASURED = "Measured"  # finished size taken from solid AABB
FLAG_ESTIMATED = "Estimated"  # blank padded / stock-rounded
FLAG_GUESSED = "Guessed"  # no solid; typed dims only
FLAG_SHAPED = "Shaped from blank"  # fill ratio low → curved/shaped


def _solid_volume_mm3(solid: object) -> float | None:
    try:
        return float(solid.volume)  # type: ignore[attr-defined]
    except Exception:
        try:
            return float(abs(solid.wrapped.Volume()))  # type: ignore[attr-defined]
        except Exception:
            return None


def dims_from_solid(solid: object) -> dict[str, Any]:
    """Oriented as thickness=smallest, length=longest, width=middle; grain along length."""
    bb = bbox_mm_from_solid(solid)
    axes = [
        ("x", float(bb["w"])),
        ("y", float(bb["d"])),
        ("z", float(bb["h"])),
    ]
    axes_sorted = sorted(axes, key=lambda t: t[1])
    (t_ax, thickness), (w_ax, width), (l_ax, length) = axes_sorted[0], axes_sorted[1], axes_sorted[2]
    blank_vol = thickness * width * length
    solid_vol = _solid_volume_mm3(solid)
    fill = (solid_vol / blank_vol) if solid_vol and blank_vol > 0 else 1.0
    shaped = fill < 0.85
    return {
        "thickness_mm": thickness,
        "width_mm": width,
        "length_mm": length,
        "grain": l_ax,  # longest axis
        "fill_ratio": round(fill, 4),
        "shaped": shaped,
        "bbox": bb,
        "solid_volume_mm3": solid_vol,
        "blank_volume_mm3": blank_vol,
    }


def part(
    part_id: str,
    solid: object,
    *,
    material: str = "unknown",
    name: str | None = None,
    qty: int = 1,
    make: str | None = None,
    grain: str | None = None,
    blank_pad_mm: float = 0.0,
) -> PartRecord:
    """Register a solid → PartRecord with finished/blank sizes derived from geometry."""
    d = dims_from_solid(solid)
    how = make or ("shaped" if d["shaped"] else "solid")
    curved = bool(d["shaped"] or how in ("shaped", "turned", "sweep"))
    t, w, L = d["thickness_mm"], d["width_mm"], d["length_mm"]
    pad = float(blank_pad_mm)
    # Shaped parts get a small blank pad if none specified
    if curved and pad <= 0:
        pad = max(2.0, 0.05 * max(t, w, L))
    bt, bw, bl = t + pad, w + pad, L + pad
    flag = FLAG_SHAPED if curved else FLAG_MEASURED
    if pad > 0 and not curved:
        flag = FLAG_ESTIMATED
    return PartRecord(
        id=str(part_id),
        name=str(name or part_id),
        qty=max(1, int(qty)),
        material=str(material),
        thickness_mm=float(t),
        width_mm=float(w),
        length_mm=float(L),
        grain=str(grain or d["grain"]),
        how_made=str(how),
        curved=curved,
        blank_thickness_mm=float(bt),
        blank_width_mm=float(bw),
        blank_length_mm=float(bl),
        notes=f"derived from solid; fill={d['fill_ratio']}",
        tags=[flag],
        estimate_flag=flag,
        fill_ratio=float(d["fill_ratio"]),
        solid_ref=solid,
    )


def consistency_report(
    parts: list[PartRecord],
    assembly: object | None = None,
    *,
    volume_tol: float = 0.15,
) -> dict[str, Any]:
    """Warn when part volumes disagree with assembly or AABBs overlap."""
    warnings: list[str] = []
    part_vol = 0.0
    solids: list[tuple[str, object]] = []
    for p in parts:
        if p.solid_ref is not None:
            solids.append((p.id, p.solid_ref))
            v = _solid_volume_mm3(p.solid_ref)
            if v:
                part_vol += v * p.qty
        else:
            ft, fw, fl = p.finished_twl()
            part_vol += ft * fw * fl * p.qty

    asm_vol = _solid_volume_mm3(assembly) if assembly is not None else None
    volume_ok = None
    if asm_vol and part_vol > 0:
        err = abs(part_vol - asm_vol) / asm_vol
        volume_ok = err <= volume_tol
        if not volume_ok:
            warnings.append(
                f"part volume sum {part_vol:.0f} vs assembly {asm_vol:.0f} ({err:.1%} > {volume_tol:.0%})"
            )

    overlaps: list[str] = []
    for i in range(len(solids)):
        for j in range(i + 1, len(solids)):
            a_id, a = solids[i]
            b_id, b = solids[j]
            try:
                if solids_bbox_overlap(a, b):
                    overlaps.append(f"{a_id}∩{b_id}")
            except Exception:
                continue
    if overlaps:
        warnings.append("AABB overlaps: " + ", ".join(overlaps[:12]))

    return {
        "part_volume_mm3": round(part_vol, 2),
        "assembly_volume_mm3": round(asm_vol, 2) if asm_vol is not None else None,
        "volume_ok": volume_ok,
        "overlaps": overlaps,
        "warnings": warnings,
    }
