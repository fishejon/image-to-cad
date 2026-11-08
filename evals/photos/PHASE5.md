# Phase 5 — Integration and rollout

**Status: SCAFFOLDING (not a product gate).** Feature flags, job relay, and spend hooks exist. Worker auth on public paths, CORS lockdown, and honest shop UI wiring are **R5/R6**.

See [`lab/furniture_cad/FEATURE_FLAGS.md`](../../lab/furniture_cad/FEATURE_FLAGS.md) · Recovery [`docs/plans/photo-to-model-recovery.md`](../../docs/plans/photo-to-model-recovery.md).

## Checklist (honest)

- [x] Worker can use env API key (local)
- [x] Per-job spend hook in loop / contract
- [x] Status via job store / `/api/jobs` relay (path bugs fixed over time)
- [~] Product Create posts jobs + polls — shop path still mixes claims; Classic Create remains real for B
- [ ] Majority dogfood Match/Close on **live A** — after R4
- [ ] Auth, rate limits, restricted CORS — **R6** (start in R1)
