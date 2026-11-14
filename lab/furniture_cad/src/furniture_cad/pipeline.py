"""P2/P3 staged pipeline: Intake → Perceive → Dimension → Construct → Compile → Verify → Derive.

Perceive is heuristic by default ($0). Set use_vision=True or FURNITURE_CAD_PERCEIVE=vision
for Anthropic two-pass counts (P3). Construct loads a seed IR (console) or builds
params from known dims.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from furniture_cad.construct import load_ir
from furniture_cad.dimension import apply_dims
from furniture_cad.export import export_solid
from furniture_cad.geom_check import bbox_mm_from_solid
from furniture_cad.intake import intake_photo
from furniture_cad.perceive import feature_counts_from_observation, perceive_casegood, perceive_vision
from furniture_cad.verify import repair_loop

LAB = Path(__file__).resolve().parents[2]
CONSOLE_IR = LAB / "examples" / "ir" / "console_01.ir.json"


def _event(events: list[dict[str, Any]], stage: str, **kwargs: Any) -> None:
    events.append({"stage": stage, "at": datetime.now(timezone.utc).isoformat(), **kwargs})


def _want_vision(use_vision: bool | None) -> bool:
    if use_vision is not None:
        return bool(use_vision)
    return (os.environ.get("FURNITURE_CAD_PERCEIVE") or "").strip().lower() in (
        "vision",
        "vision_v1",
        "1",
        "true",
        "yes",
    )


def run_pipeline(
    *,
    work_dir: Path | str,
    photo: Path | str | None = None,
    known_mm: dict[str, float] | None = None,
    seed_ir: Path | str | dict[str, Any] | None = None,
    class_hint: str = "casegood.console",
    use_vision: bool | None = None,
    max_repair_rounds: int = 4,
) -> dict[str, Any]:
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, Any]] = []
    known_mm = known_mm or {}
    vision = _want_vision(use_vision)
    spend = 0.0

    # 1. Intake
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

    # 2. Perceive
    if vision:
        obs = perceive_vision(
            intake,
            class_hint=class_hint,
            known_mm=known_mm or None,
            photo=photo,
        )
    else:
        obs = perceive_casegood(intake, class_hint=class_hint, known_mm=known_mm or None)
    (work / "observation.json").write_text(json.dumps(obs, indent=2) + "\n", encoding="utf-8")
    feat_counts = feature_counts_from_observation(obs)
    spend += float((obs.get("meta") or {}).get("spend_usd_approx") or 0.0)
    _event(
        events,
        "perceive",
        ok=True,
        class_=obs.get("class"),
        mode=(obs.get("meta") or {}).get("perceive"),
        unknowns=len(obs.get("unknowns") or []),
        counts=feat_counts,
    )

    # 3. Dimension
    dims = apply_dims(obs, known_mm=known_mm or None)
    (work / "dimension.json").write_text(json.dumps(dims, indent=2) + "\n", encoding="utf-8")
    _event(
        events,
        "dimension",
        ok=bool(dims.get("ready")),
        overall=dims.get("overall_mm"),
        conflicts=len(dims.get("conflicts") or []),
        within_3pct=dims.get("within_3pct"),
    )

    # 4–6. Construct + Compile + Verify (+ IR patch repair)
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
    # Provenance: when no seed IR is passed we fall back to the hand-written console IR,
    # which is built from the answer key. Part / cut-list scores against that key are
    # therefore NOT blind: Perceive only supplies dims and feature counts.
    answer_key_seeded = seed_ir is None
    _event(
        events,
        "construct",
        ok=True,
        schema=ir.get("schema"),
        ir_path=str(ir_src),
        answer_key_seeded=answer_key_seeded,
    )

    expected_feats = {"drawer": 2, "leg": 4} if "console" in class_hint else None
    targets = {
        "w": float((dims.get("overall_mm") or {}).get("W", {}).get("v") or 0),
        "d": float((dims.get("overall_mm") or {}).get("D", {}).get("v") or 0),
        "h": float((dims.get("overall_mm") or {}).get("H", {}).get("v") or 0),
    }
    repair = repair_loop(
        ir,
        targets_mm=targets,
        features_expected=expected_feats,
        max_rounds=max_repair_rounds,
    )
    spend += float(repair.get("spent_usd_approx") or 0.0)
    ir = repair["ir"]
    compiled = repair["compiled"]
    verify = repair["verify"] or {"ok": False, "discrepancies": []}
    (work / "ir.json").write_text(json.dumps(ir, indent=2) + "\n", encoding="utf-8")
    (work / "repair.json").write_text(json.dumps({k: v for k, v in repair.items() if k != "compiled"}, indent=2, default=str) + "\n", encoding="utf-8")
    _event(
        events,
        "compile",
        ok=True,
        features=(compiled or {}).get("features"),
        ir_hash=((compiled or {}).get("report") or {}).get("ir_hash"),
        repair_rounds=repair.get("rounds"),
    )

    # Export
    paths = export_solid(compiled["assembly"], work / "model", formats=("stl", "step"))
    bb = bbox_mm_from_solid(compiled["assembly"])
    (work / "parts.json").write_text(
        json.dumps({"parts": [p.to_dict() for p in compiled["parts"]]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (work / "cut_list_v2.json").write_text(json.dumps(compiled.get("cut_list_v2") or {}, indent=2) + "\n", encoding="utf-8")

    (work / "verify.json").write_text(json.dumps(verify, indent=2) + "\n", encoding="utf-8")
    _event(
        events,
        "verify",
        ok=bool(verify.get("ok")),
        discrepancies=len(verify.get("discrepancies") or []),
        repair_rounds=repair.get("rounds"),
    )

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
        "observation_counts": feat_counts,
        "parts_count": len(compiled["parts"]),
        "piece_count": sum(int(p.qty) for p in compiled["parts"]),
        "exported": {k: str(v) for k, v in paths.items()},
        "verify": verify,
        "repair": {"rounds": repair.get("rounds"), "ok": repair.get("ok"), "history": repair.get("history")},
        "observation_class": obs.get("class"),
        "dimension": {
            "ready": dims.get("ready"),
            "within_3pct": dims.get("within_3pct"),
            "conflicts": dims.get("conflicts"),
        },
        "ir_hash": (compiled.get("report") or {}).get("ir_hash"),
        "construct_answer_key_seeded": answer_key_seeded,
        "spent_usd_approx": round(spend, 4),
        "rounds": int(repair.get("rounds") or 1),
        "perceive_mode": (obs.get("meta") or {}).get("perceive"),
        "stop_reason": "pipeline_complete" if verify.get("ok") else "verify_failed",
    }
    (work / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
