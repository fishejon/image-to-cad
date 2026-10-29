# Plan: Photo-faithful parametric synthesis

> **Status: PARKED long-term roadmap.**  
> Active work is only the one-photo loop: [`lab/furniture_cad/NOW.md`](../../lab/furniture_cad/NOW.md).  
> Do not execute Phase 2+ or expand this doc until that loop has ~5–10 scored chairs. Keep this file for future sequencing.

## TLDR
- Replace the **universal JSON box-boolean SPEC** as the primary accuracy path with **parametric programs** that call a **block library** (build123d solids) + **category templates**, then later **fit parameters to the photo**.
- **Near-term work is offline:** [`lab/furniture_cad/`](../../lab/furniture_cad/) — Python + build123d + trimesh. **Not wired to Create, Vercel, or the browser** until an explicit go/no-go.
- Keep the existing workspace, joinery guide, HITL, and telemetry as the **product shell + learning loop** (unchanged while the lab matures).
- Start with **chairs & stools** (dozen blocks + templates); grow blocks from `failure_log.jsonl`, not guesses.
- Explicitly **not** until lab exit: prod Create path, multi-category UI, org auth / private banks.

## Product north star
Upload furniture photos → get a **per-image parametric model** that **looks like that piece**, exposes editable dims, labels uncertainty, and is **shop-grade CAD** (STEP) — covering **any furniture** by growing blocks from failures, not one mega-template.

## Current baseline (what we keep)
| Layer | Role after this plan |
| --- | --- |
| Workspace / Inspect / Adjust / Ship | Unchanged UX shell (prod) |
| HITL Match/Close/Wrong + example bank | Primary human signal once bridged |
| `runId` + PostHog + Langfuse + Postgres/R2 | Measure synthesis/fit when wired |
| `evals/golden` inventory scorer | Secondary until photo eval exists |
| `SPEC_DOC` + `CAD.buildSpec` + box CSG | **Legacy prod path** until flagged bridge |
| `lab/furniture_cad` | **Active likeness strategy** (offline B-rep blocks + templates) |

## Critical decisions
1. **Decision:** Parametric programs call a **fixed block API** (not freeform CAD scripts in the default path), composed by **category templates**. **Because:** Chairs/continuous shells fail under box ops; allowlisted blocks stay testable and reviewable. **Rejected:** Enlarging `SPEC_DOC` / mesh ops until “enough.”
2. **Decision:** **build123d B-rep blocks first, offline in `lab/furniture_cad`**; browser/prod integration is a later bridge (export mesh/STEP → viewer or server compile). **Because:** Shop-grade solids and sweeps/lofts/fillets are the goal; Three.js one-offs proved the idea but are not the long-term kernel host. **Supersedes:** “Three.js mesh kernels first / OCC later.” **Rejected:** Blocking progress on a browser-only mesh library.
3. **Decision:** Lab uses **category templates** (e.g. `four_leg_chair`, `stool`) internally; product UI can stay category-agnostic (template choice hidden). **Because:** Recipes beat unconstrained part soup for v0 chairs. **Rejected:** Shipping a furniture-type picker in the UI now.
4. **Decision:** Grow the library from **failure logs** (`missing_block`, bad fit), not speculative catalogs. **Because:** Real photos tell you which block to write next. **Rejected:** Building every furniture kernel before testing chairs.
5. **Decision:** **Analysis-by-synthesis fit** comes after hand-param templates work on real photos. **Because:** Wrong topology cannot be fitted away. **Rejected:** Visual critic that only narrates mismatches back into JSON SPEC.
6. **Decision:** Dual path / feature flag for Create only **after** lab exit (chair/stool credible). **Because:** Nothing in prod until blocks+templates prove out. **Rejected:** Big-bang delete of `spec.js` or wiring Vercel now.
7. **Decision:** Bootstrap eval on **our own chair/stool photos** with hand params first; VLM photo→params later. **Because:** Validate geometry path before perception. **Rejected:** Waiting on partner STEP sets.

## Sequencing overview (do not reorder casually)

