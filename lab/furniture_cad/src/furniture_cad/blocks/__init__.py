"""Part 2: parametric building blocks on top of build123d."""

from furniture_cad.blocks.back_mid_slat import back_mid_slat
from furniture_cad.blocks.back_panel import back_panel
from furniture_cad.blocks.curved_stile import curved_stile
from furniture_cad.blocks.rail import rail
from furniture_cad.blocks.rounded_cushion import rounded_cushion
from furniture_cad.blocks.seat_panel import seat_panel
from furniture_cad.blocks.tapered_leg import tapered_leg
from furniture_cad.blocks.winged_top_rail import winged_top_rail

BLOCK_FNS = {
    "tapered_leg": tapered_leg,
    "seat_panel": seat_panel,
    "rail": rail,
    "back_panel": back_panel,
    "back_mid_slat": back_mid_slat,
    "winged_top_rail": winged_top_rail,
    "rounded_cushion": rounded_cushion,
    "curved_stile": curved_stile,
}

__all__ = [
    "BLOCK_FNS",
    "tapered_leg",
    "seat_panel",
    "rail",
    "back_panel",
    "back_mid_slat",
    "winged_top_rail",
    "rounded_cushion",
    "curved_stile",
]
