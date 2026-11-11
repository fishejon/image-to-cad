# P0 — Ruler and ground truth

Plan: [`docs/plans/product-plan-2026-11-10.md`](../../docs/plans/product-plan-2026-11-10.md) · Decision **D8**

## Checklist

- [x] Plan saved; D7–D12 + §11 answers locked
- [x] `features.json` + `known_sizes.json` + view tags on `console_01`
- [x] Camera-fit silhouette search (`verify/camera_fit.py`)
- [x] Calibration test (D8): GT STEP vs photo — **fail until front-on photo**
- [x] Publish calibrated table noting IoU untrusted on current 3/4 shot
- [ ] Front-on console photo from Jonny → re-run calibration to ≥ 0.8

## Gate

Calibration passes (GT STEP camera-matched IoU ≥ **0.8** on a front-on studio photo), **or** gates use part/dimension metrics only until then.

## Commands

```bash
cd lab/furniture_cad
pytest -q tests/test_p0_calibration.py
python -m furniture_cad calibrate-console
```
