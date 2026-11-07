"""Load the frozen tool contract (contracts/tools.v1.json)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]  # lab/furniture_cad
CONTRACT_PATH = ROOT / "contracts" / "tools.v1.json"


@lru_cache(maxsize=1)
def load_contract() -> dict[str, Any]:
    if not CONTRACT_PATH.is_file():
        raise FileNotFoundError(f"tool contract missing: {CONTRACT_PATH}")
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def tool_names() -> list[str]:
    return [t["name"] for t in load_contract()["tools"]]


def anthropic_tools() -> list[dict[str, Any]]:
    """Messages API `tools` array."""
    out = []
    for t in load_contract()["tools"]:
        out.append(
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["input_schema"],
            }
        )
    return out


def limits() -> dict[str, Any]:
    return dict(load_contract().get("limits") or {})
