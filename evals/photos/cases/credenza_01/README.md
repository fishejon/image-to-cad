# credenza_01 — Fusion ground truth

**Dims:** 1350 × 450 × 700 mm → **53.15 × 17.72 × 27.56 in** (W × D × H).

Real Fusion export (`Credenza.step`): left sliding door, two stacked drawers over an open cubby, four tapered splayed legs, rounded outer shell corners.

| File | Status |
| --- | --- |
| `credenza_01.step` | Fusion STEP (21 solids) |
| `cut_list.hand.json` | `fusion_step_parts` — finished sizes from solid AABBs; blanks are proposals |
| `known_sizes.json` | filled from STEP bbox |
| `features.json` | filled from photo + STEP |
| `proportions.json` | leg 200, drawer front 95 |
| `credenza_01_iso.jpg` | three-quarter room photo (gitignored) |

Still needed for a full console-class GT: clean front photo + promote cut list to `authoritative_hand_plan` with real blank/joinery allowances.
