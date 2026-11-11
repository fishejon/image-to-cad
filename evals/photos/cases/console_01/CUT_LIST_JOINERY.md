# Walnut Console: Cut List and Joinery Plan

Nov 8, 2026 · Jonny Fisher

A woodworker’s build plan for the console modeled in Fusion: **47″ W × 30″ H × 12″ D**, with two drawers under an open cubby. The curved sections are carved from thick blocks, not bent, and the joinery follows Japanese carpentry practice. Finished sizes come from the Fusion model. Blank sizes, allowances, and joint dimensions are a proposal — check against a full-size mockup before cutting walnut.

Machine-readable cut list: [`cut_list.hand.json`](cut_list.hand.json). Geometry answer key: [`console_01.step`](console_01.step).

## Conventions

Sizes are in inches, written **thickness × width × length**. Stock names are rough thickness: 4/4 = 1″, 5/4 = 1-1/4″, 12/4 = 3″, 16/4 = 4″. Blanks include about 1″ extra length, 1/2″ extra width, and enough thickness to flatten. Hidden drawer parts use a secondary wood (poplar or soft maple; paulownia is the traditional choice in tansu).

## 1. How the curved sections are made

| Curved feature | Method | Why |
| --- | --- | --- |
| End panels with the sweep into the underside (2) | Carve from a laminated block, grain running front to back | Face grain flows around the curve, with no spring-back or glue-line creep from bending |
| Tapered, flared legs (4) | Carve from a thick blank using the two-profile method | Matches how the CAD leg was built; grain follows the leg’s long axis |
| Drawer front outer corners (2) | Bandsaw from a flat 3/4″ board to a template, then scribe-fit | Curve lies in the plane of the board |
| Top plank and corner radius | Flat plank with ends cut at 6°, corner radius by hand after assembly | Keeps the leaning end line continuous |

The end blocks are the costly choice (~87% waste). Alternative: split each end into a flat leaning wall plank plus a smaller carved sweep block.

## 2. Cut list

| ID | Part | Qty | Finished (T × W × L) | Rough blank (T × W × L) | Stock |
| --- | --- | ---: | --- | --- | --- |
| T1 | Top plank | 1 | 7/8 × 12 × 47, ends 6° | 5/4 × 13 × 48, three boards glued | Walnut 5/4 |
| E1 | End block, carved (L/R mirrored) | 2 | Envelope 5-7/8 × 12 × 10-1/8, wall 7/8 | Laminated 6-1/2 × 12-1/2 × 11-1/2 | Walnut 16/4 |
| B1 | Bottom panel | 1 | 7/8 × 12 × 36-1/8 | 5/4 × 12-1/2 × 38, three boards glued | Walnut 5/4 |
| LT | Loose tongue, bottom panel joint | 2 | 3/8 × 1 × 11 | 4/4 × 1-1/2 × 12 | Hard maple |
| D1 | Divider shelf | 1 | 7/8 × 10-3/4 × 45, incl. dovetail tongues | 5/4 × 11-1/4 × 46, three boards glued | Walnut 5/4 |
| BK1 | Back panel | 1 | 1/2 × 9-1/2 × 45-1/2, incl. tongues | 4/4 × 10 × 46-1/2 | Walnut 4/4 |
| DF1 | Drawer front (L/R) | 2 | 3/4 × 5-1/16 × 22-1/16 | One board 4/4 × 5-3/4 × 46, cut in two | Walnut 4/4 |
| L1 | Leg (two mirrored pairs) | 4 | Envelope 3 × 9-1/4 × 20-1/2 (incl. 1″ tenon) | 16/4 × 6-1/2 × 23, diagonal layout | Walnut 16/4 |
| W1 | Wedge (kusabi) | 8 | 3/16 × 5/8 × 2-1/2 | Offcuts of contrasting hardwood | Scrap |
| DS1 | Drawer side | 4 | 1/2 × 3-3/4 × 10-5/8, incl. front tail | 4/4 × 4-1/4 × 11-1/2 | Poplar / soft maple 4/4 |
| DB1 | Drawer back | 2 | 1/2 × 3-1/4 × 18, cut to fit | 4/4 × 3-3/4 × 18-1/2 | Poplar / soft maple 4/4 |
| DBT1 | Drawer bottom, floating | 2 | 3/8 × 10 × 18, cut to fit | 4/4 × 10-1/2 × 18-1/2, resawn | Poplar / soft maple 4/4 |
| R1 | Drawer runner | 4 | 3/8 × 3/4 × 10-1/2 | 4/4 × 1 × 11 | Hard maple |

## 3. Stock to buy

| Stock | Parts | Net blank (bf) | With 25% |
| --- | --- | ---: | ---: |
| Walnut 5/4 | T1, B1, D1 | 14.1 | 17.7 |
| Walnut 4/4 | BK1, DF1 | 5.1 | 6.3 |
| Walnut 16/4 | E1, L1 | 33.9 | 42.4 |
| **Walnut total** | | **53.1** | **66.4** |
| Poplar / soft maple 4/4 | DS1, DB1, DBT1 | 5.3 | 6.6 |
| Hard maple 4/4 | LT, R1 | &lt;1 | one board |

## 4. Joinery schedule

| Joint | Parts | Technique | Notes |
| --- | --- | --- | --- |
| Top to ends | T1, E1 | Blind hozo | Three per end, 3/8 × 2 × 1/2, at 2″ / 6″ / 10″ from front |
| Bottom to ends | B1, E1 | Loose tongue (yatoi-zane) | 3/8 × 1″, 1/2″ into each, stopped 1″ from front/back |
| Divider to ends | D1, E1 | Stopped sliding dovetail (ari-otoshi) | 3/8 deep from back; glue front 2″ only |
| Back panel | BK1 | Floating tongue in groove (sane) | 3/8 deep; pin center only |
| Legs to bottom | L1, B1 | Through wedged tenon (hozo + kusabi) | Tenon 1-1/2 × 2-1/4 × 1″; two wedges/leg |
| Drawer front to sides | DF1, DS1 | Half-blind dovetail (ari) | 1/2 deep, narrow pins |
| Drawer back to sides | DB1, DS1 | Sliding dovetail | 3/8 deep |
| Drawer bottom | DBT1 | Floating in grooves | 3/8 groove; grain across width |
| Runners | R1 | Housed and glued | 1/4 deep, 1/8 proud, waxed |

## 5–8. Carving, assembly, vs Fusion, checks

See original plan notes: carve end blocks and legs from thick blanks; assemble carcass before drawers; back is 1/2″ floating (vs 7/8 in model); runners/tongues/wedges/joinery are build additions not in the solid Fusion body; mock up one end + one leg before cutting walnut.
