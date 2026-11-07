# Phase 0 — Baseline freeze

Plan: [`docs/plans/photo-to-cutlist.md`](../../docs/plans/photo-to-cutlist.md)

## Frozen set (3 pieces)

| Role | id | Photo | Dims | Baseline B (current Create) | Baseline A (build123d loop) | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Dining/side chair | `chair_04` (Lakin) | `chairs/chair_04.jpg` | catalog in `chair_04.json` | **Done** Careful Create IoU **0.641 Close+** (2026-11-01); stance OK | pending Phase 1 | Primary studio wedge |
| Dining/side chair | `chair_02` | `chairs/chair_02.jpg` | tape/brief | **Done** Careful Create Close+\*; bespoke STL gold Close+\* | pending Phase 1 | Room photo — IoU untrusted until subject mask |
| Rectilinear case | `case_01` bookshelf | **needed** | use `examples/bookshelf.json` params as starting dims | **blocked** — need photo + Create run | pending Phase 1 | Simple case; console deferred to Phase 2 |

## Baseline B checklist

- [x] `chair_04` Create + IoU written (`chairs/chair_04.score.json` → `create`)
- [x] `chair_02` Create + stance written (`chairs/chair_02.score.json` → `create`; mark `iou_quality: untrusted_room_background`)
- [ ] `case_01` photo + dims sidecar + Careful Create + score row
- [ ] Optional: re-measure gold EXAMPLE IoU for `case_01` if a studio photo exists

## Sandbox + spend (choose before Phase 1)

| Option | Pros | Cons | Status |
| --- | --- | --- | --- |
| **A. Local Docker** (build123d + OCC in container) | No Vercel 300s cap; full STEP; cheap iterate | You run the machine | **Default recommendation** |
| B. Hosted container (Fly/Railway/Modal) | Always on for eval | Cost + cold start; still need spend cap | Alternative if local GPU/CPU painful |
| C. Vercel `/api/messages` only | Key already there | **Reject for compile loops** — Hobby ~5 min; no build123d | OK for LLM text only |

**Spend cap (proposed):** hard stop at **$25/day** Anthropic for Phase 0–1 eval; per-run cap **$2** (Careful-equivalent). Enforce in the sandbox runner when Phase 1 starts.

- [ ] Confirm host: Local Docker (A) or write-in ______
- [ ] Confirm spend cap: $25/day · $2/run (or write-in ______)
- [ ] Secrets: Anthropic key available to container (not committed); Vercel key remains for browser Create baseline B only

## Gate (Phase 0)

- [ ] Three-piece set complete (including `case_01` photo + baseline B)
- [ ] Sandbox host chosen
- [ ] Spend cap chosen
- [x] Plan doc merged / on `main` path
- [ ] **No list-builder code started** until boxes above are checked

## Explicitly out of Phase 0

Console, second case good, tube stool (`chair_03`), organic walnut (`chair_05`) — Phase 2+ expansion or `missing_block` log only.
