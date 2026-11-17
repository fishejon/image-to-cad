"""Multi-body nightstand, authored in millimetres from the supplied image."""
from __future__ import annotations

import csv
from pathlib import Path

from build123d import Box, Color, Compound, Ellipse, Pos, Rot, extrude, export_step, fillet

OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)

# User dimensions, converted exactly from inches.
W, D, H = 23 * 25.4, 18 * 25.4, 23 * 25.4
LEG = 30.0
LEG_CX, LEG_CY = W / 2 - LEG / 2, D / 2 - LEG / 2
TOP_T = 25.4
LEG_H = H - TOP_T
TENON = 12.0
SHELF_Z = 152.0
DRAWER_FRONT_W, DRAWER_FRONT_H, DRAWER_FRONT_T = 440.0, 116.0, 20.0
DRAWER_FRONT_Z = 490.0
DRAWER_FRONT_Y = -LEG_CY - LEG / 2 + 25.4 + DRAWER_FRONT_T / 2
DRAWER_DEPTH, DRAWER_SIDE_T, DRAWER_BODY_H = 330.0, 15.0, 96.0
DRAWER_Y_FRONT = DRAWER_FRONT_Y + DRAWER_FRONT_T / 2 + 2.0
DRAWER_Y_BACK = DRAWER_Y_FRONT + DRAWER_DEPTH
DRAWER_MID_Y = (DRAWER_Y_FRONT + DRAWER_Y_BACK) / 2
DRAWER_SIDE_X, DRAWER_BODY_Z = 216.0, 490.0
SLIDE_X, SLIDE_W, SLIDE_H = 242.5, 48.0, 14.0


def rounded_box(x: float, y: float, z: float, sx: float, sy: float, sz: float,
                radius: float) -> object:
    return fillet((Pos(x, y, z) * Box(sx, sy, sz)).edges(), radius)


def oval_rail(x: float, y: float, z: float, width: float, height: float,
              length: float) -> object:
    """True elliptical-section rail, extruded along the drawer travel axis."""
    profile_extrusion = extrude(Ellipse(width / 2, height / 2), amount=length)
    return Pos(x, y + length / 2, z) * Rot(90, 0, 0) * profile_extrusion


def drawer_side(side: int) -> object:
    """Cherry drawer side with an oval channel for the walnut slide rail."""
    board = rounded_box(side * DRAWER_SIDE_X, DRAWER_MID_Y, DRAWER_BODY_Z,
                        DRAWER_SIDE_T, DRAWER_DEPTH, DRAWER_BODY_H, 1.8)
    channel = oval_rail(side * SLIDE_X, DRAWER_MID_Y, DRAWER_BODY_Z,
                        SLIDE_W + 0.4, SLIDE_H + 0.4,
                        DRAWER_DEPTH + 0.4)
    return board - channel


def rail_x(y: float, z: float, *, height: float, depth: float,
           tongue_depth: float = 18.0) -> object:
    """Cross rail spanning left-right, with integral tenons at both ends."""
    core_len = W - 2 * LEG
    core = rounded_box(0, y, z, core_len, depth, height, min(2.0, depth / 4, height / 4))
    tongues = [
        Pos(side * (core_len / 2 + TENON / 2), y, z)
        * Box(TENON, tongue_depth, min(TENON, height - 2))
        for side in (-1, 1)
    ]
    return core.fuse(*tongues)


def rail_y(x: float, z: float, *, height: float, width: float,
           tongue_width: float = 18.0, slide_groove: bool = False) -> object:
    """Side rail spanning front-back, with integral tenons at both ends."""
    core_len = D - 2 * LEG
    core = rounded_box(x, 0, z, width, core_len, height, min(2.0, width / 4, height / 4))
    tongues = [
        Pos(x, side * (core_len / 2 + TENON / 2), z)
        * Box(tongue_width, TENON, min(TENON, height - 2))
        for side in (-1, 1)
    ]
    rail = core.fuse(*tongues)
    if slide_groove:
        groove_x = x - (1 if x > 0 else -1) * (width / 2 - 5.0)
        groove = Pos(groove_x, 0, z - 4.0) * Box(10.4, core_len - 10.0, 18.4)
        rail = rail - groove
    return rail


# Cut matching mortises into each leg. The rails are staggered vertically so
# perpendicular tenons do not collide inside a post.
LEG_JOINTS: list[tuple[str, float, float, float, float, float]] = []
# (axis, center_x, center_y, z, mortise_width_across_post, mortise_height)
for y_side in (-1, 1):
    y = y_side * (LEG_CY - 9.0)
    LEG_JOINTS.extend([
        ("x", -LEG_CX, y, 131.0, 18.0, TENON),
        ("x", LEG_CX, y, 131.0, 18.0, TENON),
    ])
    # Rear upper stretcher joins the two rear legs.
for x_side in (-1, 1):
    LEG_JOINTS.append(("x", x_side * LEG_CX, LEG_CY - 9.0, 514.0, 18.0, TENON))


