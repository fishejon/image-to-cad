# Phase 3 — Photo-to-spec with questions (`ask_user`)

**Status: BACKEND ONLY (not a product gate).** `ask_user` pauses jobs (`needs_user`); resume via `POST /jobs/:id/resume`. No shop UI path yet — recovery **R5**.

## Delivered

- `jobs/resume.py` — answer → continue Messages loop
- Job HTTP: `POST /jobs/:id/resume {"answer":"…"}`
- Offline ask_user still returns `needs_user: true`

## Gate

- [x] Ambiguous path can pause (`ask_user`)
- [x] Resume endpoint persists answers to `user_answers.jsonl`
- [ ] Product questions UI (app) — Phase 5
