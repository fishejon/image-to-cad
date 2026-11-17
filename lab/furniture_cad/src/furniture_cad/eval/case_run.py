"""Run the generic Construct on any ready ground-truth case, with oracle feature counts.

Perceive is bypassed on purpose: the counts come from ``features.json``, so the report isolates
how well Construct + compile generalise to the piece (sizes, parts, shape) from how well a model
reads a photo. ``--assist`` also passes the user-known leg / drawer-front heights from
``proportions.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from furniture_cad.construct import compile_ir, construct_ir_from_observation
from furniture_cad.dimension import apply_dims
from furniture_cad.eval.case_gt import CASES_DIR, is_ready, load_case, score_case, step_path

MM = ("w", "d", "h")


def _j(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def oracle_observation(case_dir: Path) -> dict[str, Any]:
    c = load_case(case_dir)
    feats = c["features"]
    attrs = feats.get("attrs") or {}
    counts = {k: int(v) for k, v in (feats.get("counts") or {}).items() if v is not None}
    counts.setdefault("end_block_carved", 0)
    cls = attrs.get("class") or f"casegood.{case_dir.name.rsplit('_', 1)[0]}"
    props = _j(case_dir / "proportions.json").get("proportions") or {}
    return {
        "schema": "observation.v1",
        "class": cls,
        "components": [],
        "dims_mm": {},
        "counts": counts,
        "end_form": attrs.get("end_form") or "flat",
        "leg_style": attrs.get("leg_style") or "square",
        "drawer_layout": attrs.get("drawer_layout") or "",
        "door_style": attrs.get("door_style") or "",
        "layout_facing": attrs.get("layout_facing") or "",
        "proportions": props,
        "unknowns": [],
        "meta": {"perceive": "oracle_counts"},
    }


def run_case(case_id: str, *, assist: bool = False, root: Path | None = None) -> dict[str, Any]:
    case_dir = (root or CASES_DIR) / case_id
    if not is_ready(case_dir):
        raise ValueError(f"case {case_id} is not ready (needs STEP + filled cut list)")
    c = load_case(case_dir)
    known = {k: float(c["known"]["overall"][k]["v"]) for k in MM}
    if assist:
        known.update({k: float(v) for k, v in (_j(case_dir / "proportions.json").get("known_mm_assist") or {}).items()})
    obs = oracle_observation(case_dir)
    dims = apply_dims(obs, known_mm=known)
    ir = construct_ir_from_observation(obs, dims)
    res = compile_ir(ir)
    rows = [p.to_dict() for p in res["parts"]]
    report = score_case(case_dir, parts_rows=rows, observed_counts=obs["counts"])
    built = {k: int(v) for k, v in (res.get("features") or {}).items()}
    truth = {k: v for k, v in obs["counts"].items() if k != "end_block_carved"}
    report["features_built_vs_truth"] = {k: {"built": built.get(k, 0), "truth": v} for k, v in truth.items()}
    report["feature_count_match"] = round(
        sum(1 for k, v in truth.items() if built.get(k, 0) == v) / max(1, len(truth)), 4
    )
    report["case"] = case_id
    report["assisted"] = assist
    report["oracle_counts"] = True
    report["asks"] = dims.get("asks") or []
    report["shape_iou"] = {"front": None, "side": None}
    step = step_path(case_dir)
    if step.is_file():
        from build123d import import_step

        from furniture_cad.eval.silhouette import silhouette_iou

        gt = import_step(str(step))
        report["shape_iou"]["front"] = silhouette_iou(gt, res["assembly"], view="front")["iou"]
        report["shape_iou"]["side"] = silhouette_iou(gt, res["assembly"], view="side", mirror_ok=True)["iou"]
    return report


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    p = report["parts"]
    return {
        "case": report["case"],
        "assisted": report["assisted"],
        "part_recall": p["recall"],
        "recall_excl_joinery": p["recall_excl_joinery"],
        "dim_match_share": p["dim_match_share"],
        "cut_list_match_share": p["cut_list_match_share"],
        "board_feet_err": (report.get("board_feet") or {}).get("err_vs_stated"),
        "feature_count_match": report["feature_count_match"],
        "shape_iou_front": report["shape_iou"]["front"],
        "shape_iou_side": report["shape_iou"]["side"],
    }
