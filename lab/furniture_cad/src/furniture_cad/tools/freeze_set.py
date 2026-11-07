"""Phase 1 freeze-set build scripts (chair_04, chair_02, case_01).

Offline path for the solids + lists gate — same helper API the model uses in build().
"""

from __future__ import annotations

from typing import Any

# Scripts are plain strings executed inside tool_build's allowlisted namespace.

SCRIPT_CHAIR_04 = r"""
params = dict(
    seat_w=457, seat_d=470, seat_t=28, seat_h=495,
    leg_top=32, leg_bot=24, leg_section='square',
    stretcher=True, stretcher_section_w=20, stretcher_section_h=30, stretcher_z=160,
    back=True, back_style='panel', back_w=420, back_h=300, back_t=14,
    cushion=True, cushion_h=40, cushion_corner_r=28,
    rake_y=40, stile_curve_y=12,
)
result = four_leg_chair(params)
assembly = result['assembly']
parts = [
    PartRecord(id='seat', name='Seat panel', qty=1, material='oak', thickness_mm=28, width_mm=457, length_mm=470, grain='x', how_made='solid'),
    PartRecord(id='front_leg', name='Front leg', qty=2, material='oak', thickness_mm=32, width_mm=32, length_mm=495, grain='z', how_made='solid'),
    PartRecord(id='rear_stile', name='Rear stile', qty=2, material='oak', thickness_mm=32, width_mm=32, length_mm=795, grain='z', how_made='solid', curved=True, blank_thickness_mm=40, blank_width_mm=48, blank_length_mm=850),
    PartRecord(id='stretcher', name='Stretcher', qty=3, material='oak', thickness_mm=20, width_mm=30, length_mm=400, grain='x', how_made='solid'),
    PartRecord(id='back', name='Back panel', qty=1, material='oak', thickness_mm=14, width_mm=420, length_mm=300, grain='z', how_made='panel'),
    PartRecord(id='cushion', name='Seat cushion', qty=1, material='upholstery', thickness_mm=40, width_mm=440, length_mm=450, grain='unknown', how_made='upholstery'),
]
"""

SCRIPT_CHAIR_02 = r"""
params = dict(
    seat_w=445, seat_d=420, seat_t=19, seat_h=445,
    leg_top=25, leg_bot=22, leg_section='square',
    stretcher=True, stretcher_section_w=18, stretcher_section_h=28,
    stretcher_z_side=229, stretcher_z_rear=317, stretcher_front=True,
    back=True, back_style='mcm_rails', back_w=400, back_h=356, back_t=16,
    winged_width=533, winged_end_h=140, winged_mid_h=55, winged_thickness=16,
    mid_slat_h=44, mid_slat_z_from_seat=102,
    curve_sag=48, rake_y=72, stile_curve_y=28,
    cushion=False,
)
result = four_leg_chair(params)
assembly = result['assembly']
parts = [
    PartRecord(id='seat', name='Seat panel', qty=1, material='oak', thickness_mm=19, width_mm=445, length_mm=420, grain='x', how_made='solid'),
    PartRecord(id='front_leg', name='Front leg', qty=2, material='oak', thickness_mm=25, width_mm=25, length_mm=445, grain='z', how_made='solid'),
    PartRecord(id='rear_stile', name='Rear stile (curved rake)', qty=2, material='oak', thickness_mm=25, width_mm=25, length_mm=720, grain='z', how_made='sweep', curved=True, blank_thickness_mm=42, blank_width_mm=55, blank_length_mm=780, notes='foot-aft / seat-forward / rake-aft'),
    PartRecord(id='apron', name='Seat apron', qty=4, material='oak', thickness_mm=22, width_mm=38, length_mm=400, grain='x', how_made='solid'),
    PartRecord(id='stretcher', name='Stretcher', qty=3, material='oak', thickness_mm=18, width_mm=28, length_mm=380, grain='x', how_made='solid'),
    PartRecord(id='mid_slat', name='Back mid slat', qty=1, material='oak', thickness_mm=16, width_mm=44, length_mm=400, grain='x', how_made='solid', curved=True, blank_thickness_mm=20, blank_width_mm=50, blank_length_mm=430),
    PartRecord(id='top_rail', name='Winged top rail', qty=1, material='oak', thickness_mm=16, width_mm=140, length_mm=533, grain='x', how_made='solid', curved=True, blank_thickness_mm=22, blank_width_mm=150, blank_length_mm=560),
]
"""

