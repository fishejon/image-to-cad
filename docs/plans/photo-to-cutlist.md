# Plan: Photo → model + cut/material lists

> **Status: ACTIVE.** Phase 0 done. **Phase 1 GATE PASSED** (freeze solids + lists; live 5/5 ≤3 rounds). **Next: Phase 2** — job service + IoU/accuracy vs Create (Nov 2026).  
> Architecture: **option 1** — Messages API tool-use loop in a worker; Vercel stays app / auth / job starter.  
> Supersedes day-to-day sequencing in [`parametric-synthesis.md`](parametric-synthesis.md) (kept as long-term kernel notes).  
> Lab bespoke scripts remain the **gold corpus**; this plan is the **shop-grade Create track**.  
> Trackers: [`evals/photos/PHASE0.md`](../../evals/photos/PHASE0.md) · [`evals/photos/PHASE1.md`](../../evals/photos/PHASE1.md)

**Author:** Jonny Fisher · **Date:** 2026-11-07 · **Revised:** tool-use worker (option 1)

## TLDR

Seven phases from baseline to photo-to-model with cut and material lists. **Phase 1 and Phase 2 decide whether to continue.** Current browser SPEC Create stays as **baseline B / dogfood fallback** until the new loop beats it on the same photos.

The model drives a **tool-use loop** on the Messages API inside a **worker container**. Tools build, render, measure, check, compare, list, and ask the user. Vercel does not run the loop.

## Product intent

Photo in → shop-usable model **and** honest cut/material lists, with likeness good enough that you’d build from it.

## Order of risk

- **Phase 1** — Does the idea work? (valid solids + lists via tool-use CLI)
- **Phase 2** — How accurate is it? (IoU + part count vs Create; job service)
- If Phase 2 misses its gate: fix the **loop and helper blocks**, not Phase 3 questions UI.

---

## Phase 0: Baseline (2–3 days)

- Freeze a test set of **three pieces:** two dining/side chairs and **one simple rectilinear case** (bookshelf). Console and a second case join in Phase 2.
- For each: photo, optional side photo, real dimensions.
- Run **current Create** on all three, plus any existing bespoke model; write scores into the photo pack. That is **baseline B**. The new loop is **baseline A** on the same photos.
- Choose the **worker host** and **job store** (small database or Redis), and how the worker reaches the model: call the **Messages API directly with its own key**, and report to existing **telemetry and Langfuse**.
- **Write the tool contract before any loop code:**
  - `build(script)` — compile/run a script against the helper library
  - `render(views)` — front / side / iso (and similar)
  - `measure(part)` — part dims / blanks
  - `check()` — bounding box, overlaps, silhouette IoU
  - `compare()` — photo against render
  - `lists()` — cut / material lists from the parts model
  - `ask_user(question)` — pause for a human answer (wired in Phase 3)
- **Runtime split:** Vercel stays the **app, auth, and job starter**. The loop runs in a **container** with limits on rounds, tokens, spend, and wall time — not on the Vercel Hobby proxy (~5 min already cuts off Careful).
- **Gate:** baseline scores recorded; worker host, job store, model-key path, and spend/wall-time caps chosen; **tool contract written**; no list-builder / loop code before this is checked (list builder may proceed once chairs baseline B exists — see Phase 1 tracker).

**Tracking:** [`evals/photos/PHASE0.md`](../../evals/photos/PHASE0.md)

---

## Phase 1: Cut-list-first spike (~1 week)

- Run the **tool-use loop from a command-line runner on the worker image**, on the three freeze pieces. The model calls the tools; `build` takes a script written against the **helper library** (parts, panels, sweeps, fillets) with sandbox limits (rounds / tokens / spend / wall time).
- Tool errors return to the model as **tool results** — a bad script costs a round, not a crash. (No separate “freeform experimental flag” path.)
- Define the parts record (name, material, thickness, grain, how it’s made).
- List builder: cut list, material list, blank sizes for curved parts, board feet, waste.
- Hand-check lists against real/catalog dimensions.
- **Gate:** all three pieces → valid solids; lists within **5% on size**, **exact on quantity**; scripts succeed within **3 rounds on ≥80%** of runs.

