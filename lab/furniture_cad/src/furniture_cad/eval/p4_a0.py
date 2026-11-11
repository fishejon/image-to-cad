"""P4: three blind pipeline(+vision) runs on console_01 vs GT bar."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from furniture_cad.eval.console_gt import score_prediction
from furniture_cad.eval.scorer import feature_recall
from furniture_cad.pipeline import run_pipeline

LAB = Path(__file__).resolve().parents[3]
REPO = LAB.parent.parent
GT = REPO / "evals" / "photos" / "cases" / "console_01"
FEATURES = GT / "features.json"
PHOTO = GT / "console_01_front_clean.jpg"
KNOWN = {"w": 1193.8, "d": 304.8, "h": 762.0}


def _run_one(work: Path, *, use_vision: bool) -> dict[str, Any]:
    t0 = time.time()
    summary = run_pipeline(
        work_dir=work,
        photo=PHOTO if PHOTO.is_file() else None,
        known_mm=KNOWN,
        use_vision=use_vision,
        class_hint="casegood.console",
    )
    wall = time.time() - t0
    parts = json.loads((work / "parts.json").read_text(encoding="utf-8")).get("parts") or []
    bb = summary.get("bbox_mm") or {}
    obs_counts = summary.get("observation_counts") or {}
    truth_feats = {}
    if FEATURES.is_file():
        truth_feats = json.loads(FEATURES.read_text(encoding="utf-8")).get("counts") or {}
    fr = feature_recall(obs_counts, truth_feats) if truth_feats else None
    gt_score = score_prediction(
        predicted_parts=parts,
        predicted_features=summary.get("features") or {},
        overall_pred_mm={"w": bb.get("w"), "d": bb.get("d"), "h": bb.get("h")},
    )
    dim_ok = True
    for k, want in KNOWN.items():
        got = float(bb.get(k) or 0)
        if abs(got - want) / want > 0.03:
            dim_ok = False
    return {
        "ok": bool(summary.get("ok")),
        "dim_within_3pct": dim_ok,
        "bbox_mm": bb,
        "feature_recall": fr,
        "parts": gt_score.get("parts"),
        "cut_list_match_share": (gt_score.get("parts") or {}).get("cut_list_match_share"),
        "gt_score": gt_score,
        "spent_usd_approx": summary.get("spent_usd_approx"),
        "wall_s": round(wall, 2),
        "rounds": summary.get("rounds"),
        "perceive_mode": summary.get("perceive_mode"),
        "valid_solid": bool((summary.get("exported") or {}).get("stl")),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="P4 console A0 ×3 blind pipeline runs")
    p.add_argument("--out", type=Path, default=GT / "P4_A0.json")
    p.add_argument("--vision", action="store_true", default=True)
    p.add_argument("--no-vision", action="store_true")
    p.add_argument("--runs", type=int, default=3)
    args = p.parse_args(argv)
    use_vision = not args.no_vision
    runs = []
    out_root = args.out.parent / "p4_a0_runs"
    out_root.mkdir(parents=True, exist_ok=True)
    for i in range(1, args.runs + 1):
        work = out_root / f"run_{i}"
        if work.exists():
            # fresh-ish: overwrite artifacts
            pass
        work.mkdir(parents=True, exist_ok=True)
        print(f"run {i}/{args.runs} vision={use_vision} …", flush=True)
        runs.append(_run_one(work, use_vision=use_vision))

    def _mean(key: str) -> float | None:
        vals = []
        for r in runs:
            if key == "feature_recall":
                fr = r.get("feature_recall") or {}
                if fr.get("recall") is not None:
                    vals.append(float(fr["recall"]))
            elif key == "part_recall":
                parts = r.get("parts") or {}
                if parts.get("recall") is not None:
                    vals.append(float(parts["recall"]))
            elif key in r and isinstance(r[key], (int, float)):
                vals.append(float(r[key]))
        return round(sum(vals) / len(vals), 4) if vals else None

    report = {
        "schema": "p4_a0.v1",
        "piece": "console_01",
        "at": datetime.now(timezone.utc).isoformat(),
        "photo": str(PHOTO),
        "use_vision": use_vision,
        "runs": runs,
        "aggregate": {
            "n": len(runs),
            "all_ok": all(r.get("ok") for r in runs),
            "mean_feature_recall": _mean("feature_recall"),
            "mean_part_recall": _mean("part_recall"),
            "mean_spend_usd": _mean("spent_usd_approx"),
            "mean_wall_s": _mean("wall_s"),
            "dims_all_within_3pct": all(r.get("dim_within_3pct") for r in runs),
        },
        "p4_gate": {
            "dims_within_3pct": all(r.get("dim_within_3pct") for r in runs),
            "part_recall_ge_0_70": (_mean("part_recall") or 0) >= 0.70,
            "feature_recall_ge_0_90": (_mean("feature_recall") or 0) >= 0.90,
            "valid_solid": all(r.get("valid_solid") for r in runs),
            "notes": "IoU / blind human rating / board-ft deferred — D8 IoU still <0.8 on studio",
        },
    }
    gate = report["p4_gate"]
    report["p4_gate"]["partial_pass"] = all(
        [
            gate["dims_within_3pct"],
            gate["part_recall_ge_0_70"],
            gate["feature_recall_ge_0_90"] if use_vision else True,
            gate["valid_solid"],
        ]
    )
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["aggregate"], indent=2))
    print("gate", json.dumps(report["p4_gate"], indent=2))
    print("wrote", args.out)
    return 0 if report["p4_gate"]["partial_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