```text
LAB (out of prod) — see lab/furniture_cad/README.md
  L0  Python scaffold + demo export
  L1  Hand-written chair/stool blocks (build123d)
  L2  Templates (four_leg_chair, stool) + CLI compile
  L3  Failure log + LLM-assisted block drafts (review gate)
  L4  Local photo loop with hand params                 ← LAB EXIT
   ↓
Phase 2+  Program IR + LLM fills template params (still may be offline)
Phase 3   Camera + fit loop
Phase 4   Split critics + uncertainty
Phase 5   Bootstrap eval + telemetry events
Phase 6   Product integration (flagged Create)          ← SHORT-TERM PROD EXIT
Phase 7   Kernel growth beyond chairs + HITL refit
Phase 8   Multi-view + B2B infra
```

Lab phases L0–L4 replace the old “Phase 0–1 Three.js kernels” track. Each lab/phase has **entry criteria**, **ordered tasks**, and **exit / success criteria**. Prod Create must not change until Phase 6 go/no-go.

---

## Lab L0–L4 — Offline build123d

**Active checklist:** [`lab/furniture_cad/NOW.md`](../../lab/furniture_cad/NOW.md) (not this section).  
**Location:** [`lab/furniture_cad/`](../../lab/furniture_cad/)  
**Constraint:** No Create / Vercel / `vision.js` wiring.  
**Part 1:** build123d + trimesh. **Part 2:** block functions. **Part 3:** chair/stool templates.  
**Growth:** `failure_log.jsonl` → next block.

---

## Phase 0 — Foundations & contracts (prod bridge; after lab exit)

**Entry:** Lab L4 exit (chair/stool templates credible on local photos).  
**Goal:** Lock the Program IR and feature-flag contracts before any Create switch.

### Tasks
- [ ] **0.1 Write IR sketch in-repo** — Document `Program` / `Part` / `KernelCall` / `Param` / `Uncertainty` / `CameraGuess` JSON shapes in this plan’s appendix (or `docs/PROGRAM_IR.md` if it outgrows one page). Include: mm units, Y-up or Z-up choice matching current viewer, param bounds, `provenance: measured|inferred|assumed`. **Files:** `docs/plans/parametric-synthesis.md` (appendix) or `docs/PROGRAM_IR.md`. **Verify:** Doc merged; one example program for a simple table and one for a bent chair shell.
- [ ] **0.2 Feature-flag contract** — Define `CAD.flags.synthesisPath` (or URL/`localStorage` toggle) and event names for PostHog/Langfuse (`synthesis_started`, `kernel_compile_ok`, `fit_round`, `fit_converged`, `critic_visual_pass`, `critic_geo_fail`). **Files:** `src/core/analytics.js`, `docs/plans/telemetry-dashboard.md` (link new metrics). **Verify:** Flag defaults **off**; flipping does not change Create behavior yet.
- [ ] **0.3 Dual-path ADR note** — Record: Create may emit `program` + compiled meshes; legacy `object`/`params` still produced via adapter when possible for Adjust/joinery; when adapter fails, Adjust shows synthesis params only. **Verify:** Written under Critical decisions / appendix; no code required beyond flag stub.
- [ ] **0.4 Sunset policy for JSON builder** — Stop investing in new `SPEC_DOC` mesh ops for likeness; only bugfixes and joinery. Track as: new likeness bugs → kernel ticket, not SPEC patch. **Verify:** One sentence in this plan + issue/label convention agreed in Critical decisions (done here).

### Phase 0 success criteria
- [ ] IR examples exist for ≥2 morphologies (rectilinear + continuous shell).
- [ ] Flag + event name list frozen (renames after Phase 5 require a migration note).
- [ ] Team can answer: “What does a successful Create return — `program` blob + meshes + paramDefs?”

### Risks & rollback
- Over-specifying IR early → keep appendix minimal; extend only when a kernel needs a field.
- Rollback: delete flag stub; no user-visible change.

---

## Phase 1 — Block library (SUPERSEDED by lab L1–L2)

