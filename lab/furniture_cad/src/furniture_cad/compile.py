"""Compile a template + params JSON into an assembly and export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from furniture_cad.catalog import TEMPLATE_CATALOG, list_templates
from furniture_cad.export import export_assembly
from furniture_cad.templates import TEMPLATE_FNS

ROOT = Path(__file__).resolve().parents[2]


def compile_template(template: str, params: dict[str, Any]) -> dict[str, Any]:
    if template not in TEMPLATE_FNS:
        raise KeyError(f"Unknown template {template!r}. Known: {list_templates()}")
    if template not in TEMPLATE_CATALOG:
        raise KeyError(f"Template {template!r} missing from catalog")
    return TEMPLATE_FNS[template](params)


def load_params(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("params file must be a JSON object")
    # Allow { "template": "...", "params": { ... } } or flat params
    if "params" in data and isinstance(data["params"], dict):
        return data["params"]
    return {k: v for k, v in data.items() if k not in ("template", "schemaVersion", "notes")}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Compile furniture_cad template → STEP/STL")
    p.add_argument("--template", required=True, choices=list_templates())
    p.add_argument("--params", type=Path, required=True, help="JSON params file")
    p.add_argument("--out", type=Path, default=None, help="Output directory")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    params = load_params(args.params)
    result = compile_template(args.template, params)
    out = args.out or (ROOT / "out" / args.template)
    written = export_assembly(result, out, name=args.template)
    meta = {
        "template": result["template"],
        "params": result["params"],
        "part_ids": sorted(result["parts"]),
        "exports": {k: str(v) for k, v in written.items()},
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
