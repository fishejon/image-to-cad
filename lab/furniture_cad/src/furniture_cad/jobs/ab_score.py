"""Scorecard: Classic Create (B) vs oracle (O) vs live blind agent (A).

Oracle = hand-tuned scripts in tools/oracle_set.py — ceiling / answer key, not
the product. Baseline A is model output from a photo under the blind protocol.
"""

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
    oracle_parts = None
    # Prefer oracle export dirs; keep freeze path as alias during migration
    stl = None
    for stl_cand in (
        LAB / "out" / "oracle" / piece_id / f"{piece_id}.stl",
        LAB / "out" / "freeze" / piece_id / f"{piece_id}.stl",
    ):
        if stl_cand.is_file():
            stl = stl_cand
            break
    for cand in (
        LAB / "examples" / "parts" / f"{piece_id}_mcm.json",
        LAB / "examples" / "parts" / f"{piece_id}_curved.json",
        LAB / "out" / "oracle" / piece_id / f"{piece_id}.parts.json",
        LAB / "out" / "freeze" / piece_id / f"{piece_id}.parts.json",
    ):
        data = _load_json(cand)
        if data and data.get("parts"):
            oracle_parts = data["parts"]
            break

    o_qty = sum(int(p.get("qty") or 0) for p in (oracle_parts or []))
    o_types = len(oracle_parts or [])
    o_iou = None
    o_rating = None
    if measure_iou and photo and photo.is_file() and stl is not None:
        from furniture_cad.silhouette import rating_for_iou, silhouette_iou

        m = silhouette_iou(photo, stl)
        o_iou = m["iou"]
        o_rating = rating_for_iou(o_iou)
    b_iou = create.get("iou")
    beats = None
    if o_iou is not None and b_iou is not None:
        beats = o_iou > float(b_iou)

    # Live agent (A): only from blind scorecard rows, never from oracle scripts
    blind = score.get("blind_A") or score.get("agent_A") or {}
    a_iou = blind.get("iou")
    a_rating = blind.get("rating") or blind.get("ratingHint")
    a_status = blind.get("status") or ("recorded" if a_iou is not None else "not_measured")

    return {
        "id": piece_id,
        "B_classic_create": {
            "iou": b_iou,
            "rating": create.get("rating") or create.get("ratingHint"),
            "geometryOk": create.get("geometryOk"),
            "specPath": create.get("specPath"),
            "iou_quality": create.get("iou_quality") or score.get("iou_quality"),
        },
        "O_oracle": {
            "role": "answer_key_hand_tuned_script",
            "parts_path_found": oracle_parts is not None,
            "part_types": o_types,
            "piece_count": o_qty,
            "iou": o_iou,
            "rating": o_rating,
            "stl": str(stl) if stl is not None else None,
        },
        "A_live_blind": {
            "status": a_status,
            "iou": a_iou,
            "rating": a_rating,
            "notes": blind.get("notes")
            or (
                None
                if a_iou is not None
                else "No blind-protocol live run recorded yet (R0 / R1)."
            ),
        },
        # Deprecated keys — keep until callers migrate
        "baseline_B_create": None,
        "baseline_A_tooluse": None,
        "oracle_beats_create_iou": beats,
        "beats_create_iou": beats,
    }


def build_scorecard(ids: list[str], *, measure_iou: bool = True) -> dict[str, Any]:
    rows = [score_piece(i, measure_iou=measure_iou) for i in ids]
    # Fill deprecated nested keys for old consumers
    for r in rows:
        r["baseline_B_create"] = r["B_classic_create"]
        r["baseline_A_tooluse"] = {
            **{k: r["O_oracle"][k] for k in ("parts_path_found", "part_types", "piece_count", "iou", "rating", "stl")},
            "deprecated_label": "was_mislabeled_baseline_A_actually_oracle",
        }
    studio = [r for r in rows if r["O_oracle"].get("iou") is not None]
    close_plus = sum(1 for r in studio if (r["O_oracle"].get("iou") or 0) >= 0.55)
    beats = [r for r in rows if r.get("oracle_beats_create_iou") is True]
    qty_ok = sum(1 for r in rows if r["O_oracle"].get("piece_count"))
    a_measured = sum(1 for r in rows if r["A_live_blind"].get("iou") is not None)
    return {
        "schema": "furniture_cad.ab_score.v2",
        "note": (
            "O = oracle (hand scripts). A = live blind agent. "
            "Do not treat O as product gate. Product gate uses A vs B."
        ),
        "pieces": rows,
        "oracle_ceiling": {
            "exact_part_count_pieces_with_lists": qty_ok,
            "iou_close_plus_studio": f"{close_plus}/{len(studio)}" if studio else "0/0",
            "oracle_beats_create_count": len(beats),
        },
        "live_agent": {
            "pieces_with_blind_A_iou": a_measured,
            "total": len(rows),
        },
        "gate": {
            "note": "Legacy Phase-2 gate used oracle as A — superseded by R-phases. kept for history only.",
            "exact_part_count_pieces_with_lists": qty_ok,
            "iou_close_plus_studio": f"{close_plus}/{len(studio)}" if studio else "0/0",
            "beats_create_count": len(beats),
            "beats_create": len(beats) > 0 and close_plus >= 1,
            "passed": False,
            "passed_reason": "Oracle-vs-Create is not a product gate (R0 truth reset).",
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Scorecard: B (Create) vs O (oracle) vs A (live blind)")
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
