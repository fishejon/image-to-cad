# Plan: Telemetry, analytics, and learning loop

## TLDR
- Ship **run_id** end-to-end (done on client; extend to proxy + feedback API).
- Add **product analytics** (PostHog) for funnels and feature usage.
- Add **LLM observability** (Langfuse on `/api/messages`) for cost, latency, prompts.
- Mirror HITL feedback to **Postgres + optional R2** so datasets are not browser-only.
- Keep schemas **domain-agnostic** so furniture is the first pack, not the only product.

## Critical decisions
1. **Decision:** Three pipelines that share `run_id` — PostHog (behavior), Langfuse (model traces), Postgres (HITL + run outcomes). **Because:** Different tools excel at different questions; forcing one warehouse early slows shipping. **Rejected:** Only PostHog (cannot safely hold prompts/specs at scale).
2. **Decision:** Opt-in before any image upload to server storage; default analytics has no photos. **Because:** Trust and future B2B. **Rejected:** Silent image upload.
3. **Decision:** Langfuse lives on the **proxy**, not the browser. **Because:** API key and full prompts never leave a controlled path. **Rejected:** Browser-side Anthropic SDK tracing.
4. **Decision:** Domain field on every run (`furniture` now; `manual` / custom later). **Because:** Same infra for instruction-generation beyond furniture. **Rejected:** Furniture-only event names.

## Current state (after HITL dataset export)
- [x] Local feedback + examples in IndexedDB
- [x] Ship → Download HITL dataset (JSON + JSONL)
- [x] Client `runId` stamped on AI runs and feedback/example rows
- [x] `runId` on Anthropic proxy requests / response headers
- [x] `/api/feedback` + `/api/events`
- [x] PostHog
- [ ] Langfuse
- [ ] Postgres / R2
- [ ] Golden-set eval job

## Tasks

### Phase 1 — Correlate runs (small, in-repo)
- [x] **Proxy run_id** — Accept `x-run-id` (or body metadata) on [`api/messages.js`](../../api/messages.js) / [`server/messages.js`](../../server/messages.js); echo on response; log structured line `{ runId, model, ms, status, tokens? }`
- [x] **Client sends run_id** — [`vision.js`](../../src/ai/vision.js) proxy/anthropic providers attach header from `o.runId`
- [x] **`POST /api/events`** — Fire-and-forget run_started / run_finished payloads (JSON body); store in memory/log first or Neon if `DATABASE_URL` set
- [x] **`POST /api/feedback`** — Same shape as `CAD.store.addFeedback`; append to DB or file; client calls after local save when `navigator.onLine` and opt-in flag
- [x] **Tests** — Unit tests for event payload validation; mock proxy header round-trip

### Phase 2 — Product + LLM visibility
- [x] **PostHog** — Load snippet when `POSTHOG_KEY` present; events: `create_started`, `create_finished`, `revise_applied`, `feedback_submitted`, `joint_targeted`, `guide_opened`, `dataset_exported`, `export_stl`
- [ ] **Langfuse** — Trace each `/api/messages` call; metadata: `runId`, `task`, `quality`, `domain`
- [ ] **Dashboard doc** — One page listing the 6 north-star metrics (create success, ratings, critic usefulness, unlabeled contacts, guide opens, $ / success)

### Phase 3 — Durable learning store
- [ ] **Postgres schema** — `runs`, `feedback`, `examples` tables keyed by `run_id`
- [ ] **R2/S3** — Optional image upload with consent; store hash + URL on run row
- [ ] **Export job** — Server-side JSONL compatible with existing `hitl-v1` schema (merge local + server)
- [ ] **Golden set** — Seed 5–10 hard images with expected inventory; weekly score script

### Phase 4 — Multi-domain / B2B readiness (later)
- [ ] Auth + `org_id` on events
- [ ] Private example banks per org
- [ ] Domain packs config (inventory fields, method catalogs, guide templates)
- [ ] Retention / delete-my-data API

## Event schema (hitl-v1 + telemetry)

```text
run_started:  { runId, domain, task, inputMode, quality, model, staged?, visual? }
run_finished: { runId, geometryOk, rounds, likenessPenalty, iou?, unlabeledContacts?, durationMs, error? }
feedback:     { runId, rating /* match|close|wrong */, failureTags[], note, object?, inventory?, model?, quality? }
example:      { runId, object, inventory, specSummary }  // mark correct
ui:           { name, runId?, props }  // PostHog only
```

## Risks & rollback
- Proxy logging must never include API keys or full image base64.
- PostHog without PII: use anonymous distinct_id = hash(device_id).
- If Neon unset, `/api/events` no-ops or logs only — app stays usable offline.
- Langfuse failure must not fail the Anthropic call.

## Success criteria
- You can answer: “Of last N creates, % Match vs Wrong by failure tag and model.”
- A single `runId` links UI feedback → proxy latency/cost → exported JSONL row.
- Dataset export from Ship still works offline without the server.
