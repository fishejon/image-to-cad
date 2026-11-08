# Phase 2 — Loop and scoring (job service + IoU)

Plan: [`docs/plans/photo-to-cutlist.md`](../../docs/plans/photo-to-cutlist.md) · Recovery: [`R0.md`](R0.md)

**Status: PRODUCT GATE NOT PASSED.**  
Infrastructure landed (job service, relay stub, silhouette helper, A/B harness). The 2026-11-07 “GATE PASSED / baseline A beats Create” result scored **oracle STLs** as if they were the agent. That is an **oracle ceiling (O)**, not live **A**.

## What actually landed

| Piece | Path |
| --- | --- |
| Job store / HTTP | `jobs/store.py`, `jobs/server.py` |
| Vercel relay | `api/jobs.js` |
| Scorecard | `python -m furniture_cad ab` → labels **B / O / A** (v2) |
| STL silhouette IoU | `silhouette.py` |
| Oracle set | `tools/oracle_set.py` |
| `check` / `compare` | Handlers largely stubbed for in-loop photo IoU — **R1** |

## Corrected checklist

- [x] Job service: create / get / run (local file store)
- [x] Vercel starter / relay scaffolding
- [x] Oracle lists + IoU measurable offline
- [ ] Live agent A beats Create B on same photos under blind protocol — **R4**
- [ ] In-loop real render + check + compare — **R1**

## Oracle ceiling (not a product gate)

| Piece | B Create IoU | O oracle IoU |
| --- | ---: | ---: |
| `chair_04` | 0.641 | 0.671 |
| `chair_02` | 0.948\* | 0.727\* |
| `case_01` | 0.297 | 0.343 |

\*Untrusted room photo. Full table: [`BASELINES_R0.json`](BASELINES_R0.json).

## Commands

```bash
cd lab/furniture_cad && source .venv/bin/activate
python -m furniture_cad run --freeze-set --work out/oracle
python -m furniture_cad ab --ids chair_04 chair_02 case_01 --out out/ab_score.json
```
