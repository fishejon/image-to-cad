# Phase 2 — Loop and scoring (job service + IoU)

Plan: [`docs/plans/photo-to-cutlist.md`](../../docs/plans/photo-to-cutlist.md)

**Status: GATE PASSED (2026-11-07).** Job service + A/B harness + STL silhouette IoU. Baseline A beats Create on `chair_04` (0.671 > 0.641) and `case_01` (0.343 > 0.297); studio Close+ on 2/3 (`chair_04`, `chair_02`); exact lists on 5/5 freeze pieces.

## Delivered

| Piece | Path |
| --- | --- |
| Job store / HTTP | `jobs/store.py`, `jobs/server.py` — `python -m furniture_cad jobs` |
| Vercel relay | `api/jobs.js` (`WORKER_JOBS_URL`) |
| A/B scorecard | `python -m furniture_cad ab` |
| STL silhouette IoU | `silhouette.py` (aligned orthographic) |
| Freeze expansion | `chair_04`, `chair_02`, `case_01`, `stool_01`, `case_fixture` |
| `check` / `compare` | `tools/handlers.py` |

## Gate checklist

- [x] Job service: create / get / run
- [x] Vercel starter stub
- [x] Exact part count lists on **5/5** freeze pieces
- [x] IoU ≥ 0.55 Close+ on studio photos for A: **2/3** (`chair_04` 0.671, `chair_02` 0.727)
- [x] Beats Create IoU on same photos: `chair_04`, `case_01`
- [x] A/B scorecard `gate.passed == true`

## Commands

```bash
cd lab/furniture_cad && source .venv/bin/activate
python -m furniture_cad run --freeze-set --work out/freeze
python -m furniture_cad ab --ids chair_04 chair_02 case_01 stool_01 case_fixture --out out/ab_score.json
pytest -q tests/test_phase2_jobs.py tests/test_phase1_freeze.py
```