**Status:** Implemented offline as build123d blocks + templates under [`lab/furniture_cad/`](../../lab/furniture_cad/), not as `src/kernels/` Three.js modules.  
**Do not** re-create a parallel browser kernel pack unless a bridge ADR says so. Chair/stool v0 blocks: `tapered_leg`, `seat_panel`, `rail`, plus further blocks driven by the failure log.

---

## Phase 2 — Program IR + LLM synthesizer

**Entry:** Phase 1 exit (demos compile).  
**Goal:** From image (+ optional inventory), LLM emits a **Program** that only references catalog kernels — not freeform Three.js source text in production.

### Tasks
- [ ] **2.1 Strict Program schema** — JSON Schema or AJV-like validation: parts[], each `{ id, kernel, args, parent?, transform }`, top-level `params[]` with bounds, `assumptions[]`, `uncertainty[]`. Reject unknown kernels. **Files:** `src/ai/programSchema.js` (or shared). **Verify:** Valid demo programs pass; mutated bad programs fail with clear errors.
- [ ] **2.2 Inventory retarget (light)** — Keep inventory call but reshape prompt toward: object identity, part roles, continuity, dominant section, rough aspect — **stop requiring inventory to drive box joinery tags**. Output feeds synthesizer, not SPEC builder. **Files:** `src/ai/vision.js` (`buildInventoryPrompt`) or new `src/ai/synthesize.js`. **Verify:** Inventory still returns JSON; structure fields usable for kernel-pack hints.
- [ ] **2.3 Synthesizer prompt + tool** — New task `synthesize_program`: system prompt lists catalog schemas (truncated), few-shot with Phase 1 demos, requires reasoning + assumptions. Prefer **structured output** / tool call over “write Three.js.” **Files:** `src/ai/synthesize.js`, prompts colocated. **Verify:** Unit test with mocked LLM returns fixture program that compiles.
- [ ] **2.4 Safe compile gate** — After LLM response: validate → compile → if fail, one repair round with compiler errors (not visual yet). Cap tokens/parts. **Verify:** Broken kernel name repaired or run fails soft with user-visible message; never `eval` raw JS from the model in the default path.
- [ ] **2.5 Langfuse task tags** — Trace `task=synthesize_program` and `task=repair_program` with `runId`, kernel ids used, compile_ok. **Files:** proxy metadata already supports `task`; client must send it. **Verify:** Local/dev Langfuse (or log line) shows spans when proxy used.
- [ ] **2.6 Offline/mock path** — For CI: fixture image → fixture program (no network). **Verify:** `node tests/run.js` covers validate+compile without API keys.

### Phase 2 success criteria
- [ ] On ≥5 diverse reference images (manual), synthesizer produces programs that **compile** ≥80% of the time (repair round allowed).
- [ ] Zero production path that `eval`s model-authored JavaScript (raw JS only allowed in an explicit experimental flag, default off).
- [ ] Compiled meshes appear in viewer with paramDefs for main dims.
- [ ] “Looks right” is **not** yet required (that’s Phase 3–4); compile reliability is the gate.

### Risks & rollback
- Model invents kernels → catalog allowlist + repair; if repair fails, fall back to legacy JSON path with user notice.
- Prompt bloat from full catalog → send pack subset once triage exists (Phase 7); until then send full v0 catalog (small).
- Rollback: flag off; Create uses legacy vision.run.

---

## Phase 3 — Camera + analysis-by-synthesis fit loop

**Entry:** Phase 2 exit (compile reliability).  
**Goal:** Numerically adjust **program params** (and optionally camera) so the render matches the photo better — without rewriting topology every round.

