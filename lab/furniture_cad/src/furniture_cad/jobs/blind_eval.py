"""R4 blind eval harness: assemble B / O / A rows under the blind protocol.

Does not tune prompts. Live A runs are optional (--live) and expensive.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from furniture_cad.jobs.ab_score import score_piece

LAB = Path(__file__).resolve().parents[3]
ROOT = LAB.parent.parent
DEFAULT_SET = ["chair_04", "chair_02", "case_01"]


def _known_mm(piece_id: str) -> dict[str, float] | None:
    if piece_id.startswith("case_"):
        path = ROOT / "evals" / "photos" / "cases" / f"{piece_id}.json"
    elif piece_id.startswith("chair_"):
        path = ROOT / "evals" / "photos" / "chairs" / f"{piece_id}.json"
    else:
        return None
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    dims = (data.get("source") or {}).get("dims_mm") or {}
    if not dims:
        return None
    return {
        "w": float(dims.get("overall_w") or 0),
        "d": float(dims.get("overall_d") or 0),
        "h": float(dims.get("overall_h") or 0),
    }


def run_card(ids: list[str]) -> dict[str, Any]:
    rows = []
    for pid in ids:
        sp = score_piece(pid, measure_iou=True)
        known = _known_mm(pid)
        rows.append(
            {
                "id": pid,
                "known_mm": known,
                "B": sp["B_classic_create"],
                "O": sp["O_oracle"],
                "A": sp["A_live_blind"],
                "oracle_beats_B": sp.get("oracle_beats_create_iou"),
            }
        )
    a_measured = sum(1 for r in rows if r["A"].get("iou") is not None)
    return {
        "schema": "furniture_cad.blind_scorecard.v1",
        "protocol": "evals/photos/BLIND_PROTOCOL.md",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "pieces": rows,
        "summary": {
            "n": len(rows),
            "A_measured": a_measured,
            "note": (
                "A not measured under three-run blind protocol yet. "
                "O is oracle ceiling only. Decision uses available evidence."
            ),
        },
    }


def decision_from_card(card: dict[str, Any]) -> dict[str, Any]:
    """Recorded decision for R4 — not a full 10×3 blind yet."""
    return {
        "decision": "continue_fix_loop_and_helpers",
        "rationale": (
            "Infrastructure for eyes + helpers exists; live A likeness still Wrong on case_01 "
            "while dims can hit within 5%. Full 8–10 piece × 3-run blind pending more user photos/dims. "
            "Do not stop the shop-grade track; do not claim the product bar is met."
        ),
        "bar_met": False,
        "next": ["expand eval photos with user dims", "improve open_etagere likeness", "R5 honest UI"],
        "scorecard": "evals/photos/blind/SCORECARD_R4.json",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="R4 blind scorecard (B/O/A)")
    p.add_argument("--ids", nargs="*", default=DEFAULT_SET)
    p.add_argument("--out", type=Path, default=ROOT / "evals" / "photos" / "blind" / "SCORECARD_R4.json")
    p.add_argument("--decision", type=Path, default=ROOT / "evals" / "photos" / "blind" / "DECISION_R4.json")
    args = p.parse_args(argv)
    card = run_card(list(args.ids))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    dec = decision_from_card(card)
    args.decision.write_text(json.dumps(dec, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(args.out), "decision": dec["decision"], "bar_met": dec["bar_met"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
