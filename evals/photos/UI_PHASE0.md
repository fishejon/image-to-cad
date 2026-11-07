# UI Phase 0–6 — Shop-grade interface

Spec: [`docs/plans/ui-ux-shop-grade.md`](../../docs/plans/ui-ux-shop-grade.md)

## Done

- [x] Spec, terms, Lists tab, Classic labels (Phase 0–1)
- [x] Progress / compare / timeline / worker status (Phase 2)
- [x] Intake + read-back (Phase 3)
- [x] Part cards, Adjust / Ask for a change (Phase 4)
- [x] First-run, spend-cap, mobile, aria-live (Phase 5)
- [x] Scope banners, multi-photo, sheet view (Phase 6)
- [x] **Create → worker job relay** (`POST /api/jobs` + poll + ask_user resume + artifacts)
- [x] STEP/STL download from shop job artifacts (Ship + Lists)
- [x] Domain profile selector (woodworking / cabinetry / metal)
- [x] Resume in-progress shop job after refresh

## Ops notes

1. **Hosted (production):** deploy Fly worker + set Vercel `WORKER_JOBS_URL` + `WORKER_JOBS_TOKEN` — see [`docs/deploy-worker.md`](../../docs/deploy-worker.md).
2. **Local:** `python -m furniture_cad jobs --port 8787` or Docker; optional Advanced → Worker URL `http://127.0.0.1:8787`.
3. Leave Worker URL empty in production so the browser uses `/api/jobs` (token stays on the server).
4. Classic Create remains fallback when the worker is offline.

## Still ongoing (eval, not product code)

- [ ] Majority dogfood Match/Close (Phase 5 gate)
- [ ] ≥20-piece hardening corpus (Phase 6)
