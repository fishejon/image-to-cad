"""Tapered square or round chair/stool leg (Z-up, foot at z=0)."""

from __future__ import annotations

from build123d import BuildPart, BuildSketch, Circle, Plane, Rectangle, loft

from furniture_cad.validate import assert_finite_number, check_solid


def tapered_leg(
    *,
    height: float,
    top_size: float,
    bot_size: float,
    section: str = "square",
) -> object:
    """
    Build a leg standing on the XY plane, tapering from bot_size at z=0 to top_size at z=height.

    section: "square" | "round". Sizes are full width (square) or diameter (round).
    """
    h = assert_finite_number("height", height, min_v=1.0, max_v=2000.0)
    top = assert_finite_number("top_size", top_size, min_v=1.0, max_v=200.0)
    bot = assert_finite_number("bot_size", bot_size, min_v=1.0, max_v=200.0)
    sec = str(section).lower().strip()
    if sec not in ("square", "round"):
        raise ValueError(f"section must be 'square' or 'round', got {section!r}")

    with BuildPart() as part:
        with BuildSketch(Plane.XY):
            if sec == "square":
                Rectangle(bot, bot)
            else:
                Circle(bot / 2.0)
        with BuildSketch(Plane.XY.offset(h)):
            if sec == "square":
                Rectangle(top, top)
            else:
                Circle(top / 2.0)
        loft()

    solid = part.part
    # Expect height exact; XY size ~ max(top, bot)
    xy = max(top, bot)
    check_solid(solid, expect_size=(xy, xy, h), tol=2.0, label="tapered_leg")
    return solid
