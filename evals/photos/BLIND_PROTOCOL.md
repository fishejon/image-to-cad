# Blind evaluation protocol

**Status:** R0 — locked for scoring. Used by R1 smoke runs and the R4 gate.

## Blind rules

1. **Inputs allowed:** the photo(s), one known dimension, and a materials brief. Nothing else.
2. **Forbidden:** hand-written build scripts, tuned per-piece parameters, oracle (`oracle_set`) scripts as the system under test, and prompt edits between the three runs of a piece.
3. **Operator:** the person scoring does not edit model outputs. Prompt or helper changes happen *between* eval rounds and are logged with a version id.
4. **Reporting:** mean and worst across three runs per piece — never the best run alone.
5. **Regression:** after R4, changes to prompt / tools / helpers re-run the eval; fail if mean IoU (or agreed metric) drops by the agreed amount.

## Labels

| Id | Source |
| --- | --- |
| **B** | Classic Create (`runAI` / Careful Create) on the same photo |
| **O** | Oracle STL from `furniture_cad.tools.oracle_set` (answer key only) |
| **A** | Live Messages tool-use loop with photo image blocks |

## Metrics per run

Record one row per run (see [`scorecard.schema.json`](scorecard.schema.json)):

- Valid solid (yes/no) and rounds used
- Key dimensions vs known size / catalog (error %)
- Part count vs hand count from the photo
- Silhouette IoU per view (`iou_quality: trusted` for studio; `untrusted_room_background` for room photos)
- Cut-list error vs hand/catalog build (size % and qty)
- Cost (USD), tokens, wall time
- Human rating: Match / Close / Wrong with reasons

## Procedure

1. Check out the prompt + helper version under test; record `git` SHA and contract version.
2. For each piece in the eval set, run the live job **three times** with identical inputs.
3. Do not peek at oracle scripts or prior best specs while scoring.
4. Write results under `evals/photos/<pack>/<id>.score.json` → `blind_A.runs[]` and aggregate `blind_A`.
5. Produce the scorecard table (mean / worst) and a short failure review.

## R4 decision table

| Result | Action |
| --- | --- |
| A meets the product bar | Proceed to R5 |
| A misses likeness; lists + dims sound | Fix loop/helpers ~2 weeks, re-run |
| A misses likeness and dims after fixes | Add image-to-mesh reference prior, re-run |
| A cannot beat B | Stop shop-grade track; revisit approach |
