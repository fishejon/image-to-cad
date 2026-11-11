# P1 — Console expressible

Plan: [`docs/plans/product-plan-2026-11-10.md`](../../docs/plans/product-plan-2026-11-10.md) · **D7 / D11**

## Checklist

- [x] `furniture_ir.v2` schema + validator
- [x] `swept_shell` + `two_profile_flared` blocks
- [x] Console IR: `lab/furniture_cad/examples/ir/console_01.ir.json`
- [x] Compiler path for v2 + deterministic hash
- [x] Golden tests vs STEP bbox + hand cut list (id recall **1.0**; W err ~2 mm)
- [ ] Higher-fidelity swept profile / volume within 5% (follow-on)

## Commands

```bash
cd lab/furniture_cad
pytest -q tests/test_p1_console_ir.py
```

## Gate

**Met for P1 exit on expressibility:** IR v2 compiles the console; bbox near STEP; part-id recall ≥ 0.85. Shape fidelity (true sweep / two-profile carve) remains iterative.
