# Phase 2 — Loop and scoring (job service + IoU)

Plan: [`docs/plans/photo-to-cutlist.md`](../../docs/plans/photo-to-cutlist.md)

**Status: INFRA LANDED — likeness gate OPEN (2026-11-07).** Job service + A/B harness + `check`/`compare` shipped. Baseline A does not yet beat Create IoU (no A silhouette path). Per plan: fix loop/helpers before Phase 3 UI.

## Delivered

| Piece | Path |
| --- | --- |
| Job store | `lab/furniture_cad/src/furniture_cad/jobs/store.py` |
| Job HTTP | `python -m furniture_cad jobs --port 8787` |
| Vercel relay | `api/jobs.js` (requires `WORKER_JOBS_URL`) |
| A/B scorecard | `python -m furniture_cad ab` |
| `check` / `compare` / `render` meta | `tools/handlers.py` |
| Tests | `tests/test_phase2_jobs.py` |

## Gate checklist

- [x] Job service: create / get / run (file store; Postgres later)
- [x] Vercel starter stub (relay only)
- [x] A/B scorecard skeleton (Create B IoUs recorded; A IoU null)
- [x] `check` targets within 5%; `compare` expected qty
- [ ] Exact part count on **4 of 5** expanded pieces (have 3 freeze + fixtures; expand console + case_02)
- [ ] IoU ≥ 0.55 on studio photos for baseline A
- [ ] Beats current Create on same photos (`chair_04` B=0.641; `case_01` B=0.297)

## Commands

```bash
cd lab/furniture_cad && source .venv/bin/activate
pytest -q tests/test_phase2_jobs.py
python -m furniture_cad ab --out out/ab_score.json
python -m furniture_cad jobs --port 8787 --root out/jobs
# POST http://127.0.0.1:8787/jobs {"prompt":"case_01","run":true,"mode":"freeze"}
```
