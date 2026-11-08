# Phase 2 (product plan) — Generalize and harden

Plan: [`docs/plans/product-plan-2026-11-08.md`](../../docs/plans/product-plan-2026-11-08.md)

## Checklist

- [x] Tier-2 blocks: table, bench, stool, angled_leg (+ apron/stretcher reuse)
- [x] Hardware registry + IR → hardware list
- [x] Shop exports: CSV cut list, DXF stub, PDF stub
- [x] Freeform script disabled on product path (`construct/sandbox.py`)
- [x] Real-set expansion tracker → 30 slots ([`SET30.md`](SET30.md))
- [ ] Full blind eval on expanded set
- [ ] Outside tester readiness (auth / retention already partly in R6)

## Commands

```bash
cd lab/furniture_cad && pytest -q tests/test_phase2_tier2.py
```