**Tracking:** [`evals/photos/PHASE1.md`](../../evals/photos/PHASE1.md)

---

## Phase 2: Loop and scoring (1–2 weeks)

- Turn the runner into a **job service**: `POST /jobs` starts a run; `GET /jobs/:id` or a stream reports status. **Vercel only starts the job and relays progress.**
- Save each job’s **project** (parts model, build script, renders, results) so a run can resume or be reused; **cache unchanged scripts**.
- Log every tool call and result to **Langfuse**, with round and spend per job.
- Expand to 5–6 pieces (add console + second case); repeatable eval.
- **Gate:** exact part count on **4 of 5**; IoU **≥ 0.55 (Close+)** on studio photos; **beats current Create** on the same photos. Raise IoU bar to **0.70** once fillet/helper coverage is in.

---

## Phase 3: Photo-to-spec with questions (~1 week)

- Intake: one known dimension, optional side photo, material brief.
- Read-first: Claude lists parts and what it can’t see.
- Question gate = **`ask_user` tool**: pauses the job and resumes when you answer (1–2 questions when scale or a hidden side is unknown).
- Assumptions list with the result.
- **Gate:** asks on every ambiguous photo and never on a clear one.

---

## Phase 4: Editable parts and lists (1–2 weeks)

- Named dimensions → edit size → **rerun the saved build with new values and call no model**. The model is used only for **structural** edits (e.g. “add a drawer”).
- Parts table with live cut/material lists; stock sizes, species, waste.
- Export CSV, printable cut list, STEP, STL.
- **Gate:** dimension edit updates model + lists in **&lt; 5 s**.

---

## Phase 5: Integration and rollout (~1 week)

- New path behind a flag as main Create; keep current Create as dogfood fallback until the new loop wins on the same photos.
- Reuse telemetry + Match/Close/Wrong.
- **Worker auth**, per-user rate limits, **spend cap per job**, and a **status view in the UI**.
- Docs/README with honest limits.
- **Gate:** majority of dogfood runs Match or Close.

---

## Phase 6: Hardening and coverage (ongoing)

- ≥20 pieces across chairs, tables, cabinets, shelving, organic shapes.
- Helpers from logged failures (e.g. two-profile tapered leg, tangent sweep) — building blocks, not templates.
- Multi-photo, plywood nesting, hardware lists, joinery guide on new parts.
- Cheaper model for repair rounds.
- **Scope tiers:** full model, shaped-blank fallback, ask for more.
- **Domain profiles** for lists beyond woodworking.
- **Mesh reference** as a fallback when B-rep helpers aren’t enough.

---

## Critical decisions (locked)

| Decision | Choice |
| --- | --- |
| Freeze set (Phase 0) | 2 dining/side chairs + 1 rectilinear case |
| Loop architecture | **Messages API tool-use in a worker** (option 1) |
| Worker host | **Local Docker (A)** — `lab/furniture_cad/Dockerfile` |
| Job store | **Postgres** (Phase 2; HITL-compatible) |
| Spend caps | **$25/day · $2/run**; rounds/tokens/wall in `contracts/tools.v1.json` |
| Tool contract | `build`, `render`, `measure`, `check`, `compare`, `lists`, `ask_user` → `lab/furniture_cad/contracts/tools.v1.json` |
| Script policy | Helper library inside `build`; bad scripts → tool errors → next round |
| IoU gate (Phase 2) | Close+ (0.55) first; Match (0.70) after helpers |
| Vercel role | App, auth, job starter / progress relay — **not** the compile loop |
| Worker | Container with round / token / spend / wall-time limits; own Anthropic key; Langfuse + telemetry |
| Current Create | Baseline B + fallback through Phase 5 |
| Lab bespoke | Gold corpus / few-shot / tests — not the product path |
| Dimension edits (Phase 4) | Rebuild saved script, **no** model call |

## Explicitly deferred until gates pass

- Full job service before Phase 1 CLI proves the loop
- Questions UI before Phase 2 gate (`ask_user` wired in Phase 3)
- Retiring SPEC Create before new loop wins
- Multi-photo, CNC/DXF, printability report (fab backlog after likeness)
