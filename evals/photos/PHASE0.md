# Phase 0 — Baseline freeze

Plan: [`docs/plans/photo-to-cutlist.md`](../../docs/plans/photo-to-cutlist.md)

## Frozen set (3 pieces)

| Role | id | Photo | Dims | **B** Classic Create | **O** oracle | **A0** live blind | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dining/side chair | `chair_04` (Lakin) | `chairs/chair_04.jpg` | catalog in `chair_04.json` | IoU **0.641 Close+** | IoU **0.671 Close+** | **not measured** | Primary studio wedge |
| Dining/side chair | `chair_02` | `chairs/chair_02.jpg` | tape/brief | IoU **0.948\*** Close+ | IoU **0.727\*** | **not measured** | Room photo — IoU untrusted |
| Rectilinear case | `case_01` bookshelf | `cases/case_01.jpg` | placeholder 900×300×1800 | IoU **0.297 Wrong** | IoU **0.343 Wrong** | **not measured** | See [`BASELINES_R0.json`](BASELINES_R0.json) |

> **A** = live photo→model under [`BLIND_PROTOCOL.md`](BLIND_PROTOCOL.md). **O** is not the system under test. Recovery track: [`R0.md`](R0.md).

## Baseline B checklist

- [x] `chair_04` Create + IoU written (`chairs/chair_04.score.json` → `create`)
- [x] `chair_02` Create + stance written (`chairs/chair_02.score.json` → `create`; mark `iou_quality: untrusted_room_background`)
- [x] `case_01` photo + sidecar (`cases/case_01.jpg` + `case_01.json`) — dims still placeholder
- [x] `case_01` Careful Create + score row (baseline B) — IoU 0.297 Wrong; geometryOk; high likeness penalty
- [ ] Optional: gold EXAMPLE / hand SPEC for `case_01` once dims known (Create is baseline B only)

## Worker + job store (choose before Phase 1 loop)

Architecture: **Messages API tool-use loop in a worker**. Vercel = app / auth / job starter only.

| Option | Pros | Cons | Status |
| --- | --- | --- | --- |
| **A. Local Docker worker** (build123d + tool runner) | No Vercel wall-time; full STEP; cheap iterate | You run the machine | **Default recommendation** |
| B. Hosted container (Fly/Railway/Modal) | Always on for eval / later jobs | Cost + cold start | Alternative |
| C. Vercel serverless for the loop | — | **Reject** — Hobby ~5 min; no build123d | App/proxy only |

**Model access:** worker calls Messages API with **its own key**; report to existing telemetry + Langfuse.

**Job store (Phase 2; frozen now):** **Postgres** (fits future HITL + existing `DATABASE_URL` path). Redis not required for v1.

**Spend / limits (frozen):** **$25/day** Anthropic; **$2/run**; rounds / tokens / wall time from [`lab/furniture_cad/contracts/tools.v1.json`](../../lab/furniture_cad/contracts/tools.v1.json) (`max_rounds` 8, `max_tokens_per_request` 16000, `max_wall_time_s` 900). Enforce in the worker (env overrides OK).

### Tool contract (frozen)

Schema: [`lab/furniture_cad/contracts/tools.v1.json`](../../lab/furniture_cad/contracts/tools.v1.json) · loaders: `furniture_cad.tools.contract`

| Tool | Role |
| --- | --- |
| `build(script)` | Run helper-library script → solids / parts model |
| `render(views)` | Front / side / iso images |
| `measure(part)` | Part / blank dims |
| `check()` | BBox, overlaps, silhouette IoU |
| `compare()` | Photo vs render |
| `lists()` | Cut / material lists |
| `ask_user(question)` | Pause job (Phase 3) |

- [x] Confirm worker host: **Local Docker (A)** — stub [`lab/furniture_cad/Dockerfile`](../../lab/furniture_cad/Dockerfile)
- [x] Confirm job store: **Postgres** (Phase 2 wiring; HITL-compatible)
- [x] Confirm spend caps: **$25/day · $2/run** (+ contract wall/round/token caps)
- [x] Tool contract reviewed / frozen in repo (`tools.v1.json` + this table + plan doc)
- [x] Secrets: worker Anthropic key via env (`ANTHROPIC_API_KEY` / `FURNITURE_CAD_ANTHROPIC_KEY`, not committed); Vercel key for browser Create baseline B only

## Gate (Phase 0)

- [x] Three-piece set complete (including `case_01` photo + baseline B) — dims for case still placeholder
- [x] Sandbox host chosen — Local Docker (A)
- [x] Spend cap chosen — $25/day · $2/run
- [x] Plan doc merged / on `main` path
- [x] Chairs baseline B recorded (`chair_04`, `chair_02`) — **partial gate**
- [~] List-builder started under Phase 1 using bookshelf SPEC fixture (photo still open) — see [`PHASE1.md`](PHASE1.md)

**2026-11-07:** Worker host / job store / spend caps / tool contract frozen. Proceeding to Phase 1 tool-use CLI while `case_01` photo remains outstanding. Do not claim full Phase 0 gate until photo + Create baseline B land.

## Explicitly out of Phase 0

Console, second case good, tube stool (`chair_03`), organic walnut (`chair_05`) — Phase 2+ expansion or `missing_block` log only.