### Tasks
- [ ] **3.1 Offscreen render hook reuse** — Factor existing Create visual-critic render (`o.render`) into a shared `CAD.renderProgram(program|compiled, camera) → png/dataURL` usable by fit and critics. **Files:** `src/ui/app.js` / viewer helpers, `src/ai/vision.js` consumers. **Verify:** Same silhouette pipeline can consume synthesis renders.
- [ ] **3.2 Camera guess v0** — From inventory aspect + photo, estimate weakly-calibrated camera (orbit yaw/pitch/FOV or three.js PerspectiveCamera extras). Persist on run as `cameraGuess`. Document limitations (single view scale ambiguity). **Verify:** Unit/smoke: known synthetic render recovers yaw within loose tolerance; on real photos, camera at least places object fully in frame.
- [ ] **3.3 Error metrics** — Implement silhouette IoU (reuse) + edge/chamfer distance or gradient-magnitude overlap on downscaled images. Return scalar `fitError` + breakdown. **Files:** new `src/ai/fitMetrics.js` or extend vision likeness helpers. **Verify:** Identical image → error ≈ 0; obviously wrong scale → higher error; tests with two fixtures.
- [ ] **3.4 Parameter subset for fit** — Mark params `fittable:true` (overall scale, key widths/heights, shell bend, seat depth). Exclude discrete counts/topology. **Verify:** Catalog/program marks; optimizer only touches fittable set.
- [ ] **3.5 Optimizer v0** — Derivative-free search (coordinate descent / Nelder-Mead / random search — pick simplest that moves error). Budget: N evals (e.g. 30–80) per Create. Log each round: params, fitError, ms. **Files:** `src/ai/fit.js`. **Verify:** Starting from intentionally wrong scale on a synthetic pair, error decreases ≥30% within budget.
- [ ] **3.6 Scale / ambiguity handling** — If no absolute scale cue, fit **relative** proportions; set overall scale from user hint, default furniture heuristic, or leave `uncertainty: scale=assumed`. **Verify:** Documented behavior; UI surfaces assumed scale.
- [ ] **3.7 Stop conditions** — Stop on: error plateau, budget exhausted, or error below threshold τ. Emit `fit_converged` vs `fit_budget`. **Verify:** Events fire; status log readable in Create UI.

### Phase 3 success criteria
- [ ] On synthetic “render as photo” tests, fit recovers major dims within tolerance (define per demo: e.g. ±5% on height/width).
- [ ] On ≥5 real photos with hand-authored **correct topology** programs, post-fit silhouette IoU improves vs pre-fit by a documented margin (target: +0.1 IoU or 20% relative error drop — tune once baseline measured).
- [ ] Fit never changes part counts / kernel ids (topology stable).
- [ ] Median fit wall time acceptable for Careful quality (document target, e.g. <60s on laptop with ≤80 renders); Fast quality uses fewer evals.

### Risks & rollback
- Local minima → multi-start from inventory aspect; keep budget hard-capped.
- Browser jank → run fit in chunks with `await` yields; allow cancel.
- Rollback: skip fit; show unfitted compile (still better than nothing).

---

## Phase 4 — Split critics + uncertainty / questions

**Entry:** Phase 3 exit (fit improves metrics on fixtures).  
**Goal:** Separate **visual pass/fail** from **geometry hygiene**; ask the user only when uncertainty is high-impact.

### Tasks
- [ ] **4.1 Visual critic (photo-only)** — Inputs: reference + post-fit render (+ fitError). Output: `{ pass, issues[], suggestedParamTweaks? }` — **does not** demand SPEC rewrite. May trigger **one** limited re-fit or param nudge list, not full resynthesis by default. **Files:** `src/ai/critics/visual.js`. **Verify:** Fixture pass/fail; Langfuse generation tagged `critic_visual`.
- [ ] **4.2 Geometry critic (cheap)** — Mesh-level: NaN, empty geom, extreme aspect, part intersections rough check, floating parts (bbox gaps). No joinery labels required on synthesis path yet. **Files:** `src/ai/critics/geo.js` or reuse `checks.js` subsets. **Verify:** Unit tests for empty/NaN fail; clean demo passes.
- [ ] **4.3 Critic orchestration** — Order: compile → fit → geo critic → visual critic. Geo fail → repair/resynth topology (Phase 2 repair); visual fail → fit again or ask user. **Verify:** Integration test with mocks for each branch.
- [ ] **4.4 Uncertainty model** — Every important dim: `measured|inferred|assumed`. Hidden backs, cushions thickness, exact joinery → assumed by default. **Verify:** Program JSON includes uncertainty; Inspect UI lists assumptions.
- [ ] **4.5 Question gate** — If high-impact uncertainty (e.g. missing rear stretcher vs slab back, scale unknown and export requested), surface 1–3 multiple-choice questions before finalize. **Files:** Create UI in `app.js`. **Verify:** Manual: ambiguous photo shows questions; clear photo skips.
- [ ] **4.6 HITL alignment** — On Wrong/Close, require failure tags; map tags → kernel gap vs fit vs inventory for later Phase 7 clustering. **Verify:** Tags stored with `runId` as today; optional `path:synthesis` field on feedback.

