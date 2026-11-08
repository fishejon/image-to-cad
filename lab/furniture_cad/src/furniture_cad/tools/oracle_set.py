"""Oracle build scripts (hand-tuned solids + typed PartRecords).

These are the **answer key**, not the system under test. Use them to score
derived lists and silhouette IoU upper bounds. Baseline A is live model
output from a photo under the blind protocol — never these scripts.

Formerly named freeze_set / baseline A in Phase 1–2 docs (that labeling was wrong).
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
# Open 5-shelf MCM case — bottom shelf clear of sled feet; inward foot fins
# Named scalars (not tuple unpack) so Phase 4 rebuild --set W/H works
W = 720.0
D = 260.0
H = 1680.0
post_s = 32.0
shelf_t = 18.0
foot_h = 64.0
clearance = 48.0
overhang = 90.0
fin_w = 70.0
shelf_w = W
run_t = post_s + 8.0
post_h = H - foot_h
bay = (post_h - clearance - 5 * shelf_t) / 4.0
hx, hy = W / 2.0 - overhang - post_s / 2.0, D / 2.0 - 18.0

posts = []
for sx in (-1, 1):
    for sy in (-1, 1):
        posts.append(Pos(sx * hx, sy * hy, foot_h + post_h / 2.0) * Box(post_s, post_s, post_h))

shelves = []
for i in range(5):
    z = foot_h + clearance + shelf_t / 2.0 + i * (shelf_t + bay)
    shelves.append(Pos(0, 0, z) * Box(shelf_w, D, shelf_t))

# Sled runners + inward rectangular fins (triangle approx with Box-only API)
feet = [
    Pos(-hx, 0, foot_h / 2.0) * Box(run_t, D, foot_h),
    Pos(hx, 0, foot_h / 2.0) * Box(run_t, D, foot_h),
    Pos(-hx + run_t / 2.0 + fin_w / 2.0, 0, foot_h * 0.4) * Box(fin_w, D * 0.55, foot_h * 0.8),
    Pos(hx - run_t / 2.0 - fin_w / 2.0, 0, foot_h * 0.4) * Box(fin_w, D * 0.55, foot_h * 0.8),
]
assembly = Compound(children=posts + shelves + feet)
parts = [
    PartRecord(id='post', name='Vertical post', qty=4, material='walnut', thickness_mm=36, width_mm=36, length_mm=1530, grain='z', how_made='solid'),
    PartRecord(id='shelf', name='Shelf board', qty=5, material='walnut', thickness_mm=20, width_mm=280, length_mm=800, grain='x', how_made='solid'),
    PartRecord(id='rail_fb', name='Front/back under-shelf rail', qty=10, material='walnut', thickness_mm=20, width_mm=36, length_mm=620, grain='x', how_made='solid'),
    PartRecord(id='rail_side', name='Side under-shelf rail', qty=10, material='walnut', thickness_mm=20, width_mm=36, length_mm=200, grain='y', how_made='solid'),
    PartRecord(id='sled_foot', name='Sled foot (coved)', qty=2, material='walnut', thickness_mm=44, width_mm=70, length_mm=280, grain='y', how_made='solid', curved=True, blank_thickness_mm=48, blank_width_mm=80, blank_length_mm=300),
]
"""

SCRIPT_STOOL = r"""
params = dict(seat_w=320, seat_d=320, seat_t=28, seat_h=450, leg_top=35, leg_bot=28, stretcher=True)
result = stool(params)
assembly = result['assembly']
parts = [
    PartRecord(id='seat', name='Stool seat', qty=1, material='oak', thickness_mm=28, width_mm=320, length_mm=320, grain='x', how_made='solid'),
    PartRecord(id='leg', name='Leg', qty=4, material='oak', thickness_mm=35, width_mm=35, length_mm=450, grain='z', how_made='solid'),
    PartRecord(id='stretcher', name='Stretcher', qty=4, material='oak', thickness_mm=20, width_mm=30, length_mm=260, grain='x', how_made='solid'),
]
"""

SCRIPT_CASE_FIXTURE = r"""
# Drawer bookshelf SPEC fixture as solids (Phase 2 expansion piece — not case_01 photo)
W, D, H, t = 900.0, 300.0, 1800.0, 18.0
sides = [
    Pos(-W/2 + t/2, 0, H/2) * Box(t, D, H),
    Pos(W/2 - t/2, 0, H/2) * Box(t, D, H),
]
boards = []
for i, z in enumerate([t/2, H*0.2, H*0.4, H*0.6, H*0.8, H - t/2]):
    boards.append(Pos(0, 0, z) * Box(W - 2*t, D - 12, t))
back = Pos(0, -D/2 + 3, H/2) * Box(W - 2*t, 6, H - 2*t)
assembly = Compound(children=sides + boards + [back])
parts = [
    PartRecord(id='side_L', name='Left side', qty=1, material='oak', thickness_mm=18, width_mm=300, length_mm=1800, grain='z', how_made='solid'),
    PartRecord(id='side_R', name='Right side', qty=1, material='oak', thickness_mm=18, width_mm=300, length_mm=1800, grain='z', how_made='solid'),
    PartRecord(id='board', name='Shelf / top / bottom board', qty=6, material='oak', thickness_mm=18, width_mm=288, length_mm=876, grain='x', how_made='solid'),
    PartRecord(id='back', name='Back panel', qty=1, material='ply', thickness_mm=6, width_mm=880, length_mm=1740, grain='x', how_made='sheet'),
]
"""

ORACLE_PIECES: dict[str, dict[str, Any]] = {
    "chair_04": {
        "name": "chair_04",
        "script": SCRIPT_CHAIR_04,
        "expect_pieces": 10,  # 1+2+2+3+1+1
        "expect_types": 6,
        "photo": "evals/photos/chairs/chair_04.jpg",
    },
    "chair_02": {
        "name": "chair_02",
        "script": SCRIPT_CHAIR_02,
        "expect_pieces": 14,  # 1+2+2+4+3+1+1
        "expect_types": 7,
        "photo": "evals/photos/chairs/chair_02.jpg",
    },
    "case_01": {
        "name": "case_01",
        "script": SCRIPT_CASE_01,
        "expect_pieces": 31,  # 4+5+10+10+2
        "expect_types": 5,
        "photo": "evals/photos/cases/case_01.jpg",
        "hand_check": {
            "posts": 4,
            "shelves": 5,
            "sled_feet": 2,
            "note": "Matches case_01 photo inventory (open MCM); rails inferred from structure",
        },
    },
    "stool_01": {
        "name": "stool_01",
        "script": SCRIPT_STOOL,
        "expect_pieces": 9,
        "expect_types": 3,
        "photo": None,
    },
    "case_fixture": {
        "name": "case_fixture",
        "script": SCRIPT_CASE_FIXTURE,
        "expect_pieces": 9,
        "expect_types": 4,
        "photo": None,
        "hand_check": {"note": "Drawer bookshelf SPEC fixture solids — list gold alignment"},
    },
}


def oracle_tool_calls(piece_id: str) -> list[dict[str, Any]]:
    meta = ORACLE_PIECES[piece_id]
    return [
        {"tool": "build", "input": {"name": meta["name"], "script": meta["script"]}},
        {"tool": "lists", "input": {}},
    ]


# Back-compat aliases (remove after call sites migrate)
FREEZE_PIECES = ORACLE_PIECES
freeze_tool_calls = oracle_tool_calls
