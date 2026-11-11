"""P2 staged pipeline: Intake → Perceive → Dimension → Construct → Compile → Verify → Derive.

Perceive is heuristic until P3 (vision). Construct loads a seed IR (console) or builds
params from known dims. No model calls on this path.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from furniture_cad.construct import compile_ir, load_ir
from furniture_cad.dimension import apply_dims
from furniture_cad.export import export_solid
from furniture_cad.geom_check import bbox_mm_from_solid
from furniture_cad.intake import intake_photo
from furniture_cad.perceive import perceive_casegood
from furniture_cad.verify import verify_against_dims

LAB = Path(__file__).resolve().parents[2]
CONSOLE_IR = LAB / "examples" / "ir" / "console_01.ir.json"


def _event(events: list[dict[str, Any]], stage: str, **kwargs: Any) -> None:
    events.append({"stage": stage, "at": datetime.now(timezone.utc).isoformat(), **kwargs})


def run_pipeline(
    *,
    work_dir: Path | str,
    photo: Path | str | None = None,
    known_mm: dict[str, float] | None = None,
    seed_ir: Path | str | dict[str, Any] | None = None,
    class_hint: str = "casegood.console",
) -> dict[str, Any]:
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, Any]] = []
    known_mm = known_mm or {}

    # 1. Intake
    intake = None
    if photo and Path(photo).is_file():
        intake = intake_photo(photo, known_mm=known_mm or None)
        (work / "intake.json").write_text(
            json.dumps({k: v for k, v in intake.items() if k not in ("mask", "image")}, indent=2, default=str)
            + "\n",
            encoding="utf-8",
        )
        _event(events, "intake", ok=True, seg=intake.get("segmentation"))
    else:
        intake = {
            "schema": "intake.v1",
            "path": None,
            "segmentation": {"score": 0.4, "quality": "no_photo"},
            "rectify": {"rectified": False},
            "scale": None,
        }
        _event(events, "intake", ok=True, note="no_photo")

    # 2. Perceive (heuristic)
    obs = perceive_casegood(intake, class_hint=class_hint, known_mm=known_mm or None)
    (work / "observation.json").write_text(json.dumps(obs, indent=2) + "\n", encoding="utf-8")
    _event(events, "perceive", ok=True, class_=obs.get("class"), unknowns=len(obs.get("unknowns") or []))

    # 3. Dimension
    dims = apply_dims(obs, known_mm=known_mm or None)
    (work / "dimension.json").write_text(json.dumps(dims, indent=2) + "\n", encoding="utf-8")
    _event(events, "dimension", ok=bool(dims.get("ready")), overall=dims.get("overall_mm"))

    # 4–5. Construct + Compile (seed IR with anchored dims)
    ir_src = seed_ir or CONSOLE_IR
    ir = load_ir(ir_src)
    if ir.get("schema") == "furniture_ir.v2":
        params = dict(ir.get("params") or {})
        overall = dims.get("overall_mm") or {}
        for key, letter in (("W", "W"), ("D", "D"), ("H", "H")):
            entry = overall.get(letter) or {}
            if entry.get("v") is not None:
                params[letter] = float(entry["v"])
        ir = {**ir, "params": params}
    (work / "ir.json").write_text(json.dumps(ir, indent=2) + "\n", encoding="utf-8")
    _event(events, "construct", ok=True, schema=ir.get("schema"), ir_path=str(ir_src))

    compiled = compile_ir(ir)
    _event(events, "compile", ok=True, features=compiled.get("features"), ir_hash=compiled.get("report", {}).get("ir_hash"))

    # Export
    paths = export_solid(compiled["assembly"], work / "model", formats=("stl", "step"))
    bb = bbox_mm_from_solid(compiled["assembly"])
    (work / "parts.json").write_text(
        json.dumps({"parts": [p.to_dict() for p in compiled["parts"]]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (work / "cut_list_v2.json").write_text(json.dumps(compiled.get("cut_list_v2") or {}, indent=2) + "\n", encoding="utf-8")

    # 6. Verify
    targets = {
        "w": float((dims.get("overall_mm") or {}).get("W", {}).get("v") or bb["w"]),
        "d": float((dims.get("overall_mm") or {}).get("D", {}).get("v") or bb["d"]),
        "h": float((dims.get("overall_mm") or {}).get("H", {}).get("v") or bb["h"]),
    }
    verify = verify_against_dims(
        compiled["assembly"],
        targets,
        features_expected={"drawer": 2, "leg": 4} if "console" in class_hint else None,
        features_found=compiled.get("features"),
    )
    (work / "verify.json").write_text(json.dumps(verify, indent=2) + "\n", encoding="utf-8")
    _event(events, "verify", ok=bool(verify.get("ok")), discrepancies=len(verify.get("discrepancies") or []))

    # 7. Derive already in cut_list_v2
    _event(events, "derive", ok=True, parts=len(compiled["parts"]))

    (work / "events.json").write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")

    summary = {
        "mode": "pipeline",
        "ok": bool(verify.get("ok")) and bool(paths.get("stl")),
        "stages": [e["stage"] for e in events],
        "events": events,
        "bbox_mm": bb,
        "features": compiled.get("features"),
        "parts_count": len(compiled["parts"]),
        "piece_count": sum(int(p.qty) for p in compiled["parts"]),
        "exported": {k: str(v) for k, v in paths.items()},
        "verify": verify,
        "observation_class": obs.get("class"),
        "ir_hash": (compiled.get("report") or {}).get("ir_hash"),
        "spent_usd_approx": 0.0,
        "rounds": 1,
        "stop_reason": "pipeline_complete" if verify.get("ok") else "verify_failed",
    }
    (work / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
