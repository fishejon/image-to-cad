# Phase 3 (product plan) — Curves and chairs

Plan: [`docs/plans/product-plan-2026-11-08.md`](../../docs/plans/product-plan-2026-11-08.md)

## Checklist

- [x] Sweep / spline / laminate blank blocks (`construct/blocks/curves.py`)
- [x] Template-free chair_side_assembly from blocks (labeled approximate)
- [x] Ship gate: defer / approximate / full (`construct/phase3_gate.py`)
- [ ] Proceed only if Phase 2 blind numbers hold
- [ ] Chair mean IoU ≥ 0.55 for full ship; else explicit “approximate” labeling

## Commands

```bash
cd lab/furniture_cad && pytest -q tests/test_phase3_curves.py
```
