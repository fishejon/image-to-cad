# P2 — One wired pipeline

Plan: [`docs/plans/product-plan-2026-11-10.md`](../../docs/plans/product-plan-2026-11-10.md)

## Checklist

- [x] Stage runner: Intake → Perceive → Dimension → Construct → Compile → Verify → Derive
- [x] Job server `mode=pipeline` (or `ir`) uses the runner; tool loop remains default fallback
- [x] Artifacts per stage under job work dir (`events.json`, `ir.json`, STL/STEP, lists)
- [x] E2E test with known dims (no model spend)

## Commands

```bash
cd lab/furniture_cad
pytest -q tests/test_p2_pipeline.py
# HTTP: POST /jobs with {"mode":"pipeline","known_mm":{"w":1193.8,"d":304.8,"h":762}, ...}
```

## Gate

**Met:** photo (optional) + known size → IR + model + lists via pipeline path with $0 model spend.
