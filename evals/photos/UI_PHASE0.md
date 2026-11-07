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

1. Start worker: `python -m furniture_cad jobs --port 8787` (set Anthropic key in worker env).
2. Optional: set Advanced → Worker URL to `http://127.0.0.1:8787`, or set Vercel `WORKER_JOBS_URL`.
3. Classic Create (Vercel `/api/messages` proxy) remains fallback when the worker is offline.

## Still ongoing (eval, not product code)

- [ ] Majority dogfood Match/Close (Phase 5 gate)
- [ ] ≥20-piece hardening corpus (Phase 6)
