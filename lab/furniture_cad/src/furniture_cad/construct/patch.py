"""Deterministic IR patches (D11) — no freeform script repair on product path."""

from __future__ import annotations

import copy
from typing import Any


def apply_ir_patches(ir: dict[str, Any], patches: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply a list of patch ops to a furniture_ir.v2 document.

    Supported ops:
      {"op": "set_param", "key": "W", "value": 1193.8}
      {"op": "set_path", "path": "legs.count", "value": 4}
      {"op": "set_drawer_cols", "value": 2}
    """
    out = copy.deepcopy(ir)
    for raw in patches or []:
        op = str(raw.get("op") or "")
        if op == "set_param":
            key = str(raw["key"])
            params = dict(out.get("params") or {})
            params[key] = raw["value"]
            out["params"] = params
        elif op == "set_path":
            _set_dotted(out, str(raw["path"]), raw["value"])
        elif op == "set_drawer_cols":
            layout = dict(out.get("layout") or {})
            children = list(layout.get("children") or [])
            for i, ch in enumerate(children):
                if isinstance(ch, dict) and ch.get("kind") == "drawer_bank":
                    children[i] = {**ch, "cols": int(raw["value"])}
            layout["children"] = children
            out["layout"] = layout
        # unknown ops ignored (logged by repair history)
    return out


def _set_dotted(root: dict[str, Any], path: str, value: Any) -> None:
    parts = [p for p in path.split(".") if p]
    if not parts:
        return
    cur: Any = root
    for p in parts[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[parts[-1]] = value


def patches_from_discrepancies(
    discrepancies: list[dict[str, Any]],
    *,
    targets_mm: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Map verify discrepancies → IR patches (deterministic rules)."""
    targets_mm = targets_mm or {}
    patches: list[dict[str, Any]] = []
    for d in discrepancies or []:
        code = d.get("code")
        if code == "dim_miss":
            axis = str(d.get("axis") or "").lower()
            want = d.get("want")
            if want is None and axis in targets_mm:
                want = targets_mm[axis]
            if axis in ("w", "d", "h") and want is not None:
                patches.append({"op": "set_param", "key": axis.upper(), "value": float(want)})
        elif code == "feature_count":
            feat = str(d.get("feature") or "")
            want_n = int(d.get("want") or 0)
            if feat == "drawer" and want_n > 0:
                patches.append({"op": "set_drawer_cols", "value": want_n})
            elif feat == "leg" and want_n > 0:
                patches.append({"op": "set_path", "path": "legs.count", "value": want_n})
    # de-dupe by (op,key/path)
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for p in patches:
        sig = f"{p.get('op')}:{p.get('key') or p.get('path') or p.get('value')}"
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append(p)
    return uniq
