# Telemetry dashboard — north-star metrics

One page for the six questions that decide whether image→CAD is improving. Sources share `runId`.

| # | Metric | Question | Primary source | How to read |
|---|--------|----------|----------------|-------------|
| 1 | **Create success** | Of last N creates, what % finish with geometry OK and user Match? | PostHog `create_finished` (`geometryOk`) + `feedback_submitted` (`rating=match`) joined on `runId`; HITL JSONL | Weekly trend; break down by `quality` and `model` |
| 2 | **Ratings mix** | Match / Close / Wrong share and top failure tags | PostHog `feedback_submitted`; `/api/feedback`; dataset export | Tag Pareto: legs, proportions, joinery, … |
| 3 | **Critic usefulness** | Do likeness / photo-match rounds reduce Wrong? | Langfuse generations (`task`, latency) + PostHog `create_finished` (`likenessPenalty`, `iou`) | Compare Fast vs Balanced/Careful Wrong rate |
| 4 | **Unlabeled contacts** | Are touching parts getting joinery labels? | PostHog / `/api/events` `run_finished.unlabeledContacts` | Should trend down as joinery targeting ships |
| 5 | **Guide opens** | Do people open the build guide after a successful create? | PostHog `guide_opened` / `create_finished` | Funnel: create → Match → guide → export |
| 6 | **$ / success** | Anthropic $ per Match (or per geometry-OK create) | Langfuse usage on `proxy_messages` ÷ Match count for same `runId`s | Cost per successful create; watch Haiku vs Sonnet |

## Suggested PostHog insights
- Funnel: `create_started` → `create_finished` → `feedback_submitted` (rating = match)
- Trend: `export_stl`, `dataset_exported`, `joint_targeted`, `guide_opened` (weekly unique)
- Breakdown: `create_finished` where `geometryOk = false` by `quality`

## Suggested Langfuse views
- Traces filtered by tag `furniture` / `sessionId = runId` (one AI run = one session)
- Tree: `proxy-messages` → `generate-{task}` generations (inventory, design, revise, …)
- Generations by name with p50/p95 latency and token usage / cost
- Error rate on observations with `level = ERROR`

## Offline fallback
Ship → **Download HITL dataset** still answers (1)–(2) without PostHog/Langfuse. Proxy logs `{ kind: "proxy_messages", runId, ms, status }` cover latency when Langfuse keys are unset.
