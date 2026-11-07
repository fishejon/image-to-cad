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


def score_piece(piece_id: str) -> dict[str, Any]:
    if piece_id.startswith("case_"):
        pack = ROOT / "evals" / "photos" / "cases"
    else:
        pack = ROOT / "evals" / "photos" / "chairs"
    score = _load_json(pack / f"{piece_id}.score.json") or {}
    create = score.get("create") or {}
    freeze_parts = None
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
    return {
        "id": piece_id,
        "baseline_B_create": {
            "iou": create.get("iou"),
            "rating": create.get("rating") or create.get("ratingHint"),
            "geometryOk": create.get("geometryOk"),
            "specPath": create.get("specPath"),
        },
        "baseline_A_tooluse": {
            "parts_path_found": freeze_parts is not None,
            "part_types": a_types,
            "piece_count": a_qty,
            "iou": None,
            "rating": None,
            "note": "IoU for A requires raster/silhouette path (Phase 2 open)",
        },
        "beats_create_iou": None,
    }


def build_scorecard(ids: list[str]) -> dict[str, Any]:
    rows = [score_piece(i) for i in ids]
    return {
        "schema": "furniture_cad.ab_score.v1",
        "pieces": rows,
        "gate": {
            "exact_part_count_4_of_5": None,
            "iou_close_plus_studio": None,
            "beats_create": False,
            "note": "Part-count exactness validated in freeze tests; IoU beat-Create still open until A silhouettes exist.",
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
