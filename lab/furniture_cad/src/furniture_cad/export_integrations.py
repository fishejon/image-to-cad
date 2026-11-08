"""Export integrations — Fusion STEP, SketchUp stub, CNC DXF (Phase 4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from furniture_cad.export import export_solid
from furniture_cad.export_shop import export_dxf_stub


def export_fusion_step(assembly: object, dest_stem: Path | str) -> dict[str, Path]:
    """Canonical Fusion round-trip artifact: STEP (+ STL companion)."""
    return export_solid(assembly, Path(dest_stem), formats=("step", "stl"))


def export_sketchup_stub(ir: dict[str, Any], dest: Path | str) -> Path:
    """JSON sidecar SketchUp importers can map (not binary .skp)."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "sketchup_bridge.v1",
        "units": ir.get("units") or "mm",
        "params": ir.get("params") or {},
        "root": ir.get("root") or {},
        "note": "Import via bridge script; binary .skp not emitted here",
    }
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return dest


def export_cnc_dxf(cut_list_v2: dict[str, Any], dest: Path | str) -> Path:
    """CNC-oriented DXF of blank faces (reuses shop DXF stub)."""
    return export_dxf_stub(cut_list_v2, dest)


def export_pack(
    *,
    assembly: object,
    ir: dict[str, Any],
    cut_list_v2: dict[str, Any],
    out_dir: Path | str,
    stem: str = "model",
) -> dict[str, str]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = export_fusion_step(assembly, out_dir / stem)
    skp = export_sketchup_stub(ir, out_dir / f"{stem}.sketchup.json")
    dxf = export_cnc_dxf(cut_list_v2, out_dir / f"{stem}.cnc.dxf")
    return {
        **{k: str(v) for k, v in paths.items()},
        "sketchup_json": str(skp),
        "cnc_dxf": str(dxf),
    }
