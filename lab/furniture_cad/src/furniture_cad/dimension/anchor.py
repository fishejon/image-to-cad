"""Anchor observation dims to user-known size; snap thicknesses to stock."""

from __future__ import annotations

from typing import Any

# Common hardwood / sheet thicknesses (mm)
STOCK_T = (6.0, 9.0, 12.0, 15.0, 18.0, 19.0, 22.0, 25.0, 32.0, 38.0, 50.0)


def snap_stock(value_mm: float, table: tuple[float, ...] = STOCK_T) -> float:
    return min(table, key=lambda t: abs(t - float(value_mm)))


def apply_dims(
    observation: dict[str, Any],
    *,
    known_mm: dict[str, float] | None = None,
    default_t: float = 19.0,
) -> dict[str, Any]:
    """Return Dimension table: overall W/D/H anchored + snapped panel thickness."""
    known_mm = known_mm or {}
    obs_dims = observation.get("dims_mm") or {}

    def _get(key: str, alt: str) -> float | None:
        if known_mm.get(key):
            return float(known_mm[key])
        entry = obs_dims.get(alt) or obs_dims.get(key)
        if isinstance(entry, dict) and entry.get("v") is not None:
            return float(entry["v"])
        return None

    W = _get("w", "W")
    D = _get("d", "D")
    H = _get("h", "H")
    t = snap_stock(default_t)

    table = {
        "schema": "dimension.v1",
        "overall_mm": {
            "W": {"v": W, "src": "user" if known_mm.get("w") else "observation", "anchored": bool(W)},
            "D": {"v": D, "src": "user" if known_mm.get("d") else "observation", "anchored": bool(D)},
            "H": {"v": H, "src": "user" if known_mm.get("h") else "observation", "anchored": bool(H)},
        },
        "stock": {"t_panel": t, "t_back": snap_stock(6.0), "leg_section": snap_stock(38.0)},
        "ready": all(v is not None for v in (W, D, H)),
    }
    return table
