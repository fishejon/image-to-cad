"""Parametric building blocks on top of build123d (R3 helper library)."""

from furniture_cad.blocks.back_mid_slat import back_mid_slat
from furniture_cad.blocks.back_panel import back_panel
from furniture_cad.blocks.carcass import carcass
from furniture_cad.blocks.curved_stile import curved_stile
from furniture_cad.blocks.open_etagere import open_etagere
from furniture_cad.blocks.panel import panel
from furniture_cad.blocks.rail import rail
from furniture_cad.blocks.rounded_cushion import rounded_cushion
from furniture_cad.blocks.seat_panel import seat_panel
from furniture_cad.blocks.shelf_board import shelf_board
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
    "panel": panel,
    "shelf_board": shelf_board,
    "open_etagere": open_etagere,
    "carcass": carcass,
}

# Doc strings the model sees via list_blocks / catalog
HELPER_DOCS = {
    "panel": "Flat panel (width × height × thickness).",
    "shelf_board": "Horizontal shelf board (length × depth × thickness).",
    "open_etagere": "Open 4-post MCM bookshelf; returns assembly+parts from W/D/H.",
    "carcass": "Open-front box carcass with shelves and back.",
    "tapered_leg": "Tapered leg from section params.",
    "rail": "Rectilinear rail/stretcher along +X.",
}

__all__ = [
    "BLOCK_FNS",
    "HELPER_DOCS",
    "tapered_leg",
    "seat_panel",
    "rail",
    "back_panel",
    "back_mid_slat",
    "winged_top_rail",
    "rounded_cushion",
    "curved_stile",
    "panel",
    "shelf_board",
    "open_etagere",
    "carcass",
]
