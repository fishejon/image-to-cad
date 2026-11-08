# Phase 0 (product plan) — Measure and consolidate

Plan: [`docs/plans/product-plan-2026-11-08.md`](../../docs/plans/product-plan-2026-11-08.md)

## Freeze

Do **not** expand: shop UI polish, Langfuse dashboards, build guide, bespoke chair scripts, example-bank few-shot for likeness.

## Checklist

- [x] Product plan + D1–D6 locked in repo
- [x] Scorer: part match / cut-list share / feature recall / overall 3% (`furniture_cad.eval.scorer`)
- [x] IoU product metric = **fixed scale** (±2% translation only); legacy scale-search retained behind flag
- [x] Schemas: `observation.v1`, `furniture_ir.v1`
- [ ] Fusion console STEP + hand cut list (Jonny) → real set piece 1
- [ ] SAM / rectification (replace brightness mask)
- [ ] Re-score B/O with fixed-scale IoU; publish corrected table
- [ ] Blind A0 on current pieces
- [ ] Hand-IR the console; stub IR compiler (carcass, divider, drawer_bank, leg_set)

## Commands

```bash
cd lab/furniture_cad && pytest -q tests/test_phase0_scorer_iou.py
python -m furniture_cad ab --ids chair_04 chair_02 case_01 --out out/ab_fixed_scale.json
```