### Phase 4 success criteria
- [ ] Visual and geometry critics are independently toggleable in Quality/advanced.
- [ ] A run can **pass geo + fail visual** (and vice versa) with distinct status strings (no overloaded “photo match skipped”).
- [ ] Assumptions visible in Inspect; at least one question type implemented (scale or back-structure).
- [ ] No regression: legacy JSON path still works with flag off.

### Risks & rollback
- Question fatigue → max 3; skip on Fast quality.
- Rollback: critics log-only; do not block Ship.

---

## Phase 5 — Bootstrap eval + telemetry

**Entry:** Phase 4 critics wired (even if thresholds soft).  
**Goal:** Measure the new path with **our photos**, not partner CAD.

### Tasks
- [ ] **5.1 Curate eval pack v0** — 10–20 images spanning: rectilinear case good, table, continuous chair/shell, mixed, soft seating, open shelf. Store under `evals/photos/` (or consented R2) with sidecar JSON: notes, expected morphology tags. **Verify:** README lists each image and why it’s hard; license/consent noted.
- [ ] **5.2 Scoring script** — `npm run score:synthesis` (or extend `score-golden`): for each image, run synthesize+fit (mockable), record compile_ok, fitError, IoU, critic flags, $ / latency if available. **Files:** `tools/score-synthesis.js`, fixtures. **Verify:** Script runs offline on fixtures; CI can run mock mode.
- [ ] **5.3 Human rubric** — Spreadsheet or markdown checklist: Match/Close/Wrong after fit; topology correct Y/N; editable params useful Y/N. Run once as baseline before Phase 6 launch. **Verify:** Baseline numbers checked into `evals/photos/BASELINE.md` (qualitative OK).
- [ ] **5.4 PostHog funnels** — Events from Phase 0 firing on real Create synthesis path; dashboard doc updated with north-star: % Match, compile rate, median fitError, $ / Match. **Files:** `docs/plans/telemetry-dashboard.md`. **Verify:** Test event appears in PostHog Activity when key set.
- [ ] **5.5 Langfuse session** — Full Create = one `sessionId=runId` with inventory → synthesize → fit rounds → critics. **Verify:** Trace tree readable; images masked as today.
- [ ] **5.6 Compare vs legacy** — On the same 10–20 images, run legacy JSON path once; record HITL + IoU. **Verify:** `BASELINE.md` includes side-by-side; synthesis need not win every case yet but must win **continuous/shell** cases.

### Phase 5 success criteria
- [ ] Eval pack ≥10 images with documented baseline.
- [ ] Automated mock score runs in CI.
- [ ] Side-by-side shows synthesis **clearly better** on ≥ the continuous/shell subset (human Match/Close or IoU).
- [ ] Telemetry answers: “Did fit run, how many evals, did visual critic pass, what did user rate?”

### Risks & rollback
- Image consent → only use owned/licensed photos; no silent upload beyond existing opt-in.
- Rollback: scoring stays local; no product flag flip.

---

## Phase 6 — Product integration (short-term exit)

**Entry:** Phase 5 baseline shows synthesis wins on hard continuous cases.  
**Goal:** Users can Create via synthesis+fit behind a flag (then default-on when stable).

