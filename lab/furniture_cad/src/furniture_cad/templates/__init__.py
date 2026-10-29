"""Part 3: category templates that compose blocks."""

from furniture_cad.templates.four_leg_chair import four_leg_chair
from furniture_cad.templates.stool import stool

TEMPLATE_FNS = {
    "four_leg_chair": four_leg_chair,
    "stool": stool,
}

__all__ = ["TEMPLATE_FNS", "four_leg_chair", "stool"]
