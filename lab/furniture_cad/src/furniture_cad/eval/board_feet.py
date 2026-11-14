"""Board-feet error vs a hand plan (P4 staged bar: <= 15%)."""

from __future__ import annotations

from typing import Any

from furniture_cad.lists import material_plan
from furniture_cad.parts import PartRecord


def hand_net_bf(hand: dict[str, Any]) -> dict[str, float | None]:
    """Truth board feet from a ``hand_cut_list.v1`` dict.

    * ``stated``: sum of the plan's own ``stock_buy[].net_bf`` (authoritative).
    * ``recomputed``: raw T x W x L / 144 over every ``blank_in`` x qty (informational;
      parts without a blank, such as wedges from offcuts, are skipped).
    """
    stated = sum(float(s.get("net_bf") or 0) for s in hand.get("stock_buy") or [])
    rec = 0.0
    for p in hand.get("parts") or []:
        b = p.get("blank_in")
        if b:
            rec += float(b["t"]) * float(b["w"]) * float(b["l"]) / 144.0 * int(p.get("qty") or 1)
    return {"stated": round(stated, 2) if stated else None, "recomputed": round(rec, 2) if rec else None}


def pred_net_bf(parts_rows: list[dict[str, Any]]) -> float:
    """Predicted board feet from pipeline ``parts.json`` rows, via the product's own
    ``material_plan`` (blanks fitted to real stock thickness)."""
    parts = [PartRecord.from_dict(r) for r in parts_rows]
    return round(float(material_plan(parts)["totals"]["blank_board_feet"]), 2)


def board_feet_error(pred_bf: float, truth_bf: float | None) -> float | None:
    if not truth_bf:
        return None
    return round(abs(pred_bf - truth_bf) / truth_bf, 4)


def score_board_feet(hand: dict[str, Any], parts_rows: list[dict[str, Any]], *, limit: float = 0.15) -> dict[str, Any]:
    truth = hand_net_bf(hand)
    pred = pred_net_bf(parts_rows)
    err_stated = board_feet_error(pred, truth["stated"])
    err_rec = board_feet_error(pred, truth["recomputed"])
    return {
        "pred_bf": pred,
        "truth_bf": truth,
        "err_vs_stated": err_stated,
        "err_vs_recomputed": err_rec,
        "limit": limit,
        "within_limit": bool(err_stated is not None and err_stated <= limit),
    }
