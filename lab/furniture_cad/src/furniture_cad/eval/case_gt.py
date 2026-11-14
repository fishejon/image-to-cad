"""Generic ground-truth cases: scaffold a case folder and score a run against it.

A case lives in ``evals/photos/cases/<id>/`` and is *ready* once it has a Fusion STEP
export and a filled ``cut_list.hand.json`` (``status`` other than ``template``).
``console_01`` is the reference layout; ``new-case`` scaffolds the same shape.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from furniture_cad.eval.board_feet import score_board_feet
from furniture_cad.eval.scorer import feature_recall, score_run

LAB = Path(__file__).resolve().parents[3]
ROOT = LAB.parent.parent
CASES_DIR = ROOT / "evals" / "photos" / "cases"
TEMPLATE_STATUS = "template"
MM_PER_IN = 25.4
CASE_FILES = ("known_sizes.json", "features.json", "views.json", "cut_list.hand.json", "README.md")
FEATURE_KEYS = ("drawer", "door", "shelf", "leg", "open_cubby", "pull")


def _w(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def scaffold_case(
    case_id: str,
    *,
    dims_in: tuple[float, float, float] | None = None,
    root: Path | None = None,
) -> Path:
    """Create ``<root>/<case_id>/`` with template files. Never overwrites."""
    if not case_id or "/" in case_id or case_id.startswith("."):
        raise ValueError(f"bad case id: {case_id!r}")
    out = (root or CASES_DIR) / case_id
    if out.exists():
        raise FileExistsError(f"{out} already exists")
    out.mkdir(parents=True)
    overall: dict[str, Any] = {}
    for axis, i in (("w", 0), ("d", 1), ("h", 2)):
        v_in = dims_in[i] if dims_in else None
        overall[axis] = {
            "v": round(v_in * MM_PER_IN, 1) if v_in else None,
            "src": "user",
            "in": v_in,
        }
    _w(
        out / "known_sizes.json",
        {
            "schema": "known_sizes.v1",
            "id": case_id,
            "units": "mm",
            "overall": overall,
            "anchor": "w",
            "notes": "Fill from the Fusion model (one overall size is enough; all three if known).",
        },
    )
    _w(
        out / "features.json",
        {
            "schema": "features.v1",
            "id": case_id,
            "counts": {k: None for k in FEATURE_KEYS},
            "attrs": {},
            "notes": "Counts a person can read off the photo. Replace null with integers.",
        },
    )
    _w(
        out / "views.json",
        {
            "schema": "views.v1",
            "id": case_id,
            "photos": [],
            "needed": ["front_clean"],
        },
    )
    _w(
        out / "cut_list.hand.json",
        {
            "schema": "hand_cut_list.v1",
            "id": case_id,
            "title": case_id,
            "date": date.today().isoformat(),
            "author": "",
            "dims_in": {"w": dims_in[0], "d": dims_in[1], "h": dims_in[2]} if dims_in else {},
            "dims_mm": {k: overall[k]["v"] for k in ("w", "d", "h")},
            "dims_from": "Fusion",
            "status": TEMPLATE_STATUS,
            "units_source": "inches",
            "notes": [],
            "parts": [],
            "stock_buy": [],
            "joinery": [],
        },
    )
    (out / "README.md").write_text(
        f"# {case_id} — ground truth (template)\n\n"
        "Drop in the Fusion export and fill the templates, then set `cut_list.hand.json` "
        '`status` to `"authoritative_hand_plan"`.\n\n'
        "| File | What to add |\n| --- | --- |\n"
        f"| `{case_id}.step` | Fusion STEP export (answer key geometry) |\n"
        "| `cut_list.hand.json` | one row per part type: `id`, `name`, `qty`, `finished_in` {t,w,l}, "
        "`thickness_mm`/`width_mm`/`length_mm` (finished), `blank_in` {t,w,l}, `stock`, `material`; "
        "plus `stock_buy` (per-stock `net_bf`) and `joinery` |\n"
        "| `known_sizes.json` | overall W/D/H |\n"
        "| `features.json` | feature counts |\n"
        "| `views.json` + photo | a clean straight-on front photo (jpg files are gitignored) |\n\n"
        "Part ids in the predicted cut list must match the hand ids for part matching to work.\n",
        encoding="utf-8",
    )
    return out


def step_path(case_dir: Path) -> Path:
    return case_dir / f"{case_dir.name}.step"


def is_ready(case_dir: Path) -> bool:
    hand = case_dir / "cut_list.hand.json"
    if not step_path(case_dir).is_file() or not hand.is_file():
        return False
    data = json.loads(hand.read_text(encoding="utf-8"))
    return data.get("status") != TEMPLATE_STATUS and bool(data.get("parts"))


def load_case(case_dir: Path) -> dict[str, Any]:
    def _j(name: str) -> dict[str, Any]:
        p = case_dir / name
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}

    return {
        "id": case_dir.name,
        "hand": _j("cut_list.hand.json"),
        "features": _j("features.json"),
        "known": _j("known_sizes.json"),
    }


def truth_parts(hand: dict[str, Any]) -> list[dict[str, Any]]:
    return [
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
        for p in hand.get("parts") or []
    ]


def score_case(
    case_dir: Path,
    *,
    parts_rows: list[dict[str, Any]],
    observed_counts: dict[str, int] | None = None,
    overall_pred_mm: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Score one run against a ready case: parts, features, dims, board feet."""
    if not is_ready(case_dir):
        raise ValueError(f"case {case_dir.name} is not ready (needs STEP + filled cut list)")
    c = load_case(case_dir)
    hand = c["hand"]
    truth_mm = {k: float(hand["dims_mm"][k]) for k in ("w", "d", "h")}
    truth_counts = {k: int(v) for k, v in ((c["features"].get("counts") or {}).items()) if v is not None}
    report = score_run(
        predicted_parts=parts_rows,
        truth_parts=truth_parts(hand),
        overall_pred_mm=overall_pred_mm,
        overall_truth_mm=truth_mm,
    )
    report["piece"] = c["id"]
    if observed_counts is not None and truth_counts:
        report["feature_recall"] = feature_recall(observed_counts, truth_counts)
    report["board_feet"] = score_board_feet(hand, parts_rows)
    return report
