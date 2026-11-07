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

## Worker + job store (choose before Phase 1 loop)

Architecture: **Messages API tool-use loop in a worker**. Vercel = app / auth / job starter only.

| Option | Pros | Cons | Status |
| --- | --- | --- | --- |
| **A. Local Docker worker** (build123d + tool runner) | No Vercel wall-time; full STEP; cheap iterate | You run the machine | **Default recommendation** |
| B. Hosted container (Fly/Railway/Modal) | Always on for eval / later jobs | Cost + cold start | Alternative |
| C. Vercel serverless for the loop | — | **Reject** — Hobby ~5 min; no build123d | App/proxy only |

**Model access:** worker calls Messages API with **its own key**; report to existing telemetry + Langfuse.

**Job store (Phase 2; pick now):** Postgres (fits future HITL) or Redis for queue + status. Write-in: ______

**Spend / limits (proposed):** **$25/day** Anthropic; **$2/run**; hard caps on rounds, tokens, wall time. Enforce in the worker.

### Tool contract (write before loop code)

| Tool | Role |
| --- | --- |
| `build(script)` | Run helper-library script → solids / parts model |
| `render(views)` | Front / side / iso images |
| `measure(part)` | Part / blank dims |
| `check()` | BBox, overlaps, silhouette IoU |
| `compare()` | Photo vs render |
| `lists()` | Cut / material lists |
| `ask_user(question)` | Pause job (Phase 3) |

- [ ] Confirm worker host: Local Docker (A) or ______
- [ ] Confirm job store: Postgres / Redis / ______
- [ ] Confirm spend caps: $25/day · $2/run (or ______)
- [ ] Tool contract reviewed / frozen in repo (this table + plan doc)
- [ ] Secrets: worker Anthropic key (not committed); Vercel key for browser Create baseline B only

## Gate (Phase 0)

- [ ] Three-piece set complete (including `case_01` photo + baseline B)
- [ ] Sandbox host chosen
- [ ] Spend cap chosen
- [x] Plan doc merged / on `main` path
- [x] Chairs baseline B recorded (`chair_04`, `chair_02`) — **partial gate**
- [~] List-builder started under Phase 1 using bookshelf SPEC fixture (photo still open) — see [`PHASE1.md`](PHASE1.md)

**2026-11-07:** Proceeding to Phase 1 scaffolding while `case_01` photo remains outstanding (user request). Do not claim full Phase 0 gate until photo + Create baseline B land.

## Explicitly out of Phase 0

Console, second case good, tube stool (`chair_03`), organic walnut (`chair_05`) — Phase 2+ expansion or `missing_block` log only.