SCRIPT_CASE_01 = r"""
# Open 5-shelf MCM case — rectilinear proxy solids (knife-edge / cove approximated)
W, D, H = 900.0, 300.0, 1800.0
post_s, shelf_t, foot_h = 40.0, 22.0, 80.0
shelf_w = W
inner_h = H - foot_h
bay = (inner_h - 5 * shelf_t) / 4.0
hx, hy = W / 2.0 - 60.0, D / 2.0 - 20.0

posts = []
for sx in (-1, 1):
    for sy in (-1, 1):
        posts.append(Pos(sx * hx, sy * hy, foot_h + inner_h / 2.0) * Box(post_s, post_s, inner_h))

shelves = []
for i in range(5):
    z = foot_h + shelf_t / 2.0 + i * (shelf_t + bay)
    shelves.append(Pos(0, 0, z) * Box(shelf_w, D, shelf_t))

feet = [
    Pos(-hx, 0, foot_h / 2.0) * Box(post_s, D, foot_h),
    Pos(hx, 0, foot_h / 2.0) * Box(post_s, D, foot_h),
]
assembly = Compound(children=posts + shelves + feet)
parts = [
    PartRecord(id='post', name='Vertical post', qty=4, material='walnut', thickness_mm=40, width_mm=40, length_mm=1720, grain='z', how_made='solid'),
    PartRecord(id='shelf', name='Shelf board', qty=5, material='walnut', thickness_mm=22, width_mm=300, length_mm=900, grain='x', how_made='solid'),
    PartRecord(id='rail_fb', name='Front/back under-shelf rail', qty=10, material='walnut', thickness_mm=22, width_mm=40, length_mm=780, grain='x', how_made='solid'),
    PartRecord(id='rail_side', name='Side under-shelf rail', qty=10, material='walnut', thickness_mm=22, width_mm=40, length_mm=220, grain='y', how_made='solid'),
    PartRecord(id='sled_foot', name='Sled foot (coved)', qty=2, material='walnut', thickness_mm=40, width_mm=80, length_mm=300, grain='y', how_made='solid', curved=True, blank_thickness_mm=45, blank_width_mm=90, blank_length_mm=320),
]
"""

FREEZE_PIECES: dict[str, dict[str, Any]] = {
    "chair_04": {
        "name": "chair_04",
        "script": SCRIPT_CHAIR_04,
        "expect_pieces": 10,  # 1+2+2+3+1+1
        "expect_types": 6,
    },
    "chair_02": {
        "name": "chair_02",
        "script": SCRIPT_CHAIR_02,
        "expect_pieces": 14,  # 1+2+2+4+3+1+1
        "expect_types": 7,
    },
    "case_01": {
        "name": "case_01",
        "script": SCRIPT_CASE_01,
        "expect_pieces": 31,  # 4+5+10+10+2
        "expect_types": 5,
        "hand_check": {
            "posts": 4,
            "shelves": 5,
            "sled_feet": 2,
            "note": "Matches case_01 photo inventory (open MCM); rails inferred from structure",
        },
    },
}


def freeze_tool_calls(piece_id: str) -> list[dict[str, Any]]:
    meta = FREEZE_PIECES[piece_id]
    return [
        {"tool": "build", "input": {"name": meta["name"], "script": meta["script"]}},
        {"tool": "lists", "input": {}},
    ]
