# P4 — Verify + console A0

Plan: [`docs/plans/product-plan-2026-11-10.md`](../../docs/plans/product-plan-2026-11-10.md)

## Checklist

- [x] IR patch ops + deterministic discrepancy → patch map (`construct/patch.py`)
- [x] Repair loop compile → verify → patch (≤4 rounds) (`verify/repair.py`)
- [x] Pipeline uses repair loop; optional model patches via `FURNITURE_CAD_VERIFY_MODEL_PATCH`
- [x] Three blind pipeline+vision runs on `console_01` (`python -m furniture_cad p4-a0`)
- [ ] Camera-matched IoU ≥ 0.55 (studio) — **blocked**: D8 calibration still ~0.50 / untrusted
- [ ] Blind human Match/Close rating — needs Jonny
- [ ] Board-feet error ≤ 15% — not yet scored in A0 harness
- [ ] More Fusion GT (sideboard / bookcase / nightstand) — **blocked on Jonny**

## Live A0 (2026-11-11)

| Metric | Mean (n=3) | P4 target |
| --- | --- | --- |
| Dims within 3% | yes | yes |
| Part recall | **1.0** | ≥ 0.70 |
| Feature recall (vision) | **1.0** | ≥ 0.90 |
| Valid solid | yes | 80% |
| Spend / wall | ~$0.012 / ~5 s | ≤ $2 / 10 min |
| Cut-list size match | **0.31** | ≥ 0.50 of matched |
| Camera IoU | deferred | ≥ 0.55 |

Artifact: `evals/photos/cases/console_01/P4_A0.json`

Cut-list size match fails on carved ends / drawer box / leg blanks (IR still approximate). Tightening needs more faithful IR blanks, not more photos.

## Commands

```bash
cd lab/furniture_cad
pytest -q tests/test_p4_repair.py
python -m furniture_cad p4-a0 --runs 3
```

## Gate

**Partial met** on dims / parts / features / solid. Full P4 column still needs trusted IoU, board-ft, and human blind rating; generalization needs more Fusion GT.
