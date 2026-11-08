"""Discrepancy critic — structured verify feedback (Phase 1)."""

from __future__ import annotations

from typing import Any

from furniture_cad.geom_check import bbox_mm_from_solid, within_pct


def verify_against_dims(
    assembly: object,
    dims: dict[str, float],
    *,
    tol_pct: float = 0.03,
    features_expected: dict[str, int] | None = None,
    features_found: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Compare assembly AABB to anchored dims; emit discrepancy list."""
    bb = bbox_mm_from_solid(assembly)
    discrepancies: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {"bbox_mm": bb, "targets": dims}

    for axis, key in (("w", "W"), ("d", "D"), ("h", "H")):
        want = dims.get(axis) or dims.get(key.lower()) or dims.get(key)
        got = bb.get(axis)
        if want is None or got is None:
            discrepancies.append(
                {
                    "code": "missing_dim",
                    "axis": axis,
                    "severity": "warn",
                    "msg": f"No target for {axis}",
                }
            )
            continue
        ok = within_pct(float(got), float(want), tol_pct)
        err_pct = abs(float(got) - float(want)) / float(want) if want else 0.0
        metrics[f"{axis}_err_pct"] = round(err_pct, 4)
        if not ok:
            discrepancies.append(
                {
                    "code": "dim_miss",
                    "axis": axis,
                    "got": float(got),
                    "want": float(want),
                    "err_pct": round(err_pct, 4),
                    "severity": "error" if err_pct > 0.08 else "warn",
                    "stage": "verify",
                    "msg": f"{axis.upper()} {got:.1f} vs {want:.1f} ({err_pct:.1%})",
                }
            )

    features_expected = features_expected or {}
    features_found = features_found or {}
    for feat, want_n in features_expected.items():
        got_n = int(features_found.get(feat) or 0)
        if got_n != int(want_n):
            discrepancies.append(
                {
                    "code": "feature_count",
                    "feature": feat,
                    "got": got_n,
                    "want": int(want_n),
                    "severity": "error",
                    "stage": "verify",
                    "msg": f"{feat}: found {got_n}, expected {want_n}",
                }
            )

    return {
        "schema": "verify.v1",
        "ok": not any(d.get("severity") == "error" for d in discrepancies),
        "metrics": metrics,
        "discrepancies": discrepancies,
    }
