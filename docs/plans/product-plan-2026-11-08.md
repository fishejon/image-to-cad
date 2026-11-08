# Image-to-CAD: Product Plan and Technical Spec

> **Status: ACTIVE.** Supersedes day-to-day sequencing in [`photo-to-model-recovery.md`](photo-to-model-recovery.md) (R0–R7 remain historical).  
> Prepared for Jonny, November 8, 2026.

## Bottom line

Infrastructure is real; proof is not. Accuracy is mostly not a modeling-kernel problem. It is:

1. Broken measuring stick (IoU with scale search, brightness masks, front-only orthographic).
2. Loop cannot see (flat silhouettes hide drawers / interiors).
3. Perception and construction fused in one LLM path.
4. Two engines (browser SPEC + Python build123d) neither complete.

**Direction:** stop feature creep; build a real eval harness; wedge on **casegoods**; split pipeline into **Intake → Perceive → Dimension → Construct → Verify → Derive → Review**.

## Locked decisions (2026-11-08)

| Id | Decision | Choice |
| --- | --- | --- |
| **D1** | Single canonical engine | **IR + build123d compiler**; browser = viewer / param editor. JS box-CSG optional preview only |
| **D2** | Wedge | **Casegoods first** (console, sideboard, bookcase, cabinet); chairs later |
| **D3** | Capture guidance | **Allowed** — straight-on + scale / user-known dimension |
| **D4** | Fusion ground truth | Console modeled by Jonny (STEP + hand cut list); then ~1 piece / 1–2 weeks |
| **D5** | Eval budget | Plan for a few hundred USD model spend in Phase 0–1; hard job cap **$2** |
| **D6** | Blind eval operator | Separate from tuner (different day / frozen prompts) |

## Product bar (Tier 1 casegoods exit)

| Metric | Target |
| --- | --- |
| Overall dims (one known size) | within **3%** on 90% of pieces |
| Part-instance recall / precision | ≥ **85%** each |
| Cut list size vs GT | within **5 mm or 3%** on 85% matched |
| Buy list BF error | within **10%** |
| Feature recall (drawers, doors, shelves, legs) | ≥ **90%** |
| Valid solid in round limit | ≥ **90%** |
| Median cost / time | ≤ **$1.50** / **6 min** (hard $2 / 10 min) |
| Blind human rating | majority Match or Close |

## Pipeline

```
photos → INTAKE → PERCEIVE → DIMENSION → CONSTRUCT → VERIFY → DERIVE → REVIEW/EXPORT
         rectify    Observation   snap/stock    IR→B-rep     render+metrics  lists     confidence UI
         segment    (no geom)     anchored      blocks                      allowances
         scale
```

Typed contracts: `observation.v1`, `furniture_ir.v1`, PartRecord v2 (local frame + allowances).

## Phase 0 (weeks 1–2): Measure and consolidate

1. Freeze shop UI / telemetry / guide / bespoke chair feature work.
2. Fusion console GT (Jonny): STEP + hand cut list → real set piece 1.
3. Fix scorer: segmentation path, **no scale search** in IoU, rectification when possible; re-score B/O.
4. Write scorer (Hungarian part match, size error, feature recall); run **A0** under blind protocol.
5. Adopt IR + stage pipeline; retire per-chair scripts as the active path.

**In repo (Phase 0):** fixed-scale IoU v3, `eval.scorer`, `observation.v1` / `furniture_ir.v1`, console IR + stub compiler, intake/verify hooks, `tools.v2.json`, corrected B/O table. Fusion STEP + live A0 remain operator tasks.

**Exit:** trusted baseline table, IR expresses console, stage hooks land; A0 live under D6 when scheduled.

## Phase 1 (weeks 3–8): Casegood vertical slice

Tier-1 blocks + IR compiler; Perceive/Dimension stages; shaded verify + discrepancy critic; local-frame lists with joinery allowances. Exit: console within targets; 10-piece set ≥70% of bar; A beats B on a majority.

## Phase 2 (weeks 9–14): Generalize and harden

Tier-2 blocks; hardware registry; DXF/PDF shop sheets; sandbox freeform; expand real set to ~30; full blind eval. Exit: Tier-1 bar on blind set; Tier-2 ~70%; safe for 10–20 testers.

## Phase 3 (weeks 15–22): Curves and chairs

Spline/sweep/laminate blanks; template-free chair from blocks. Gate: only if Phase 2 numbers hold.

## Phase 4 (parallel from week 12): Productization

Tester cohort, consented dataset loop, capture guidance, export integrations (Fusion STEP, SketchUp, CNC DXF).

## Stop doing now

Shop UI polish, Langfuse expansion beyond eval needs, few-shot from example bank until metric is trusted, one-off chair scripts for likeness, build-guide enhancements.

## First ten days

| Days | Work |
| --- | --- |
| 1–2 | Scorer + console GT export (Jonny) |
| 3–4 | Seg + rectify; drop scale search; re-score B/O |
| 5–6 | Shaded perspective render + section in verify |
| 7–8 | A0 blind on current pieces; publish corrected baselines |
| 9–10 | `observation.v1` + `furniture_ir.v1`; stub compiler (carcass, divider, drawer_bank, leg_set); hand-IR the console |

If the console cannot be expressed in IR by day 10, fix IR before building on it.

Implement phase-by-phase without expanding UI. Tracker: [`evals/photos/PHASE0_PRODUCT.md`](../../evals/photos/PHASE0_PRODUCT.md).

