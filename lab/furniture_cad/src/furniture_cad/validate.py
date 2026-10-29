"""Solid hygiene checks for blocks and assemblies."""

from __future__ import annotations

from typing import Any


def assert_finite_number(name: str, value: float, *, min_v: float | None = None, max_v: float | None = None) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    v = float(value)
    if not (v == v) or v in (float("inf"), float("-inf")):  # noqa: PLR0124 — NaN check
        raise ValueError(f"{name} must be finite, got {value!r}")
    if min_v is not None and v < min_v:
        raise ValueError(f"{name}={v} below minimum {min_v}")
    if max_v is not None and v > max_v:
        raise ValueError(f"{name}={v} above maximum {max_v}")
    return v


def solid_ok(solid: Any) -> bool:
    """Return True if OCC/build123d reports a valid non-empty solid."""
    if solid is None:
        return False
    try:
        if hasattr(solid, "is_valid") and callable(solid.is_valid):
            if not solid.is_valid():
                return False
        vol = float(solid.volume) if hasattr(solid, "volume") else 0.0
        if not (vol == vol) or vol <= 0:  # noqa: PLR0124
            return False
        return True
    except Exception:
        return False


def bbox_size(solid: Any) -> tuple[float, float, float]:
    """Axis-aligned size (dx, dy, dz) in model units (mm)."""
    bb = solid.bounding_box()
    return (
        float(bb.max.X - bb.min.X),
        float(bb.max.Y - bb.min.Y),
        float(bb.max.Z - bb.min.Z),
    )


def check_solid(
    solid: Any,
    *,
    expect_size: tuple[float, float, float] | None = None,
    tol: float = 1.5,
    label: str = "solid",
) -> None:
    if not solid_ok(solid):
        raise ValueError(f"{label} is not a valid solid with positive volume")
    if expect_size is not None:
        got = bbox_size(solid)
        for axis, (g, e) in enumerate(zip(got, expect_size, strict=True)):
            if abs(g - e) > tol:
                raise ValueError(
                    f"{label} bbox axis {axis}: got {g:.3f}, expected ~{e:.3f} (tol={tol})"
                )
