# P4 — Verify + console A0

Plan: [`docs/plans/product-plan-2026-11-10.md`](../../docs/plans/product-plan-2026-11-10.md)

## Checklist

- [x] IR patch ops + deterministic discrepancy → patch map (`construct/patch.py`)
- [x] Repair loop compile → verify → patch (≤4 rounds) (`verify/repair.py`)
- [x] Pipeline uses repair loop; optional model patches via `FURNITURE_CAD_VERIFY_MODEL_PATCH`
- [x] Three blind pipeline+vision runs on `console_01` (`python -m furniture_cad p4-a0`)
- [x] Construct derives IR from Perceive (generic casegood template) — `construct/from_observation.py`
- [ ] Camera-matched IoU ≥ 0.55 (studio) — **blocked**: D8 calibration still ~0.50 / untrusted
- [x] Blind human rating: **Close** (2026-11-14) — right features/layout/size; wrong case-to-leg massing; missing pill/wishbone silhouette
- [x] Board-feet scored in A0 harness (`eval/board_feet.py`)
- [ ] More Fusion GT (sideboard / bookcase / nightstand) — **blocked on Jonny**; empty case folders scaffolded

## Honest Construct baseline (offline, 2026-11-13)

Pipeline default no longer seeds `console_01.ir.json`. IR is built from Perceive counts + dims.

| Metric | Answer-key seed (golden) | From-observation (honest) | P4 target |
| --- | --- | --- | --- |
| Part recall | 1.0 | **0.77** | ≥ 0.70 |
| Cut-list size match | 0.46 | **0.15** | ≥ 0.50 |
| Board-ft err | ~0.47 | **~0.32** | ≤ 0.15 |
| Feature counts | drawer=2, leg=4 | same when Perceive supplies them | — |
| `blind_construct` | false | **true** | true |

Golden IR remains at `examples/ir/console_01.ir.json` for compile tests only (`seed_ir=`). Joinery blanks (LT/W1/R1) are IR-opt-in, not invented by the compiler.

## Proportions + metric split (2026-11-14, offline; live A0 not re-run)

- **Perceive now asks for two proportions** in the same vision call (no extra model call): `under_z_frac` (case underside / overall height) and `drawer_bank_frac` (drawer-front span / case height). Out-of-range or non-numeric values are dropped. Construct uses them when present and otherwise keeps the generic prior (`under_z` = 0.35 H, fixed drawer fractions). The IR notes say which one was used.
- **The prior is wrong for this console.** It puts the case underside at 267 mm; the real one is 495 mm (legs are 65% of height), so the prior-built case is 495 mm tall.
- **Drawer sizing rules:** with a measured bank, front height = bank span - 2 reveals, box height = front - 1 in; box depth = D - front - back - 1/8 in on every path.
- **Metric split** (`console_01/cut_list.hand.json` parts now carry `class`): `visible`, `construction` (drawer box parts), `joinery` (LT, W1, R1). The harness reports recall per class, `recall_excl_joinery`, and `dim_match_share` (share of individual dimensions within 5 mm / 3%).
- Truth proportions live in `console_01/proportions.json`; A0 reports `proportion_abs_err` per run.

Offline, with 2 drawers / 4 legs observed (not a photo score):

| | prior proportions | true proportions (upper bound) |
| --- | --- | --- |
| Recall, all parts | 0.77 | 0.77 |
| Recall excl. joinery | 1.00 | 1.00 |
| Dimension match share | 0.38 | 0.49 |
| Cut-list match (all 3 dims) | 0.15 | 0.15 |
| Board-ft error | 0.32 | 0.54 |

Reading it:
- Part recall is capped at 0.77 on any photo-derived IR: the three joinery parts are never invented.
- Proportions fix heights (DF1 front height within 0.2 mm) but part pass/fail needs all three dimensions. What still blocks parts: stock thickness defaults (19 / 6 / 12 mm vs the plan's 22.2 / 12.7 / 12.7), drawer box width, E1 height (3.7%), leg flare envelope, and B1.
- **Board-ft got worse with correct proportions.** The 0.32 was partly luck (a wrongly tall case inflated end blocks). With the right shape, the real gap shows: carved ends and legs are cut from much thicker blanks than their envelopes. Needs blank allowances for carved parts, not more tuning.
- Not measured yet: how well a vision model estimates the two proportions. Run `p4-a0 --runs 3` and read `mean_proportion_abs_err` (tolerance 0.05).

## Live proportions result and the change (2026-11-14)

Live A0 ×3 (PR #80): `mean_proportion_abs_err` 0.0804 vs 0.05 tolerance. Split by metric:

| Metric | Model returned (3 runs) | Truth | Mean abs error |
| --- | --- | --- | --- |
| `under_z_frac` | 0.65, 0.62, 0.58 | 0.65 | 0.033 (inside tolerance, but varies run to run) |
| `drawer_bank_frac` | 0.40, 0.35, 0.35 | 0.494 | 0.128 (always low) |

Asking for ratios makes the model estimate the denominator too (case height = overall height minus under_z). **Change:** Perceive now returns landmark rows (0–1000 down the image: top, floor, case bottom, top and bottom of the drawer fronts) and code computes the ratios (`proportions_from_landmarks`). Rows in an impossible order are dropped, which falls back to the prior instead of a wrong value. Same call count; direct ratios are no longer read.

Decision rule: re-run `python -m furniture_cad p4-a0 --runs 3`. If `mean_proportion_abs_err` is still over 0.05 on `drawer_bank_frac`, stop asking the model for geometry and ask the user for one drawer-front height (a known size), or derive under_z from the silhouette mask's width profile.

## Commands

```bash
cd lab/furniture_cad
pytest -q
python -m furniture_cad p4-a0 --runs 3
```

## Gate

**Partial.** Blind Construct is on; console part recall still clears 0.70 offline. Cut-list size match and board-ft need block fidelity + repair against the honest IR. Full P4 still needs IoU, human rating, and more Fusion GT.
