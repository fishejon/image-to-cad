"""Score predicted models/lists against console_01 Fusion GT + hand cut list."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from furniture_cad.eval.scorer import score_run

LAB = Path(__file__).resolve().parents[3]
ROOT = LAB.parent.parent
GT_DIR = ROOT / "evals" / "photos" / "cases" / "console_01"
META = ROOT / "evals" / "photos" / "cases" / "console_01.json"

# Map common predicted ids → hand-list ids for matching
ID_ALIASES = {
    "top": "T1",
    "side": "E1",
    "end": "E1",
    "end_block": "E1",
    "bottom": "B1",
    "divider": "D1",
    "shelf": "D1",
    "back": "BK1",
    "drawer_front": "DF1",
    "front": "DF1",
    "leg": "L1",
    "drawer_side": "DS1",
    "drawer_back": "DB1",
    "drawer_bottom": "DBT1",
    "runner": "R1",
    "tongue": "LT",
    "wedge": "W1",
}


def load_hand_cut_list(path: Path | None = None) -> dict[str, Any]:
    path = path or (GT_DIR / "cut_list.hand.json")
    return json.loads(path.read_text(encoding="utf-8"))


def truth_parts_from_hand(hand: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for p in hand.get("parts") or []:
        out.append(
            {
                "id": p["id"],
                "name": p.get("name") or p["id"],
                "qty": int(p.get("qty") or 1),
                "thickness_mm": float(p["thickness_mm"]),
                "width_mm": float(p["width_mm"]),
                "length_mm": float(p["length_mm"]),
                "type": p["id"],
                "material": p.get("material"),
            }
        )
    return out


def truth_features_from_meta() -> dict[str, int]:
    meta = json.loads(META.read_text(encoding="utf-8")) if META.is_file() else {}
    s = (meta.get("source") or {}).get("structure") or {}
    return {
        "drawer": int(s.get("drawers") or 2),
        "leg": int(s.get("legs") or 4),
        "end_block": int(s.get("end_blocks_carved") or 2),
        "open_cubby": int(s.get("open_cubby") or 1),
    }


def normalize_pred_parts(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normed = []
    for p in parts:
        raw_id = str(p.get("id") or p.get("name") or "part")
        key = raw_id.lower().replace(" ", "_")
        mapped = ID_ALIASES.get(key) or ID_ALIASES.get(key.split("_")[0]) or raw_id
        row = dict(p)
        row["id"] = mapped
        row["type"] = mapped
        if "finished_mm" in row and row["finished_mm"]:
            t, w, L = [float(x) for x in row["finished_mm"][:3]]
            row.setdefault("thickness_mm", t)
            row.setdefault("width_mm", w)
            row.setdefault("length_mm", L)
        normed.append(row)
    return normed


def step_bbox_mm(step_path: Path | None = None) -> dict[str, float]:
    from build123d import import_step

    step_path = step_path or (GT_DIR / "console_01.step")
    solid = import_step(str(step_path))
    bb = solid.bounding_box()
    size = bb.size
    # Fusion model: X=W, Y=D, Z=H
    return {
        "w": float(size.X),
        "d": float(size.Y),
        "h": float(size.Z),
        "min": [float(bb.min.X), float(bb.min.Y), float(bb.min.Z)],
        "max": [float(bb.max.X), float(bb.max.Y), float(bb.max.Z)],
    }


def ensure_gt_stl(out_dir: Path | None = None) -> Path:
    from build123d import export_stl, import_step

    out_dir = out_dir or (LAB / "out" / "console_01_gt")
    out_dir.mkdir(parents=True, exist_ok=True)
    stl = out_dir / "console_01.stl"
    if not stl.is_file():
        solid = import_step(str(GT_DIR / "console_01.step"))
        export_stl(solid, str(stl))
    return stl


def score_gt_ceiling(*, measure_iou: bool = True) -> dict[str, Any]:
    """Answer-key self-check: STEP dims + photo IoU of GT STL."""
    hand = load_hand_cut_list()
    bbox = step_bbox_mm()
    truth_mm = {
        "w": float(hand["dims_mm"]["w"]),
        "d": float(hand["dims_mm"]["d"]),
        "h": float(hand["dims_mm"]["h"]),
    }
    dim_score = score_run(
        predicted_parts=[],
        truth_parts=[],
        overall_pred_mm={"w": bbox["w"], "d": bbox["d"], "h": bbox["h"]},
        overall_truth_mm=truth_mm,
    )
    iou = None
    rating = None
    photo = GT_DIR / "console_01.jpg"
    if measure_iou and photo.is_file():
        from furniture_cad.silhouette import rating_for_iou, silhouette_iou

        stl = ensure_gt_stl()
        m = silhouette_iou(photo, stl)
        iou = m["iou"]
        rating = rating_for_iou(iou)
    return {
        "schema": "furniture_cad.console_gt_ceiling.v1",
        "piece": "console_01",
        "step_bbox_mm": {k: bbox[k] for k in ("w", "d", "h")},
        "hand_dims_mm": truth_mm,
        "overall_dims_within_3pct": dim_score["overall_dims_within_3pct"],
        "overall_dims": dim_score["overall_dims"],
        "gt_stl_vs_photo_iou": iou,
        "gt_stl_vs_photo_rating": rating,
        "hand_part_types": len(hand.get("parts") or []),
        "hand_piece_count": sum(int(p.get("qty") or 0) for p in hand.get("parts") or []),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def score_prediction(
    *,
    predicted_parts: list[dict[str, Any]],
    predicted_features: dict[str, int] | None = None,
    overall_pred_mm: dict[str, float] | None = None,
    pred_stl: Path | str | None = None,
    cost_usd: float | None = None,
    wall_s: float | None = None,
) -> dict[str, Any]:
    hand = load_hand_cut_list()
    truth = truth_parts_from_hand(hand)
    feats_t = truth_features_from_meta()
    feats_p = predicted_features or {}
    truth_mm = {
        "w": float(hand["dims_mm"]["w"]),
        "d": float(hand["dims_mm"]["d"]),
        "h": float(hand["dims_mm"]["h"]),
    }
    iou = None
    rating = None
    photo = GT_DIR / "console_01.jpg"
    if pred_stl and photo.is_file() and Path(pred_stl).is_file():
        from furniture_cad.silhouette import rating_for_iou, silhouette_iou

        m = silhouette_iou(photo, Path(pred_stl))
        iou = m["iou"]
        rating = rating_for_iou(iou)
    report = score_run(
        predicted_parts=normalize_pred_parts(predicted_parts),
        truth_parts=truth,
        predicted_features=feats_p,
        truth_features=feats_t,
        overall_pred_mm=overall_pred_mm,
        overall_truth_mm=truth_mm,
        iou=iou,
        cost_usd=cost_usd,
        wall_s=wall_s,
    )
    report["piece"] = "console_01"
    report["iou_rating"] = rating
    report["truth_features"] = feats_t
    return report


def score_ir_stub() -> dict[str, Any]:
    """Score current furniture_ir stub compiler against the hand cut list."""
    from furniture_cad.construct import compile_ir
    from furniture_cad.geom_check import bbox_mm_from_solid

    ir = LAB / "examples" / "ir" / "console_stub.ir.json"
    result = compile_ir(ir)
    parts = []
    for p in result["parts"]:
        parts.append(p.to_dict() if hasattr(p, "to_dict") else dict(p))
    bb = bbox_mm_from_solid(result["assembly"])
    # Export STL for IoU
    from furniture_cad.export import export_solid

    out = LAB / "out" / "console_01_ir_stub"
    paths = export_solid(result["assembly"], out / "console_01_ir", formats=("stl",))
    return score_prediction(
        predicted_parts=parts,
        predicted_features=result.get("features") or {},
        overall_pred_mm={"w": bb["w"], "d": bb["d"], "h": bb["h"]},
        pred_stl=paths.get("stl"),
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Score console_01 against Fusion GT + hand cut list")
    p.add_argument("--ceiling", action="store_true", help="STEP self-check + GT STL vs photo IoU")
    p.add_argument("--ir-stub", action="store_true", help="score IR compiler stub vs hand list")
    p.add_argument("--parts", type=Path, default=None, help="predicted parts JSON")
    p.add_argument("--stl", type=Path, default=None, help="predicted STL for IoU")
    p.add_argument("--overall-mm", nargs=3, type=float, metavar=("W", "D", "H"), default=None)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    if args.ceiling:
        report = score_gt_ceiling()
    elif args.ir_stub:
        report = score_ir_stub()
    elif args.parts:
        data = json.loads(args.parts.read_text(encoding="utf-8"))
        parts = data.get("parts") or data
        overall = None
        if args.overall_mm:
            overall = {"w": args.overall_mm[0], "d": args.overall_mm[1], "h": args.overall_mm[2]}
        report = score_prediction(predicted_parts=parts, overall_pred_mm=overall, pred_stl=args.stl)
    else:
        # default: both ceiling + ir stub
        report = {
            "schema": "furniture_cad.console_gt_bundle.v1",
            "ceiling": score_gt_ceiling(),
            "ir_stub": score_ir_stub(),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

    text = json.dumps(report, indent=2) + "\n"
    out = args.out or (ROOT / "evals" / "photos" / "cases" / "console_01" / "score.gt.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
