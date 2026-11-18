"""WP4 Dimension v2 — provenance, stock snap, CV measurements."""

from __future__ import annotations

from furniture_cad.dimension import apply_dims, snap_stock
from furniture_cad.dimension.stock import snap_stock as snap_detail


def test_snap_stock_within_tol() -> None:
    d = snap_detail(18.7)
    assert d["snapped"] is True
    assert d["source_tag"] == "snapped"
    assert abs(d["value_mm"] - 19.0) < 0.1 or abs(d["value_mm"] - 19.05) < 0.1


def test_snap_stock_keeps_measured_when_far() -> None:
    d = snap_detail(21.0)  # 1.95 from 19.05, 1.4 from 22 — may snap to 22
    # Far from all: use a weird value
    d2 = snap_detail(27.0)  # >1.5 from 25.4 and 31.75
    assert d2["snapped"] is False
    assert d2["source_tag"] == "cv"
    assert d2["value_mm"] == 27.0


def test_apply_dims_provenance_and_cv_drawer(tmp_path=None) -> None:
    obs = {
        "schema": "observation.v1",
        "class": "casegood.console",
        "counts": {"drawer": 2, "leg": 4},
        "dims_mm": {},
        "measurements": [
            {"id": "df0_h", "kind": "drawer_front_h", "value_mm": 128.0, "err_mm": 2.0, "source": "cv", "conf": 0.8},
            {"id": "top_t", "kind": "top_thickness", "value_mm": 22.0, "err_mm": 1.0, "source": "cv", "conf": 0.7},
        ],
    }
    dims = apply_dims(obs, known_mm={"w": 1193.8, "d": 304.8, "h": 762.0})
    assert dims["schema"] == "dimension.v2"
    assert dims["known_extra_mm"].get("drawer_front_h") == 128.0
    assert dims["stock"].get("t_top") == 22.0
    assert dims["provenance"]
    assert all(p.get("source") for p in dims["provenance"])
    assert dims["cv_source_share"] >= 0.5
    # Back-compat float snap
    assert snap_stock(18.7) in (19.0, 19.05)


def test_uncertain_measurement_becomes_ask() -> None:
    obs = {
        "class": "casegood.console",
        "counts": {"drawer": 2},
        "dims_mm": {},
        "measurements": [
            {"kind": "drawer_front_h", "value_mm": 100.0, "err_mm": 8.0, "source": "cv", "conf": 0.4},
        ],
    }
    dims = apply_dims(obs, known_mm={"w": 1000, "d": 300, "h": 700})
    assert "drawer_front_h" not in dims["known_extra_mm"]
    assert any(a.get("key") == "drawer_front" for a in dims["asks"])
