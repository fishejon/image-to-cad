# Plan: Photo → model + cut/material lists

> **Status: SUPERSEDED for sequencing** by [`photo-to-model-recovery.md`](photo-to-model-recovery.md) (R0–R7, 2026-11-08).  
> This file remains as the original option-1 architecture note. **Do not treat Phases 1–5 as product gates passed.**

**Author:** Jonny Fisher · **Date:** 2026-11-07 · **Revised:** 2026-11-08 (truth reset)

## Honest status (R0)

| Old claim | Reality |
| --- | --- |
| Phase 2 gate passed (baseline A beats Create) | **Oracle** hand scripts beat Create on IoU — not the live agent. Product gate **not** passed. |
| Phase 1 live 5/5 within 3 rounds | Tool-calling **smoke** (text prompt → parts/lists); not photo→model |
| `check` / `compare` / IoU in the loop | Stubs / offline silhouette only — loop does not close on real renders yet |
| Lists exact on freeze pieces | Typed `PartRecord` numbers next to scripts — not derived from solids |
| Phase 5 landed | Scaffolding (flags, relay, spend hooks); auth/CORS/exposure still open |
| Shop-grade UI | Progress/stepper and worker claims ahead of real job wiring — see recovery R5 |

**What remains solid:** tool contract shape, job store shape, list builder, Lists tab vocabulary, failure log, eval pack, worker + Vercel starter idea.

## Labels

- **B** — Classic Create  
- **O** — Oracle (`lab/furniture_cad/src/furniture_cad/tools/oracle_set.py`)  
- **A** — Live blind agent ([`evals/photos/BLIND_PROTOCOL.md`](../../evals/photos/BLIND_PROTOCOL.md))  

Starting numbers: [`evals/photos/BASELINES_R0.json`](../../evals/photos/BASELINES_R0.json) · tracker [`evals/photos/R0.md`](../../evals/photos/R0.md)

## Original phase outline (historical)

Phases 0–6 below described the first plan. Execution continues as **R0–R7** in the recovery doc. Keep worker host / spend caps / Messages tool-use architecture unless R4 says otherwise.

### Architecture (still intended)

- Messages API tool-use loop in a **worker**; Vercel = app / auth / job starter  
- Tools: `build`, `render`, `measure`, `check`, `compare`, `lists`, `ask_user` → `contracts/tools.v1.json` (→ v2 in R1)  
- Spend: **$25/day · $2/run** (open decision whether to keep once images are in the loop)

### Critical path now

**R0** truth → **R1** eyes → **R2** lists-from-geometry ∥ **R3** helpers → **R4** blind eval → **R5** honest UI → **R6** hardening → **R7** coverage.

Do **not** build more shop UI before R4 reports (non-model UI polish may continue).