def leg(x: float, y: float) -> object:
    post = rounded_box(x, y, LEG_H / 2, LEG, LEG, LEG_H, 4.0)
    for axis, cx, cy, z, across, height in LEG_JOINTS:
        if abs(cx - x) > 1 or abs(cy - y) > 1:
            continue
        if axis == "x":
            # Inner-face mortise for a cross rail's end tenon.
            pocket_x = x - (1 if x > 0 else -1) * (LEG / 2 - TENON / 2)
            pocket = Pos(pocket_x, cy, z) * Box(TENON + 0.4, across + 0.4, height + 0.4)
        else:
            # Front/rear-face mortise for a side rail's end tenon.
            pocket_y = y - (1 if y > 0 else -1) * (LEG / 2 - TENON / 2)
            pocket = Pos(cx, pocket_y, z) * Box(across + 0.4, TENON + 0.4, height + 0.4)
        post = post - pocket
    # Each continuous oval walnut slide rail is housed halfway into the front
    # and rear legs. The socket is the same oval section as the rail itself.
    side = 1 if x > 0 else -1
    if abs(abs(x) - LEG_CX) < 1 and abs(abs(y) - LEG_CY) < 1:
        socket_center_y = y + (7.5 if y < 0 else -7.5)
        socket = oval_rail(side * SLIDE_X, socket_center_y, DRAWER_BODY_Z,
                            SLIDE_W + 0.4, SLIDE_H + 0.4, 15.4)
        post = post - socket
    return post


parts: list[tuple[str, str, object, int, str]] = []
for name, x, y in [
    ("Front left leg", -LEG_CX, -LEG_CY),
    ("Front right leg", LEG_CX, -LEG_CY),
    ("Rear left leg", -LEG_CX, LEG_CY),
    ("Rear right leg", LEG_CX, LEG_CY),
]:
    parts.append((name, "Cherry", leg(x, y), 1, "Blind mortises for rail tenons"))

parts.append(("Top panel", "Cherry", rounded_box(0, 0, H - TOP_T / 2, W, D, TOP_T, 6.0), 1,
              "Four-leg frame supports top"))

# Cherry aprons and stretchers frame the lower shelf and drawer opening.
parts.extend([
    ("Front lower apron", "Cherry", rail_x(-LEG_CY + 9.0, 131.0, height=18.0, depth=16.0), 1,
     "Integral end tenons into front legs"),
    ("Rear lower apron", "Cherry", rail_x(LEG_CY - 9.0, 131.0, height=18.0, depth=16.0), 1,
     "Integral end tenons into rear legs"),
    ("Rear upper apron", "Cherry", rail_x(LEG_CY - 9.0, 514.0, height=18.0, depth=18.0), 1,
     "Mortise-and-tenon into rear legs"),
])

# The side supports are each one continuous oval walnut rail, housed into the
# legs and let into a matching channel in the cherry drawer side. There is no
# rectangular side apron behind or alongside these oval rails.
for side, label in [(-1, "Left"), (1, "Right")]:
    parts.append((f"{label} drawer slide rail", "Black walnut",
                  oval_rail(side * SLIDE_X, 0.0, DRAWER_BODY_Z,
                            SLIDE_W, SLIDE_H, 2 * LEG_CY), 1,
                  "Continuous oval section; housed into both legs and let into drawer-side channel"))

# Lower shelf overhangs the shallow front and rear aprons by 3.4 mm.
shelf_width, shelf_depth, shelf_t = W - 2 * LEG, 432.0, 24.0
parts.append(("Open lower shelf", "Cherry",
              rounded_box(0, 0, SHELF_Z, shelf_width, shelf_depth, shelf_t, 5.0), 1,
              "Projects 3.4 mm beyond front and rear apron edges"))

# Single inset drawer. A separate face, two sides, rear, and bottom leave each
# woodworking component independently selectable and measurable.
parts.append(("Drawer front", "Cherry", rounded_box(0, DRAWER_FRONT_Y, DRAWER_FRONT_Z,
              DRAWER_FRONT_W, DRAWER_FRONT_T, DRAWER_FRONT_H, 4.5), 1,
              "Inset front; nominal 25.4 mm setback from frame front"))

parts.extend([
    ("Drawer left side", "Cherry", drawer_side(-1), 1,
     "Rabbeted to front and rear panels"),
    ("Drawer right side", "Cherry", drawer_side(1), 1,
     "Rabbeted to front and rear panels"),
    ("Drawer back", "Cherry", rounded_box(0, DRAWER_Y_BACK - 8.0, DRAWER_BODY_Z, 2 * DRAWER_SIDE_X, 16.0, DRAWER_BODY_H, 1.8), 1,
     "Captured between drawer sides"),
    ("Drawer bottom", "Cherry plywood", rounded_box(0, DRAWER_MID_Y, DRAWER_BODY_Z - DRAWER_BODY_H / 2 + 6.0, 2 * DRAWER_SIDE_X - 2 * DRAWER_SIDE_T, DRAWER_DEPTH - 16.0, 12.0, 1.0), 1,
     "Fits in shallow grooves in drawer sides and back"),
])

MATERIAL_COLORS = {
    "Cherry": Color(0.69, 0.37, 0.21),
    "Cherry plywood": Color(0.69, 0.37, 0.21),
    "Black walnut": Color(0.24, 0.15, 0.10),
}

for name, material, shape, _, _ in parts:
    shape.label = name
    shape.color = MATERIAL_COLORS[material]
assembly = Compound(children=[p[2] for p in parts], label="Cherry nightstand with walnut slide rails")
step_path = OUT / "cherry_nightstand_walnut_slides.step"
export_step(assembly, str(step_path))

with (OUT / "cut_list.csv").open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Part", "Material", "Qty", "Nominal bounding size (mm)", "Joinery / notes"])
    for name, material, shape, qty, note in parts:
        bb = shape.bounding_box()
        size = f"{bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f}"
        writer.writerow([name, material, qty, size, note])

assert len(parts) == 16, len(parts)
bb = assembly.bounding_box()
assert abs(bb.size.X - W) < 0.1, bb.size.X
assert abs(bb.size.Y - D) < 0.1, bb.size.Y
assert abs(bb.size.Z - H) < 0.1, bb.size.Z
print(f"Wrote {step_path}; {len(parts)} bodies; bbox {bb.size.X:.3f} x {bb.size.Y:.3f} x {bb.size.Z:.3f} mm")