### Tasks
- [ ] **6.1 Create path switch** — When flag on: Create runs Phase 2–4 pipeline; status log mirrors inventory / compile / fit / critics. **Files:** `src/ui/app.js`, `src/ai/synthesize.js`, `src/ai/fit.js`. **Verify:** Manual Create on chair photo produces shell-like mesh, not stick-box approximation.
- [ ] **6.2 Param Adjust bridge** — Adjust tab edits `paramDefs` from program; recompile (+ optional quick re-fit). **Verify:** Slider changes visible geometry.
- [ ] **6.3 Export bridge** — Ship STL/zip from compiled meshes (assembled + per-part). Guide/joinery may be limited — show honest empty state if no exact solids. **Verify:** STL downloads; messaging clear when joinery guide unavailable.
- [ ] **6.4 Legacy fallback** — On repeated compile failure, offer “Try classic builder” (JSON path). Log `synthesis_fallback`. **Verify:** Fallback works; event fires.
- [ ] **6.5 Quality presets mapping** — Fast: 1 synth attempt, low fit budget, critics off; Balanced: fit + geo; Careful: fit + geo + visual + questions. **Verify:** Presets change logs/budgets as documented.
- [ ] **6.6 Default-on gate** — Only after ≥1 week flagged use or internal dogfood checklist: flip default on for Create; keep escape hatch. **Verify:** Written go/no-go using Phase 5 metrics + dogfood notes.

### Phase 6 success criteria (SHORT-TERM EXIT)
- [ ] Flagged (or default) Create uses kernels + fit for photo furniture.
- [ ] Continuous chair/shell likeness **materially** beats legacy JSON on eval pack + dogfood.
- [ ] Users can nudge params and recompile; export meshes.
- [ ] Telemetry + HITL cover the new path.
- [ ] Joinery-guide gaps are explicit, not silently wrong.

### Risks & rollback
- Feature flag off restores legacy Create immediately.
- Do not delete JSON path in this phase.

---

## Phase 7 — Medium-term: coverage, triage, HITL refit

**Entry:** Phase 6 short-term exit.  
**Goal:** “Any furniture” via **failure-driven kernels** and better routing — still mesh-first.

### Tasks
- [ ] **7.1 Failure clustering** — Monthly (or per 20 Wrong ratings): group HITL tags + kernel ids + notes; file kernel tickets. **Verify:** First clustering note in `evals/` or plan checkbox update.
- [ ] **7.2 Kernel pack growth** — Add kernels only from clusters (examples: drawer box, hinged door panel, slat array, stone slab, wire/metal tube). Cap batch size (e.g. +3–5 kernels per cycle). **Verify:** Each new kernel has tests + catalog entry + ≥1 eval image.
- [ ] **7.3 Soft triage** — Lightweight classifier or inventory heuristic selects **catalog subset** (rectilinear vs continuous vs soft) to shrink prompts — UI stays category-agnostic. **Verify:** Wrong pack still recoverable via full-catalog repair; token use drops on common cases.
- [ ] **7.4 HITL refit UX** — “Reject part”, “pin this dimension”, “refit from here.” Persist pins in program. **Verify:** Pin survives re-fit; rejected part triggers local resynth.
- [ ] **7.5 Second-view prompt** — When visual critic fails twice, ask for optional side/back photo (store on run if consent). **Verify:** UI path exists; single-view still works if declined.
- [ ] **7.6 Eval pack → 50–100** — Expand photos; weekly `score:synthesis`; demote inventory-only golden as primary bar. **Verify:** Weekly job doc’d; primary metric is synthesis score + HITL.
- [ ] **7.7 Example-bank few-shot for programs** — Path A injects past **successful programs** (not SPEC JSON) into synthesizer. **Verify:** Mark-correct stores program summary; prompt includes it.

### Phase 7 success criteria (MEDIUM-TERM EXIT)
- [ ] Broad morphology coverage: case goods, tables, shelving, upholstered/continuous seating, at least one “weird” cluster addressed with a new kernel.
- [ ] Eval ≥50 images; weekly score trend readable.
- [ ] Honest assumed labels + optional second view when needed.
- [ ] Median user Match+Close rate improved vs Phase 6 baseline (document target after baseline, e.g. +15 pts).

### Risks & rollback
- Kernel explosion → require cluster evidence before adding.
- Few-shot program injection size → truncate aggressively (same as SPEC Path A).

---

