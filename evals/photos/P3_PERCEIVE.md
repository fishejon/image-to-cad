# P3 — Real Perceive + Dimension

Plan: [`docs/plans/product-plan-2026-11-10.md`](../../docs/plans/product-plan-2026-11-10.md)

## Checklist

- [x] Vision Perceive (`perceive/vision.py`): Anthropic observation.v1 + two-pass counts + ask_user on disagreement
- [x] Pipeline flag: `--vision` / `FURNITURE_CAD_PERCEIVE=vision` / jobs `mode=pipeline_vision`
- [x] Dimension: user-wins conflicts, single-anchor scale, stock snap, `within_3pct`
- [x] Offline tests (`tests/test_p3_perceive.py`)
- [x] Live feature recall ≥ 0.90 on `console_01` studio photo vs `features.json` (recorded **1.0**, ~$0.012)
- [ ] Second / third casegood GT (sideboard, bookcase) — **blocked on Fusion**

## Live record (`console_01_front_clean.jpg`)

| Metric | Value |
| --- | --- |
| Feature recall | **1.0** |
| Counts | drawer=2, shelf=1, leg=4, open_cubby=1, end_block_carved=2, pull=0 |
| Spend | ~$0.012 (Haiku, 2 calls) |
| Dims | user-known 1193.8 × 304.8 × 762 → within 3% by construction |

Artifact: `evals/photos/cases/console_01/perceive_score.json` (local; may be gitignored).

## Commands

```bash
cd lab/furniture_cad
pytest -q tests/test_p3_perceive.py tests/test_p2_pipeline.py
python -m furniture_cad perceive \
  --photo ../../evals/photos/cases/console_01/console_01_front_clean.jpg \
  --features ../../evals/photos/cases/console_01/features.json \
  --known-mm 1193.8 304.8 762 \
  --out ../../evals/photos/cases/console_01/perceive_score.json
```

## Gate

**Partial met** on console studio photo. Full P3 still needs ≥2 more GT pieces (sideboard, bookcase) from Fusion.
