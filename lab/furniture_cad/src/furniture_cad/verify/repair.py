"""Verify repair loop — discrepancy → IR patch → recompile (P4).

Only Perceive and Verify call a model. Model patch proposal is optional and
gated; deterministic patches always run first.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from furniture_cad.construct.compile import compile_ir
from furniture_cad.construct.patch import apply_ir_patches, patches_from_discrepancies
from furniture_cad.verify.critic import verify_against_dims


def propose_patches_model(
    ir: dict[str, Any],
    discrepancies: list[dict[str, Any]],
    *,
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[list[dict[str, Any]], float]:
    """Ask the model for IR patches only (JSON list). Returns (patches, spend)."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("FURNITURE_CAD_ANTHROPIC_KEY")
    if not key or not discrepancies:
        return [], 0.0
    if (os.environ.get("FURNITURE_CAD_VERIFY_MODEL_PATCH") or "").strip().lower() not in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return [], 0.0

    import anthropic
    from furniture_cad.tools.loop import _approx_cost_usd

    model = model or os.environ.get("FURNITURE_CAD_REPAIR_MODEL") or os.environ.get(
        "FURNITURE_CAD_MODEL", "claude-haiku-4-5"
    )
    client = anthropic.Anthropic(api_key=key)
    slim_ir = {
        "params": ir.get("params"),
        "layout": ir.get("layout"),
        "legs": ir.get("legs"),
        "carcass": {"form": (ir.get("carcass") or {}).get("form")},
    }
    resp = client.messages.create(
        model=model,
        max_tokens=512,
        system=(
            "Return ONLY a JSON array of IR patches. Allowed ops: "
            'set_param {key,value}, set_path {path,value}, set_drawer_cols {value}. '
            "Do not invent freeform scripts."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"IR snippet:\n{json.dumps(slim_ir)}\n\n"
                    f"Discrepancies:\n{json.dumps(discrepancies)}\n\n"
                    "Propose minimal patches."
                ),
            }
        ],
    )
    text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text")
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("patches") or []
    usage = getattr(resp, "usage", None)
    spend = _approx_cost_usd(
        input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
        output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
    )
    return list(data or []), float(spend)


def repair_loop(
    ir: dict[str, Any],
    *,
    targets_mm: dict[str, float],
    features_expected: dict[str, int] | None = None,
    max_rounds: int = 4,
    use_model_patches: bool = False,
) -> dict[str, Any]:
    """Compile → verify → patch until ok or max_rounds."""
    current = ir
    history: list[dict[str, Any]] = []
    spend = 0.0
    compiled = None
    verify = None

    for round_i in range(1, max_rounds + 1):
        compiled = compile_ir(current)
        verify = verify_against_dims(
            compiled["assembly"],
            targets_mm,
            features_expected=features_expected,
            features_found=compiled.get("features"),
        )
        entry = {
            "round": round_i,
            "ok": bool(verify.get("ok")),
            "discrepancies": verify.get("discrepancies") or [],
            "ir_hash": (compiled.get("report") or {}).get("ir_hash"),
        }
        if verify.get("ok"):
            history.append(entry)
            break

        patches = patches_from_discrepancies(
            verify.get("discrepancies") or [],
            targets_mm=targets_mm,
        )
        if use_model_patches:
            model_patches, cost = propose_patches_model(
                current, verify.get("discrepancies") or []
            )
            spend += cost
            patches = patches + model_patches

        entry["patches"] = patches
        history.append(entry)
        if not patches:
            break
        current = apply_ir_patches(current, patches)

    return {
        "schema": "repair.v1",
        "ok": bool(verify and verify.get("ok")),
        "rounds": len(history),
        "history": history,
        "ir": current,
        "compiled": compiled,
        "verify": verify,
        "spent_usd_approx": round(spend, 4),
    }
