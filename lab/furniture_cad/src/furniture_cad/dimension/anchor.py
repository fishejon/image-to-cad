"""Anchor observation dims to user-known size; snap thicknesses to stock."""

from __future__ import annotations

from typing import Any

# Common hardwood / sheet thicknesses (mm)
STOCK_T = (6.0, 9.0, 12.0, 15.0, 18.0, 19.0, 22.0, 25.0, 32.0, 38.0, 50.0)

CONFLICT_TOL = 0.03  # 3% — matches product gate


def snap_stock(value_mm: float, table: tuple[float, ...] = STOCK_T) -> float:
    return min(table, key=lambda t: abs(t - float(value_mm)))


def _obs_value(obs_dims: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        entry = obs_dims.get(key)
        if isinstance(entry, dict) and entry.get("v") is not None:
            return float(entry["v"])
        if isinstance(entry, (int, float)):
            return float(entry)
    return None


def apply_dims(
    observation: dict[str, Any],
    *,
    known_mm: dict[str, float] | None = None,
    default_t: float = 19.0,
    conflict_tol: float = CONFLICT_TOL,
) -> dict[str, Any]:
    """Return Dimension table: overall W/D/H anchored + snapped panel thickness.

    Rules:
    - User-known dims always win.
    - Observation dims that disagree with known by > conflict_tol are conflicts
      (user value kept).
    - If exactly one known overall dim is provided and observation has the other
      two, scale the observation axes by the known/obs ratio on that axis.
    - Panel thicknesses snap to STOCK_T.
    """
    known_mm = known_mm or {}
    obs_dims = observation.get("dims_mm") or {}
    conflicts: list[dict[str, Any]] = []

    obs_w = _obs_value(obs_dims, "W", "w")
    obs_d = _obs_value(obs_dims, "D", "d")
    obs_h = _obs_value(obs_dims, "H", "h")

    known_w = float(known_mm["w"]) if known_mm.get("w") else None
    known_d = float(known_mm["d"]) if known_mm.get("d") else None
    known_h = float(known_mm["h"]) if known_mm.get("h") else None

    # Single-anchor scale: one known + matching obs → scale remaining obs dims
    scale = None
    if known_w is not None and obs_w and abs(obs_w) > 1e-6:
        scale = known_w / obs_w
        anchor_axis = "w"
    elif known_d is not None and obs_d and abs(obs_d) > 1e-6:
        scale = known_d / obs_d
        anchor_axis = "d"
    elif known_h is not None and obs_h and abs(obs_h) > 1e-6:
        scale = known_h / obs_h
        anchor_axis = "h"
    else:
        anchor_axis = None

    known_count = sum(1 for v in (known_w, known_d, known_h) if v is not None)
    if known_count == 1 and scale is not None:
        if known_w is None and obs_w is not None:
            obs_w = obs_w * scale
        if known_d is None and obs_d is not None:
            obs_d = obs_d * scale
        if known_h is None and obs_h is not None:
            obs_h = obs_h * scale

    def _resolve(
        letter: str,
        known: float | None,
        obs: float | None,
        known_key: str,
    ) -> tuple[float | None, str, bool]:
        if known is not None:
            if obs is not None and abs(obs) > 1e-6:
                err = abs(known - obs) / abs(known)
                if err > conflict_tol:
                    conflicts.append(
                        {
                            "axis": letter,
                            "known": known,
                            "observation": obs,
                            "err": round(err, 4),
                            "resolution": "user_wins",
                        }
                    )
            return known, "user", True
        if obs is not None:
            src = "observation"
            if known_count == 1 and scale is not None and known_key != anchor_axis:
                src = "scaled"
            return obs, src, True
        return None, "missing", False

    W, w_src, w_ok = _resolve("W", known_w, obs_w, "w")
    D, d_src, d_ok = _resolve("D", known_d, obs_d, "d")
    H, h_src, h_ok = _resolve("H", known_h, obs_h, "h")

    t_raw = _obs_value(obs_dims, "t_panel", "t") or default_t
    t = snap_stock(t_raw)

    table = {
        "schema": "dimension.v1",
        "overall_mm": {
            "W": {"v": W, "src": w_src, "anchored": w_ok},
            "D": {"v": D, "src": d_src, "anchored": d_ok},
            "H": {"v": H, "src": h_src, "anchored": h_ok},
        },
        "stock": {
            "t_panel": t,
            "t_back": snap_stock(6.0),
            "leg_section": snap_stock(
                float(_obs_value(obs_dims, "leg_section") or 38.0)
            ),
        },
        "conflicts": conflicts,
        "scale_factor": round(scale, 6) if scale is not None and known_count == 1 else None,
        "ready": all(v is not None for v in (W, D, H)),
        "within_3pct": len(conflicts) == 0 and all(v is not None for v in (W, D, H)),
    }
    return table
