"""IR block library — Tier-1 casegoods + Tier-2 tables/benches."""

from furniture_cad.construct.blocks.casegood import (
    apron,
    divider,
    door,
    drawer_box,
    drawer_front,
    face_frame,
    leg_set,
    stretcher,
    top_panel,
    TIER1_BLOCKS,
)
from furniture_cad.construct.blocks.tier2 import (
    TIER2_BLOCKS,
    angled_leg,
    bench,
    stool,
    table,
)

__all__ = [
    "TIER1_BLOCKS",
    "TIER2_BLOCKS",
    "apron",
    "divider",
    "door",
    "drawer_box",
    "drawer_front",
    "face_frame",
    "leg_set",
    "stretcher",
    "top_panel",
    "angled_leg",
    "bench",
    "stool",
    "table",
]
