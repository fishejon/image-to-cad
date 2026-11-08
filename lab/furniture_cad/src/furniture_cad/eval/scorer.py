"""Phase 0 scorer: part matching, size error, feature recall (plan §5.3)."""

from __future__ import annotations

from typing import Any


def _size_tuple(p: dict[str, Any]) -> tuple[float, float, float]:
    if "finished_mm" in p and p["finished_mm"]:
        t, w, L = [float(x) for x in p["finished_mm"][:3]]
        return t, w, L
    return (
        float(p.get("thickness_mm") or 0),
        float(p.get("width_mm") or 0),
        float(p.get("length_mm") or 0),
    )


def _type_key(p: dict[str, Any]) -> str:
    return str(p.get("type") or p.get("id") or p.get("name") or "part").lower().split("_")[0]


def _match_cost(pred: dict[str, Any], truth: dict[str, Any]) -> float:
    """Lower is better. Type mismatch heavily penalized; size uses sorted dims."""
    if _type_key(pred) != _type_key(truth) and str(pred.get("id")) != str(truth.get("id")):
        # allow id equality even if type label differs
        if str(pred.get("id") or "") != str(truth.get("id") or ""):
            return 1e6
    ps = sorted(_size_tuple(pred))
    ts = sorted(_size_tuple(truth))
    err = 0.0
    for a, b in zip(ps, ts):
        if b <= 0:
            continue
        err += max(abs(a - b), abs(a - b) / b * 100.0)  # mix mm and % — used only for ranking
    qty_pen = abs(int(pred.get("qty") or 1) - int(truth.get("qty") or 1)) * 50.0
    return err + qty_pen


def hungarian_match(pred: list[dict[str, Any]], truth: list[dict[str, Any]]) -> list[tuple[int, int, float]]:
    """Greedy Hungarian-ish assignment (exact scipy optional). Returns (pi, ti, cost)."""
    n, m = len(pred), len(truth)
    used_p, used_t = set(), set()
    pairs: list[tuple[int, int, float]] = []
    # Build all candidate edges
    edges: list[tuple[float, int, int]] = []
    for i in range(n):
        for j in range(m):
            edges.append((_match_cost(pred[i], truth[j]), i, j))
    edges.sort()
    for cost, i, j in edges:
        if cost >= 1e6:
            break
        if i in used_p or j in used_t:
            continue
        used_p.add(i)
        used_t.add(j)
        pairs.append((i, j, cost))
    return pairs


def size_errors(pred: dict[str, Any], truth: dict[str, Any]) -> dict[str, float]:
    ps = sorted(_size_tuple(pred))
    ts = sorted(_size_tuple(truth))
    abs_errs = [abs(a - b) for a, b in zip(ps, ts)]
    pct_errs = [abs(a - b) / b if b else 0.0 for a, b in zip(ps, ts)]
    return {
        "max_abs_mm": max(abs_errs) if abs_errs else 0.0,
        "max_pct": max(pct_errs) if pct_errs else 0.0,
        "within_5mm_or_3pct": bool(
            abs_errs and all((a <= 5.0) or (p <= 0.03) for a, p in zip(abs_errs, pct_errs))
        ),
    }


def score_parts(
    predicted: list[dict[str, Any]],
    ground_truth: list[dict[str, Any]],
) -> dict[str, Any]:
    """Part precision/recall and cut-list size match share."""
    pairs = hungarian_match(predicted, ground_truth)
    matched = len(pairs)
    prec = matched / len(predicted) if predicted else 0.0
    rec = matched / len(ground_truth) if ground_truth else 0.0
    size_ok = 0
    errs: list[dict[str, Any]] = []
    for i, j, _ in pairs:
        se = size_errors(predicted[i], ground_truth[j])
        errs.append({"pred": predicted[i].get("id"), "truth": ground_truth[j].get("id"), **se})
        if se["within_5mm_or_3pct"]:
            size_ok += 1
    cut_match = size_ok / len(ground_truth) if ground_truth else 0.0
    return {
        "matched": matched,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "cut_list_match_share": round(cut_match, 4),
        "pairs": [{"pred_i": i, "truth_j": j, "cost": c} for i, j, c in pairs],
        "size_errors": errs,
    }


def feature_recall(
    predicted_counts: dict[str, int],
    truth_counts: dict[str, int],
) -> dict[str, Any]:
    keys = sorted(set(predicted_counts) | set(truth_counts))
    per: dict[str, Any] = {}
    hits = 0
    for k in keys:
        p, t = int(predicted_counts.get(k) or 0), int(truth_counts.get(k) or 0)
        ok = p == t
        per[k] = {"pred": p, "truth": t, "ok": ok}
        if t > 0 and ok:
            hits += 1
    denom = sum(1 for k in keys if int(truth_counts.get(k) or 0) > 0) or 1
    return {"recall": round(hits / denom, 4), "per_feature": per}


def score_run(
    *,
    predicted_parts: list[dict[str, Any]],
    truth_parts: list[dict[str, Any]],
    predicted_features: dict[str, int] | None = None,
    truth_features: dict[str, int] | None = None,
    overall_pred_mm: dict[str, float] | None = None,
    overall_truth_mm: dict[str, float] | None = None,
    iou: float | None = None,
    cost_usd: float | None = None,
    wall_s: float | None = None,
) -> dict[str, Any]:
    parts = score_parts(predicted_parts, truth_parts)
    feats = None
    if predicted_features is not None and truth_features is not None:
        feats = feature_recall(predicted_features, truth_features)
    dim_ok = None
    dim_detail = {}
    if overall_pred_mm and overall_truth_mm:
        dim_ok = True
        for k in ("w", "d", "h"):
            if k not in overall_truth_mm or not overall_truth_mm[k]:
                continue
            got, want = float(overall_pred_mm.get(k) or 0), float(overall_truth_mm[k])
            err = abs(got - want) / want
            dim_detail[k] = {"got": got, "want": want, "err": round(err, 4)}
            if err > 0.03:
                dim_ok = False
    return {
        "schema": "furniture_cad.score_run.v1",
        "parts": parts,
        "features": feats,
        "overall_dims_within_3pct": dim_ok,
        "overall_dims": dim_detail,
        "iou": iou,
        "cost_usd": cost_usd,
        "wall_s": wall_s,
    }