## Phase 8 — Long-term: shop CAD + multi-view + B2B

**Entry:** Phase 7 medium-term exit (likeness credible).  
**Goal:** Photo-faithful **and** manufacturable; orgs can run private eval.

### Tasks
- [ ] **8.1 B-rep backend spike** — Map subset of kernels (`box_panel`, `rail`, `tapered_leg`, simple joints) to CadQuery/OCC or equivalent; emit STEP. Keep mesh kernels for sculpted parts. **Verify:** Spike repo/tool exports STEP that opens in a CAD tool for a rectilinear table.
- [ ] **8.2 Dual backend IR** — Same Program compiles to `mesh` and/or `brep` with capability matrix per kernel. **Verify:** Capability table documented; UI shows which parts are shop-exact.
- [ ] **8.3 Joinery remapping** — Reattach trusted joinery guide to B-rep/exact parts; synthesis path gains unlabeled-contact checks where exact. **Verify:** Guide pages generate for stick-built assemblies again.
- [ ] **8.4 Multi-view / scale references** — Ingest 2nd photo or credit-card/tape scale; tighten camera+scale. **Verify:** Eval subset with scale cue reduces scale uncertainty rate.
- [ ] **8.5 Domain critic** — Makeable / printable / wood-movement heuristics on B-rep parts. **Verify:** Flags absurd stock sizes; tests for thresholds.
- [ ] **8.6 Telemetry Phase 4** — Auth, `org_id`, private example banks, retention/delete-my-data (from `telemetry-analytics.md`). **Verify:** Per that plan’s Phase 4 checkboxes.
- [ ] **8.7 Partner / measured benchmarks** — Optional measured dims or partner CAD where available; report photo IoU **and** dim error. **Verify:** Benchmark harness separate from photo-only pack.

### Phase 8 success criteria (LONG-TERM EXIT)
- [ ] Core stick-built categories: STEP + cut-list-grade dims with known uncertainty.
- [ ] Sculpted parts: still photo-faithful meshes until B-rep catches up — labeled as visual-only.
- [ ] Multi-view/scale optional but clearly better when provided.
- [ ] Orgs can store private programs/examples and delete data.
- [ ] Product claim shifts from “looks like the photo” to “looks like the photo **and** builds” for advertised categories.

### Risks & rollback
- OCC in browser vs server — prefer **server-side** B-rep compile; mesh path stays client-first.
- Rollback: mesh-only synthesis remains the customer path; STEP is progressive enhancement.

---

## Cross-cutting engineering rules
1. **No raw `eval` of model code** on the default path (Phase 2).
2. **Topology vs continuous params:** LLM owns discrete structure; optimizer owns fittable floats (Phase 3).
3. **Every Create has a `runId`** linking HITL ↔ PostHog ↔ Langfuse ↔ program artifact.
4. **Flag-first:** Phases 1–5 can merge dark; Phase 6 is first user-visible Create switch.
5. **Likeness bugs → kernel or fit ticket**, not more `SPEC_DOC` rules (Phase 0.4).
6. **Tests:** kernels and fit metrics in `tests/`; LLM paths mocked in CI.

## Dependencies between workstreams

| Workstream | Blocks | Parallelizable with |
| --- | --- | --- |
| Kernel lib (P1) | P2–P3 | Telemetry dash polish, eval photo gathering (early P5 curation) |
| Synthesizer (P2) | P3–P4 | Camera research spikes |
| Fit loop (P3) | P4 visual critic quality | Geo critic (P4.2) |
| Critics/uncertainty (P4) | P6 UX questions | Eval curation (P5.1) |
| Eval+telemetry (P5) | P6 go/no-go | Dogfood |
| Product flag (P6) | P7 | — |
| Kernel growth (P7) | P8 B-rep mapping priorities | HITL refit UX |
| B-rep / B2B (P8) | — | Multi-view can start late P7 |

