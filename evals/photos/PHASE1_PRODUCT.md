# Phase 1 (product plan) — Casegood vertical slice

Plan: [`docs/plans/product-plan-2026-11-08.md`](../../docs/plans/product-plan-2026-11-08.md)

## Checklist

- [x] Tier-1 IR blocks: divider, top, drawer_box, drawer_front, door, face_frame, leg_set, apron, stretcher
- [x] IR compiler uses blocks; console IR compiles with drawers + legs + cut_list.v2 allowances
- [x] Perceive heuristic → `observation.v1`
- [x] Dimension: anchor user dims + stock snap
- [x] Verify critic: dim + feature discrepancies
- [x] PartRecord v2-shaped rows (`derive_allowance`)
- [ ] Vision Perceive (model) + full camera-matched shaded render
- [ ] 10-piece casegood set ≥70% of Tier-1 bar
- [ ] A beats B on a majority (blind)

## Commands

```bash
cd lab/furniture_cad && pytest -q tests/test_phase1_casegood.py tests/test_phase0_ir_compile.py
```

## Exit (not yet)

Console within targets on Fusion GT; 10-piece set metrics; cost/time within $1.50 / 6 min.
