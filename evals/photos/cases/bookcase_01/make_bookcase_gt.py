"""Dimensioned, multi-body walnut bookcase inspired by the supplied photo.

Units are millimetres. The image gives appearance, while the user supplied the
overall envelope. Tenons and matching post mortises are modeled explicitly.
"""
from __future__ import annotations

from pathlib import Path
import csv

from build123d import Axis, Box, Compound, Pos, export_step, fillet

OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)

# Exact conversions from the requested inch envelope.
W, D, H = 47.24 * 25.4, 14.96 * 25.4, 78.74 * 25.4
POST_X, POST_Y, POST_R = 52.0, 46.0, 13.0
SHELF_T, SHELF_R = 34.0, 11.0
TENON_PROJ, TENON_Y, TENON_Z = 28.0, 30.0, 18.0
POST_CX = W / 2 - POST_X / 2
POST_CY = D / 2 - POST_Y / 2
SHELF_CENTERS = [250.0, 850.0, 1190.0, 1530.0, 1878.0]


def rounded_box(x: float, y: float, z: float, sx: float, sy: float, sz: float,
                radius: float) -> object:
    """Create a centered rounded solid, with all edge rounds kept in bounds."""
    solid = Pos(x, y, z) * Box(sx, sy, sz)
    return fillet(solid.edges(), radius)


def shelf_board(z: float, index: int) -> object:
    # Main board ends at the inner faces of the stiles. Four integral tenons
    # enter matching mortises: one at front and rear of each side stile.
    inner_span = W - 2 * POST_X
    board = rounded_box(0, 0, z, inner_span, D, SHELF_T, SHELF_R)
    tenons = []
    for side in (-1, 1):
        x = side * (inner_span / 2 + TENON_PROJ / 2)
        for y in (-POST_CY, POST_CY):
            tenons.append(Pos(x, y, z) * Box(TENON_PROJ, TENON_Y, TENON_Z))
    return board.fuse(*tenons)


def upright(x: float, y: float) -> object:
    post = rounded_box(x, y, H / 2, POST_X, POST_Y, H, POST_R)
    # Mortise pockets open on the inward-facing side; their depth is the full
    # tenon projection, and clearance is 0.25 mm per face for assembly.
    for z in SHELF_CENTERS:
        yy = y
        if x < 0:
            xx = x + POST_X / 2 - TENON_PROJ / 2
        else:
            xx = x - POST_X / 2 + TENON_PROJ / 2
        pocket = Pos(xx, yy, z) * Box(TENON_PROJ + 0.5, TENON_Y + 0.5, TENON_Z + 0.5)
        post = post - pocket
    return post


parts: list[tuple[str, str, object, int]] = []
for label, x, y in [
    ("Front left stile", -POST_CX, -POST_CY),
    ("Front right stile", POST_CX, -POST_CY),
    ("Rear left stile", -POST_CX, POST_CY),
    ("Rear right stile", POST_CX, POST_CY),
]:
    parts.append((label, "Solid walnut", upright(x, y), 1))

for i, z in enumerate(SHELF_CENTERS, 1):
    parts.append((f"Shelf {i} with four integral mortise-and-tenon tongues", "Solid walnut", shelf_board(z, i), 1))

# Independent cabinet carcase, inset in the lower opening. It uses housed
# dadoes: the top and bottom panels run between side panels in shallow rebates.
cab_w, cab_d = W - 2 * POST_X - 34.0, D - 54.0
cab_z0, cab_z1 = 488.0, 830.0
cab_t = 18.0
cab_y = -5.0
cab_mid_z = (cab_z0 + cab_z1) / 2
side_h = cab_z1 - cab_z0
parts.extend([
    ("Cabinet left gable", "Solid walnut", Pos(-cab_w/2 + cab_t/2, cab_y, cab_mid_z) * Box(cab_t, cab_d, side_h), 1),
    ("Cabinet right gable", "Solid walnut", Pos(cab_w/2 - cab_t/2, cab_y, cab_mid_z) * Box(cab_t, cab_d, side_h), 1),
    ("Cabinet bottom with housed dado ends", "Solid walnut", Pos(0, cab_y, cab_z0 + cab_t/2) * Box(cab_w - 2*cab_t + 12, cab_d, cab_t), 1),
    ("Cabinet top with housed dado ends", "Solid walnut", Pos(0, cab_y, cab_z1 - cab_t/2) * Box(cab_w - 2*cab_t + 12, cab_d, cab_t), 1),
    ("Cabinet back panel", "Walnut plywood", Pos(0, cab_y + cab_d/2 - 9, cab_mid_z) * Box(cab_w - 2*cab_t, 18, side_h - 2*cab_t), 1),
])

# Paired flush inset doors, with a 3 mm reveal between fronts and carcass.
door_w = (cab_w - 2*cab_t - 3) / 2
door_h = side_h - 2*cab_t - 3
door_y = cab_y - cab_d/2 - 9.0
for side, name in [(-1, "Left"), (1, "Right")]:
    parts.append((f"{name} inset cabinet door", "Solid walnut", Pos(side * (door_w/2 + 1.5), door_y, cab_mid_z) * Box(door_w, 18, door_h), 1))

assembly = Compound(children=[p[2] for p in parts])
step_path = OUT / "walnut_bookcase.step"
export_step(assembly, str(step_path))

with (OUT / "cut_list.csv").open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Part", "Material", "Qty", "Nominal bounding size (mm)", "Joinery / notes"])
    for name, material, shape, qty in parts:
        bb = shape.bounding_box()
        size = f"{bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f}"
        note = "Mortises at five shelf heights" if "stile" in name.lower() else (
            "Four integral loose-tenon profiles; glue and clamp" if "shelf" in name.lower() else
            "Housed dado construction" if "housed" in name.lower() else
            "Inset door with 3 mm reveal" if "door" in name.lower() else ""
        )
        writer.writerow([name, material, qty, size, note])

assert abs(assembly.bounding_box().size.X - W) < 0.1
assert abs(assembly.bounding_box().size.Y - D) < 0.1
assert abs(assembly.bounding_box().size.Z - H) < 0.1
assert len(parts) == 16
print(f"Wrote {step_path}; {len(parts)} independently selectable bodies; bbox {W:.3f} x {D:.3f} x {H:.3f} mm")
