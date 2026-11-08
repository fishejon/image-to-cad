"""Freeform script sandbox policy (Phase 2) — no in-process exec of model code."""

from __future__ import annotations

from typing import Any

# Freeform build(script) is retired on the product path (D1). Keep policy explicit.
SANDBOX_POLICY = {
    "product_path": "build_ir",
    "freeform_script": "disabled",
    "requirements": [
        "subprocess or container only if re-enabled",
        "no network",
        "CPU/memory/time limits",
        "no absolute host path leakage in artifacts",
    ],
}


def assert_no_freeform(tool_name: str) -> None:
    if tool_name in ("build", "exec", "eval_script"):
        raise RuntimeError(
            f"{tool_name} disabled on product path — use build_ir (furniture_ir.v1). "
            f"Policy: {SANDBOX_POLICY['freeform_script']}"
        )


def sandbox_status() -> dict[str, Any]:
    return dict(SANDBOX_POLICY)
