# Phase 0 (product plan) — Measure and consolidate

Plan: [`docs/plans/product-plan-2026-11-08.md`](../../docs/plans/product-plan-2026-11-08.md)

## Freeze

Do **not** expand: shop UI polish, Langfuse dashboards, build guide, bespoke chair scripts, example-bank few-shot for likeness.

## Checklist

- [x] Product plan + D1–D6 locked in repo
- [x] Scorer: part match / cut-list share / feature recall / overall 3% (`furniture_cad.eval.scorer`)
- [x] IoU product metric = **fixed scale** (±2% translation only); legacy scale-search retained behind flag
- [x] Schemas: `observation.v1`, `furniture_ir.v1`
- [x] Hand-IR the console (`examples/ir/console_stub.ir.json`); stub IR compiler (`construct/compile.py`)
- [x] Intake hooks: EXIF orient + brightness seg + OpenCV rectify detect (`intake/`)
- [x] Verify shaded-render stub with orthographic fallback (`verify/render_shaded.py`)
- [x] Tool contract v2 draft (`contracts/tools.v2.json`)
- [x] Corrected B/O table (fixed-scale): [`blind/CORRECTED_BASELINES.md`](blind/CORRECTED_BASELINES.md)
- [x] Console GT placeholder set: [`cases/console_01/`](cases/console_01/) (STEP pending Jonny)
- [ ] Fusion console STEP + hand cut list (Jonny) → replace placeholder
- [ ] SAM / full homography rectification (replace brightness mask)
- [ ] Blind A0 live runs under frozen prompts (spend-capped; operator ≠ tuner)

## A0 status

| Piece | A0 | Status |
| --- | --- | --- |
| chair_04 / chair_02 / case_01 | — | **Deferred** — protocol frozen in R0/R4; run under D6 (separate day / frozen prompts) with $2 hard cap |

Product gate uses **A**, not O. Corrected B/O stick is fixed-scale IoU v3.

## Commands

```bash
cd lab/furniture_cad && pytest -q tests/test_phase0_scorer_iou.py tests/test_phase0_ir_compile.py
python -m furniture_cad ab --ids chair_04 chair_02 case_01 --out out/ab_fixed_scale.json
```

## Exit

Trusted baseline table published; IR expresses console; stage hooks (`intake` / `construct` / `verify`) land; A0 live recording remains an operator task (not a code blocker for Phase 1).
