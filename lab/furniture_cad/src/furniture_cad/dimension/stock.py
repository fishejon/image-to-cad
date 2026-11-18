"""Stock thickness tables and snap rules (WP4)."""

from __future__ import annotations

from typing import Any

# S4S nominal finished thickness after typical planing loss from rough stock.
# Rough → finished (default planing loss baked in):
LUMBER_S4S_MM: dict[str, float] = {
    "4/4": 19.05,
    "5/4": 25.4,
    "6/4": 31.75,
    "8/4": 44.45,
}

SHEET_MM: tuple[float, ...] = (6.35, 12.7, 19.05)

# Combined snap table (mm)
STOCK_T_MM: tuple[float, ...] = tuple(
    sorted(
        set(
            list(LUMBER_S4S_MM.values())
            + list(SHEET_MM)
            + [9.0, 15.0, 18.0, 19.0, 22.0, 25.0, 32.0, 38.0, 50.0]
        )
    )
)

SNAP_TOL_MM = 1.5


def snap_stock(
    value_mm: float,
    *,
    table: tuple[float, ...] = STOCK_T_MM,
    tol_mm: float = SNAP_TOL_MM,
) -> dict[str, Any]:
    """Snap to stock when within ``tol_mm``; otherwise keep measured value.

    Returns ``{value_mm, snapped, source_tag, stock_name?}``.
    """
    v = float(value_mm)
    nearest = min(table, key=lambda t: abs(t - v))
    if abs(nearest - v) <= tol_mm:
        name = None
        for k, mm in LUMBER_S4S_MM.items():
            if abs(mm - nearest) < 1e-6:
                name = k
                break
        if name is None:
            for mm in SHEET_MM:
                if abs(mm - nearest) < 1e-6:
                    name = f"sheet_{mm:g}"
                    break
        return {
            "value_mm": nearest,
            "snapped": True,
            "source_tag": "snapped",
            "stock_name": name,
            "raw_mm": v,
        }
    return {
        "value_mm": v,
        "snapped": False,
        "source_tag": "cv",
        "stock_name": None,
        "raw_mm": v,
    }
