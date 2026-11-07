# Phase 2 — Loop and scoring (job service + IoU)

Plan: [`docs/plans/photo-to-cutlist.md`](../../docs/plans/photo-to-cutlist.md)

**Status: IN PROGRESS** after Phase 1 gate.

## Goals

- Job service: `POST /jobs`, `GET /jobs/:id` (Vercel starts/relays; worker runs loop)
- Persist project artifacts; Langfuse tool traces
- Expand eval to 5–6 pieces; compare baseline A (tool-use) vs B (Create)
- **Gate:** exact part count on 4/5; IoU ≥ 0.55 on studio photos; **beats Create** on same photos

## Notes

- Create baseline B: `chair_04` IoU 0.641 Close+; `chair_02` Close+\*; `case_01` IoU 0.297 Wrong
- Phase 2 must beat those on studio shots — start with job stub + A/B harness before raising IoU bar to 0.70
