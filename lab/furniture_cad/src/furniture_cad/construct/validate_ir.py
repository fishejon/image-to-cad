"""Validate furniture_ir.v1 / v2 documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMAS = Path(__file__).resolve().parents[3] / "contracts" / "schemas"


def validate_ir(ir: dict[str, Any]) -> dict[str, Any]:
    schema = ir.get("schema")
    if schema == "furniture_ir.v2":
        return _validate_v2(ir)
    if schema == "furniture_ir.v1":
        return {"ok": True, "schema": schema, "warnings": ["v1 is legacy; prefer furniture_ir.v2"]}
    return {"ok": False, "errors": [f"unsupported schema {schema!r}"]}


def _validate_v2(ir: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if ir.get("units") != "mm":
        errors.append("units must be mm")
    params = ir.get("params") or {}
    for k in ("W", "H", "D"):
        if k not in params or float(params[k]) <= 0:
            errors.append(f"params.{k} required and > 0")
    carcass = ir.get("carcass") or {}
    form = carcass.get("form")
    if form not in ("swept_shell", "box"):
        errors.append("carcass.form must be swept_shell or box")
    layout = ir.get("layout") or {}
    if not layout.get("children"):
        warnings.append("layout.children empty")
    # Reject unknown top-level keys beyond schema
    allowed = {"schema", "units", "params", "material", "carcass", "layout", "legs", "notes"}
    unknown = sorted(set(ir) - allowed)
    if unknown:
        errors.append(f"unknown fields: {unknown}")
    return {"ok": not errors, "schema": "furniture_ir.v2", "errors": errors, "warnings": warnings}


def load_schema_doc(version: str = "v2") -> dict[str, Any]:
    path = SCHEMAS / f"furniture_ir.{version}.json"
    return json.loads(path.read_text(encoding="utf-8"))
