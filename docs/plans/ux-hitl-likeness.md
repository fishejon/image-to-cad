# Plan: UX clarity + HITL feedback (Path A)

## TLDR
- Split AI into **Create from image** vs **Revise**; `+` New opens Create with upload first.
- Replace opaque rounds/visual critic with **Quality** presets + explicit run/status messaging.
- Rename workspace pack actions; lighten right-rail labels.
- Capture post-generate **Match / Close / Wrong** feedback + failure tags; **Mark correct** saves an example bank used as few-shot on later generates (works with external Claude; no weight training yet).
- Out of scope for this slice: furniture-type specialists, Bedrock/open-model fine-tune, full guide joinery overhaul, generic topology critic (follow-on).

## Critical decisions
1. **Decision:** Create vs Revise as tabs inside `#aiBox`, not two modals. **Because:** One overlay, less chrome; empty docs default to Create. **Rejected:** Separate full-page routes (heavier for static app).
2. **Decision:** Quality presets map to rounds + default visual flag (Fast=1/off, Balanced=2/on, Careful=4/on). **Because:** Users understand “careful,” not “rounds.” Advanced can still override visual. **Rejected:** Keeping raw rounds as primary control.
3. **Decision:** Feedback + examples live in IndexedDB via `CAD.store` (separate record keys). **Because:** Same persistence story as workspace; exportable later. **Rejected:** Only localStorage (quota).
4. **Decision:** Path A only (prompt injection of past successes). **Because:** Anthropic API has no self-serve FT; dataset must exist before Bedrock/open FT. **Rejected:** Blocking UX on fine-tune infra.
5. **Decision:** Taxonomy stays category-agnostic (failure tags = proportions, count, section, topology, missing, extra, dimensions). **Because:** Product is not chair/MCM-specific.

## Tasks
- [x] **Plan file** — this doc — Verify: exists under `docs/plans/`
- [x] **Create/Revise split + New → Create** — `app.js`, `index.html` — Verify: empty project opens Create; revise tab disabled when no parts
- [x] **Quality + status** — `app.js`, `vision.js` log hooks — Verify: status shows inventory/geometry/photo-match skipped|ran|failed
- [x] **Packs + rail labels** — `index.html` — Verify: titles say Download/Restore all designs; tabs Inspect/Adjust/Move/Check/Ship/Spec
- [x] **Feedback store** — `store.js` — Verify: unit tests for quality + example bank helpers
- [x] **HITL UI + inject** — Inspect feedback card + `vision.run` pastExamples — Verify: rate after generate; mark correct; prompt contains SIMILAR PAST SUCCESS
- [x] **Tests** — `tests/run.js` — Verify: `node tests/run.js` (46 passed)

## Follow-on (not this PR)
- Generic topology/section inventory + unlabeled-contact critic
- Trusted joinery guide pages
- Dataset export for Bedrock Haiku / open VLM fine-tune

## Risks & rollback
- Few-shot injection can bloat prompts — cap at 1 example, truncate spec JSON.
- Feedback IDB failure falls back to no bank (generate still works).
