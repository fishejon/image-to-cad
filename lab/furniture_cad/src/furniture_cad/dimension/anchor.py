"""Dimension v2 — merge measured / user / snapped values with provenance."""

from __future__ import annotations

from typing import Any

from furniture_cad.dimension.stock import STOCK_T_MM, snap_stock as snap_stock_detail

# Back-compat: tests import snap_stock as returning a float
STOCK_T = STOCK_T_MM
CONFLICT_TOL = 0.03  # 3% — matches product gate


def snap_stock(value_mm: float, table: tuple[float, ...] = STOCK_T_MM) -> float:
    return float(snap_stock_detail(value_mm, table=table)["value_mm"])


def _obs_value(obs_dims: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        entry = obs_dims.get(key)
        if isinstance(entry, dict) and entry.get("v") is not None:
            return float(entry["v"])
        if isinstance(entry, (int, float)):
            return float(entry)
    return None


def _measurement_map(observation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index WP2 measurements by kind."""
    out: dict[str, dict[str, Any]] = {}
    for m in observation.get("measurements") or []:
        kind = str(m.get("kind") or "")
        if kind and m.get("value_mm") is not None:
            out[kind] = m
    return out


def _prov(
    *,
    key: str,
    value_mm: float | None,
    source_tag: str,
    err_mm: float | None = None,
    conf: float | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "value_mm": value_mm,
        "source": source_tag,
        "err_mm": err_mm,
        "conf": conf,
        "note": note,
    }


def apply_dims(
    observation: dict[str, Any],
    *,
    known_mm: dict[str, float] | None = None,
    default_t: float = 19.05,
    conflict_tol: float = CONFLICT_TOL,
) -> dict[str, Any]:
    """Return Dimension table: overall W/D/H + stock + provenance.

    Priority: user > ArUco/cv measurements > snapped > default.
    Values with relative error above 5% become asks instead of guesses.
    """
    known_mm = known_mm or {}
    obs_dims = observation.get("dims_mm") or {}
    measured = _measurement_map(observation)
    conflicts: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []

    obs_w = _obs_value(obs_dims, "W", "w")
    obs_d = _obs_value(obs_dims, "D", "d")
    obs_h = _obs_value(obs_dims, "H", "h")

    known_w = float(known_mm["w"]) if known_mm.get("w") else None
    known_d = float(known_mm["d"]) if known_mm.get("d") else None
    known_h = float(known_mm["h"]) if known_mm.get("h") else None

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
            src = "cv" if known_count != 1 else ("snapped" if known_key != anchor_axis else "cv")
            # scaled observation still tagged cv (derived from photo) unless only prior
            if known_count == 1 and scale is not None and known_key != anchor_axis:
                src = "cv"
            return obs, src, True
        return None, "guessed", False

    W, w_src, w_ok = _resolve("W", known_w, obs_w, "w")
    D, d_src, d_ok = _resolve("D", known_d, obs_d, "d")
    H, h_src, h_ok = _resolve("H", known_h, obs_h, "h")
    for letter, val, src in (("W", W, w_src), ("D", D, d_src), ("H", H, h_src)):
        provenance.append(_prov(key=f"overall_{letter}", value_mm=val, source_tag=src, conf=0.95 if src == "user" else 0.7))

    # Panel thickness: prefer measured top_thickness / body, else default → snap
    t_raw = None
    t_src = "default"
    if measured.get("top_thickness"):
        t_raw = float(measured["top_thickness"]["value_mm"])
        t_src = "cv"
    elif _obs_value(obs_dims, "t_panel", "t") is not None:
        t_raw = float(_obs_value(obs_dims, "t_panel", "t"))  # type: ignore[arg-type]
        t_src = "cv"
    else:
        t_raw = default_t
        t_src = "default"
    t_snap = snap_stock_detail(t_raw)
    t = float(t_snap["value_mm"])
    t_tag = t_snap["source_tag"] if t_snap["snapped"] else t_src
    if t_src == "default" and not t_snap["snapped"]:
        t_tag = "default"
    provenance.append(
        _prov(key="t_panel", value_mm=t, source_tag=t_tag, note=t_snap.get("stock_name"))
    )

    back_snap = snap_stock_detail(6.35)
    leg_raw = None
    if measured.get("leg_width_top"):
        leg_raw = float(measured["leg_width_top"]["value_mm"])
    else:
        leg_raw = float(_obs_value(obs_dims, "leg_section") or 38.0)
    leg_snap = snap_stock_detail(leg_raw)

    known_extra: dict[str, float] = {}
    for key, name in (("leg", "leg_h"), ("drawer_front", "drawer_front_h")):
        v = known_mm.get(key)
        if v is not None and float(v) > 0:
            known_extra[name] = float(v)
            provenance.append(_prov(key=name, value_mm=float(v), source_tag="user", conf=0.99))

    # Prefer CV drawer-front height from Measure when user did not supply one
    asks: list[dict[str, Any]] = []
    if "drawer_front_h" not in known_extra:
        df = measured.get("drawer_front_h")
        if df and df.get("value_mm"):
            err = float(df.get("err_mm") or 0)
            val = float(df["value_mm"])
            rel = err / max(val, 1.0)
            if rel > 0.05:
                asks.append(
                    {
                        "key": "drawer_front",
                        "q": f"Measured drawer front ≈ {val:.0f} mm (±{err:.0f}); confirm height?",
                        "default": val,
                    }
                )
                provenance.append(_prov(key="drawer_front_h", value_mm=val, source_tag="cv", err_mm=err, conf=0.4, note="uncertain"))
            else:
                known_extra["drawer_front_h"] = val
                provenance.append(_prov(key="drawer_front_h", value_mm=val, source_tag="cv", err_mm=err, conf=float(df.get("conf") or 0.7)))

    counts = observation.get("counts") or {}
    cls = str(observation.get("class") or "")
    if "leg_h" not in known_extra and cls.startswith("casegood"):
        asks.append(
            {
                "key": "leg",
                "q": "How tall are the legs, from the floor to the underside of the case (mm)?",
                "default": "prior: case underside at 35% of overall height",
            }
        )
    if "drawer_front_h" not in known_extra and int(counts.get("drawer") or 0) > 0:
        asks.append(
            {
                "key": "drawer_front",
                "q": "How tall is one drawer front (mm)?",
                "default": "prior: fixed fractions of the case",
            }
        )

    # Overhang / top_t from measure for Construct stock hints
    stock_extra: dict[str, Any] = {}
    if measured.get("top_overhang"):
        oh = float(measured["top_overhang"]["value_mm"])
        stock_extra["overhang"] = [oh, oh, 0.0]
        provenance.append(_prov(key="overhang", value_mm=oh, source_tag="cv"))
    if measured.get("top_thickness"):
        stock_extra["t_top"] = float(measured["top_thickness"]["value_mm"])

    cv_or_user = sum(1 for p in provenance if p.get("source") in ("cv", "user", "snapped") and p.get("value_mm") is not None)
    tagged = sum(1 for p in provenance if p.get("source") and p.get("value_mm") is not None)

    table = {
        "schema": "dimension.v2",
        "overall_mm": {
            "W": {"v": W, "src": w_src, "anchored": w_ok},
            "D": {"v": D, "src": d_src, "anchored": d_ok},
            "H": {"v": H, "src": h_src, "anchored": h_ok},
        },
        "stock": {
            "t_panel": t,
            "t_back": float(back_snap["value_mm"]),
            "t_top": stock_extra.get("t_top", t),
            "leg_section": float(leg_snap["value_mm"]),
            "overhang": stock_extra.get("overhang"),
        },
        "known_extra_mm": known_extra,
        "asks": asks,
        "conflicts": conflicts,
        "provenance": provenance,
        "cv_source_share": round(cv_or_user / max(1, tagged), 4),
        "scale_factor": round(scale, 6) if scale is not None and known_count == 1 else None,
        "ready": all(v is not None for v in (W, D, H)),
        "within_3pct": len(conflicts) == 0 and all(v is not None for v in (W, D, H)),
    }
    return table
