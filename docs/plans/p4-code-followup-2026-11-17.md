# P4 code follow-up — cut-list, D8, new forms

## Goals (ordered)

| # | Goal | Baseline | Target |
| --- | --- | --- | --- |
| 1 | Cut-list fidelity (credenza / sideboard / console) | cut-list match 0.17–0.45; board-ft err 0.25–0.54 | raise cut-list match; board-ft err ≤ 0.15 where honest |
| 2 | Strict D8 IoU | 0.758 front | ≥ 0.80 on `console_01_front_clean` |
| 3 | Nightstand + bookcase Construct | recall 0.67 / 0.14 | nightstand recall ≥ 0.85; bookcase emits stiles/shelves/cabinet |

## 1. Cut-list fidelity

Root causes from oracle assisted runs:
- Stock thickness prior `wall=19` vs truth 20–22 mm; top often thicker than wall.
- No top overhang → B1/E1/BK1/T1 depth/width off on sideboard/credenza.
- Drawer box sizing (slide gap, box depth) coarse vs hand list.
- Board-ft: predicted blanks thinner / smaller than hand `blank_in` + carved allowances.

Work:
1. Pass case stock hints from attrs / known sizes when present; prefer `wall` from median panel thickness priors per class.
2. Add `carcass.top.overhang` + `top.t` from observation attrs / proportions when available; default small overhang for flat-top casegoods.
3. Tighten drawer bank geometry (front width = bay − 2·reveal; box depth from D − front − back − clearance).
4. Improve blank allowances for shaped legs / carved ends in `lists_with_allowances` / material plan.
5. Re-score `case-run --assist` on console, credenza, sideboard.

## 2. D8 ≥ 0.80

Already at 0.76 after letterbox + triangle + hole-fill. Next:
1. Finer translation refine + optional scale ±2% search around AABB fit.
2. Soft morphological close on photo mask (shadow toes).
3. Prefer `console_01_front_clean`; refresh `CALIBRATION.json`.
4. Gate note: P4 0.55 already cleared; 0.80 is the strict D8 bar.

## 3. Nightstand + bookcase forms

**Nightstand** (closer): single drawer + low shelf + 4 legs + oval slide rails as attrs.
- Layout: one bay, drawer bank rows=1 align=top, open below, shelf near bottom.
- Legs: square/rounded, height = H − top_t; rails optional as construction parts.
- Emit SR1 if `joinery_cue` mentions slide rails (simplified box rails OK).

**Bookcase** (harder): organic continuous frame.
- Phase A: rectilinear approximation — 4 stiles (ST1), N shelves (SH1), mid cabinet bay with DR1×2.
- Phase B (optional): filleted stile/rail massing for silhouette.
- Drive shelf count from features; cabinet band from proportions if present.

## Execution order

1. Cut-list fixes (shared IR/compile) → biggest product win on ready cases.
2. D8 refine.
3. Nightstand Construct.
4. Bookcase Construct (rectilinear).
5. Tests + `P4_VERIFY` + PR.

## Out of scope

- New Fusion exports / studio photo shoots.
- Full organic CNC frame matching the bookcase photo.
