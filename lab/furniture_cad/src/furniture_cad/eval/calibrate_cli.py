"""CLI: calibrate console_01 GT (D8) and publish table."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from furniture_cad.eval.console_gt import ensure_gt_stl, score_gt_ceiling, score_ir_stub
from furniture_cad.verify.camera_fit import calibrate_gt

LAB = Path(__file__).resolve().parents[3]
ROOT = LAB.parent.parent
GT = ROOT / "evals" / "photos" / "cases" / "console_01"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="D8 calibration + console metric table")
    p.add_argument("--out", type=Path, default=GT / "CALIBRATION.json")
    args = p.parse_args(argv)

    views = json.loads((GT / "views.json").read_text(encoding="utf-8")) if (GT / "views.json").is_file() else {}
    photos = views.get("photos") or [{}]
    # Prefer D8-eligible front photo
    photo_meta = next((p for p in photos if p.get("d8_calibration_eligible")), photos[0])
    pose = photo_meta.get("pose_hint") or "front"
    photo = GT / str(photo_meta.get("file") or "console_01.jpg")
    step = GT / "console_01.step"

    ensure_gt_stl()
    cal = calibrate_gt(photo=photo, step_or_stl=step, pose_hint=pose)
    # Diagnostic: clean iso (not D8-eligible) — shows mask quality when props are gone
    iso_clean = GT / "console_01_iso_clean.jpg"
    iso_cal = None
    if iso_clean.is_file():
        iso_cal = calibrate_gt(photo=iso_clean, step_or_stl=step, pose_hint="three_quarter_left")
    ceiling = score_gt_ceiling(measure_iou=True)  # legacy fixed-scale ortho for comparison
    ir = score_ir_stub()
    a0 = {}
    score_path = GT / "score.json"
    if score_path.is_file():
        a0 = (json.loads(score_path.read_text(encoding="utf-8")).get("blind_A") or {})

    table = {
        "schema": "furniture_cad.calibrated_table.v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "piece": "console_01",
        "photo": {
            "file": str(photo_meta.get("file") or photo.name),
            "pose_hint": pose,
            "d8_eligible": bool(photo_meta.get("d8_calibration_eligible")),
        },
        "d8_calibration": cal,
        "diagnostic_iso_clean": iso_cal,
        "legacy_fixed_scale_ortho": {
            "gt_stl_iou": ceiling.get("gt_stl_vs_photo_iou"),
            "gt_rating": ceiling.get("gt_stl_vs_photo_rating"),
            "ir_stub_iou": ir.get("iou"),
            "ir_stub_rating": ir.get("iou_rating"),
            "a0_iou": a0.get("iou"),
            "a0_rating": a0.get("rating"),
            "note": "Orthographic fixed-scale — untrusted when D8 fails",
        },
        "non_iou_metrics": {
            "gt_dims_within_3pct": ceiling.get("overall_dims_within_3pct"),
            "ir_stub_dims_within_3pct": ir.get("overall_dims_within_3pct"),
            "ir_stub_parts_recall": (ir.get("parts") or {}).get("recall"),
            "a0_parts_recall": ((a0.get("runs") or [{}])[0]).get("parts_recall"),
            "a0_cut_list_match_share": ((a0.get("runs") or [{}])[0]).get("cut_list_match_share"),
            "a0_cost_usd": a0.get("cost_usd"),
        },
        "gate": {
            "iou_trusted_for_product_gates": bool(cal.get("passed")),
            "use_until_pass": ["overall_dims", "part_recall", "feature_recall", "cut_list_match"],
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")
    md = GT / "CALIBRATION.md"
    md.write_text(
        "\n".join(
            [
                "# console_01 — calibrated metric table (P0 / D8)",
                "",
                f"Recorded: `{table['recorded_at']}`",
                "",
                f"**D8 calibration (front):** {'PASS' if cal.get('passed') else 'FAIL'} — "
                f"camera-fit IoU **{cal.get('iou')}** (need ≥ {cal.get('threshold')}).",
                "",
                (
                    f"**Clean iso diagnostic:** IoU **{iso_cal.get('iou')}** ({iso_cal.get('rating')}) "
                    f"on `console_01_iso_clean.jpg` — not a D8 gate, but shows white-bg helps."
                    if iso_cal
                    else ""
                ),
                "",
                f"D8 still wants a **front-on, no-props, plain-bg** shot (same as iso_clean but straight-on).",
                "",
                "| Source | Legacy ortho IoU | Rating |",
                "| --- | ---: | --- |",
                f"| GT STEP→STL | {ceiling.get('gt_stl_vs_photo_iou')} | {ceiling.get('gt_stl_vs_photo_rating')} |",
                f"| IR stub | {ir.get('iou')} | {ir.get('iou_rating')} |",
                f"| A0 smoke | {a0.get('iou')} | {a0.get('rating')} |",
                "",
                "Until D8 passes, product gates use **dims / parts / features / cut-list**, not IoU.",
                "",
                f"Machine record: [`CALIBRATION.json`](CALIBRATION.json)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out),
                "d8_passed": cal.get("passed"),
                "d8_iou": cal.get("iou"),
                "iso_clean_iou": (iso_cal or {}).get("iou"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
