"""Baseline A (tool-use / freeze) vs baseline B (Careful Create) scorecard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# …/lab/furniture_cad/src/furniture_cad/jobs/ab_score.py
LAB = Path(__file__).resolve().parents[3]  # lab/furniture_cad
ROOT = LAB.parent.parent  # repo root


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def score_piece(piece_id: str, *, measure_iou: bool = True) -> dict[str, Any]:
    if piece_id.startswith("case_") and piece_id != "case_fixture":
        pack = ROOT / "evals" / "photos" / "cases"
        photo = pack / f"{piece_id}.jpg"
    elif piece_id.startswith("chair_"):
        pack = ROOT / "evals" / "photos" / "chairs"
        photo = pack / f"{piece_id}.jpg"
    else:
        pack = None
        photo = None
    score = _load_json(pack / f"{piece_id}.score.json") if pack else {}
    score = score or {}
    create = score.get("create") or {}
    freeze_parts = None
    stl = LAB / "out" / "freeze" / piece_id / f"{piece_id}.stl"
    for cand in (
        LAB / "examples" / "parts" / f"{piece_id}_mcm.json",
        LAB / "examples" / "parts" / f"{piece_id}_curved.json",
        LAB / "out" / "freeze" / piece_id / f"{piece_id}.parts.json",
    ):
        data = _load_json(cand)
        if data and data.get("parts"):
            freeze_parts = data["parts"]
            break

    a_qty = sum(int(p.get("qty") or 0) for p in (freeze_parts or []))
    a_types = len(freeze_parts or [])
    a_iou = None
    a_rating = None
    if measure_iou and photo and photo.is_file() and stl.is_file():
        from furniture_cad.silhouette import rating_for_iou, silhouette_iou

        m = silhouette_iou(photo, stl)
        a_iou = m["iou"]
        a_rating = rating_for_iou(a_iou)
    b_iou = create.get("iou")
    beats = None
    if a_iou is not None and b_iou is not None:
        beats = a_iou > float(b_iou)
    return {
        "id": piece_id,
        "baseline_B_create": {
            "iou": b_iou,
            "rating": create.get("rating") or create.get("ratingHint"),
            "geometryOk": create.get("geometryOk"),
            "specPath": create.get("specPath"),
        },
        "baseline_A_tooluse": {
            "parts_path_found": freeze_parts is not None,
            "part_types": a_types,
            "piece_count": a_qty,
            "iou": a_iou,
            "rating": a_rating,
            "stl": str(stl) if stl.is_file() else None,
        },
        "beats_create_iou": beats,
    }


def build_scorecard(ids: list[str], *, measure_iou: bool = True) -> dict[str, Any]:
    rows = [score_piece(i, measure_iou=measure_iou) for i in ids]
    studio = [r for r in rows if r["baseline_A_tooluse"].get("iou") is not None]
    close_plus = sum(1 for r in studio if (r["baseline_A_tooluse"].get("iou") or 0) >= 0.55)
    beats = [r for r in rows if r.get("beats_create_iou") is True]
    qty_ok = sum(1 for r in rows if r["baseline_A_tooluse"].get("piece_count"))
    return {
        "schema": "furniture_cad.ab_score.v1",
        "pieces": rows,
        "gate": {
            "exact_part_count_pieces_with_lists": qty_ok,
            "iou_close_plus_studio": f"{close_plus}/{len(studio)}" if studio else "0/0",
            "beats_create_count": len(beats),
            "beats_create": len(beats) > 0 and close_plus >= 1,
            "passed": close_plus >= 1 and len(beats) >= 1 and qty_ok >= 4,
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="A/B scorecard Create vs tool-use freeze")
    p.add_argument("--ids", nargs="*", default=["chair_04", "chair_02", "case_01"])
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)
    card = build_scorecard(list(args.ids))
    text = json.dumps(card, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