## Risks & rollback (global)
- **Likeness still fails after fit** → check topology (wrong kernels) before tuning optimizer; resynth with tighter inventory, don’t only crank eval budget.
- **Cost explosion** (fit renders × LLM) → Quality presets hard-cap; prefer Haiku for repair; cache renders by param hash.
- **Joinery regression** → expected until P8; communicate in UI; keep legacy path for shop-minded users.
- **IR churn** → version `program.schemaVersion`; migrations when breaking.
- **Emergency rollback:** `synthesisPath=false` → full legacy Create/Revise.

## Definition of done by horizon

| Horizon | Done means |
| --- | --- |
| Short-term (through P6) | Photo-faithful parametric Create via kernels+fit; beats JSON on continuous furniture; telemetry+HITL on; joinery optional/honest. |
| Medium-term (P7) | Failure-grown kernels cover most furniture morphologies; 50–100 image weekly score; HITL refit + optional 2nd view. |
| Long-term (P8) | B-rep/STEP for stick-built; multi-view/scale; org auth/private banks; dual claim photo + build. |

---

## Appendix A — Program IR sketch (v0)

```json
{
  "schemaVersion": 1,
  "domain": "furniture",
  "units": "mm",
  "params": [
    { "id": "overall_w", "value": 600, "min": 200, "max": 2000, "fittable": true, "provenance": "inferred" },
    { "id": "seat_h", "value": 420, "min": 300, "max": 550, "fittable": true, "provenance": "inferred" }
  ],
  "parts": [
    {
      "id": "shell",
      "kernel": "bent_shell",
      "args": { "outline": "...", "thickness": 12, "bendAngle": 85 },
      "transform": { "pos": [0, 0, 0], "rotDeg": [0, 0, 0] }
    },
    {
      "id": "leg_fl",
      "kernel": "tapered_leg",
      "args": { "h": "seat_h", "topSize": 35, "botSize": 25, "section": "round" },
      "transform": { "pos": [-250, -250, 0], "rotDeg": [0, 0, 0] }
    }
  ],
  "assumptions": ["Rear stretcher not visible; omitted"],
  "uncertainty": [
    { "about": "overall_w", "level": "inferred", "reason": "single view, no scale cue" }
  ],
  "cameraGuess": { "yaw": 35, "pitch": 20, "fov": 35, "distance": 1800 },
  "reasoning": "..."
}
```

## Appendix B — Event names (freeze in Phase 0)

```text
synthesis_started   { runId, quality, domain }
inventory_done      { runId, morphologyHints? }
program_compiled    { runId, ok, kernelIds[], partCount, error? }
fit_round           { runId, i, fitError, iou?, ms }
fit_finished        { runId, converged, evals, fitError, iou? }
critic_geo          { runId, pass, issues[] }
critic_visual       { runId, pass, issues[] }
question_asked      { runId, kind }
synthesis_fallback  { runId, reason }
create_finished     { runId, path: "synthesis"|"legacy", rating later via feedback }
```

## Appendix C — Mapping from old pipeline

| Old (`vision.js`) | New |
| --- | --- |
| `buildInventoryPrompt` | Morphology / part-tree hints for synthesizer |
| `buildPrompt` + `SPEC_DOC` | `synthesize_program` + kernel catalog |
| Builder/critic JSON rounds | Repair compile errors; fit owns dims |
| Visual critic (re-ask LLM) | Fit metrics + visual critic pass/fail |
| `CAD.buildSpec` | `CAD.compileProgram` |
| Staged carcass/interiors/refine | Optional later for large case goods; not required for v0 chair |
| Joinery + `checks.unlabeledContacts` | Legacy / Phase 8 B-rep |

## Appendix D — Suggested calendar (indicative, not commits)

| Window | Focus |
| --- | --- |
| Weeks 1–2 | P0 + P1 kernels + demos |
| Weeks 3–4 | P2 synthesizer + safe compile |
| Weeks 5–6 | P3 camera + fit |
| Weeks 7–8 | P4 critics/uncertainty + P5 eval baseline |
| Weeks 9–10 | P6 flagged Create + dogfood → go/no-go |
| Months 3–6 | P7 kernel growth + HITL refit |
| Months 6–18 | P8 B-rep, multi-view, B2B |

Adjust dates after P1 demo sign-off; **phase exits beat the calendar**.
