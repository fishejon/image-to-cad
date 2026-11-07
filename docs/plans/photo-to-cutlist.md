# Plan: Photo → model + cut/material lists

> **Status: ACTIVE.** Phase 0 partial (chairs baseline B done; `case_01` photo open). **Phase 1 in progress** — allowlist + parts + lists in `lab/furniture_cad` (Nov 2026).  
> Supersedes day-to-day sequencing in [`parametric-synthesis.md`](parametric-synthesis.md) (kept as long-term kernel notes).  
> Lab bespoke scripts remain the **gold corpus**; this plan is the **shop-grade Create track**.  
> Trackers: [`evals/photos/PHASE0.md`](../../evals/photos/PHASE0.md) · [`evals/photos/PHASE1.md`](../../evals/photos/PHASE1.md)

**Author:** Jonny Fisher · **Date:** 2026-11-07

## TLDR

Seven phases from baseline to photo-to-model with cut and material lists. **Phase 1 and Phase 2 decide whether to continue.** Current browser SPEC Create stays as **baseline B / dogfood fallback** until the new loop beats it on the same photos.

## Product intent

Photo in → shop-usable model **and** honest cut/material lists, with likeness good enough that you’d build from it.

## Order of risk

- **Phase 1** — Does the idea work? (valid solids + lists)
- **Phase 2** — How accurate is it? (IoU + part count vs Create)
- If Phase 2 misses its gate: fix the **loop and helper blocks**, not Phase 3 questions UI.

---

## Phase 0: Baseline (2–3 days)

- Freeze a test set of **three pieces:** two dining/side chairs and **one simple rectilinear case** (bookshelf). Console and a second case join in Phase 2.
- For each: photo, optional side photo, real dimensions.
- Run **current Create** on all three, plus any existing bespoke model; write scores into the photo pack. That is **baseline B**. The new loop is **baseline A** on the same photos.
- Pick sandbox host + secrets + **spend cap**. Use a **local or hosted container**, not the Vercel Hobby proxy (~5 min cuts off Careful; compile loops would hit sooner).
- **Gate:** baseline scores recorded; container host and spend cap chosen; **no list-builder work** before this is checked.

**Tracking:** [`evals/photos/PHASE0.md`](../../evals/photos/PHASE0.md)

---

## Phase 1: Cut-list-first spike (~1 week)

- Claude writes the build script against an **allowlisted build123d API** (parts, panels, sweeps, fillets, helper blocks), run by hand in a container. Freeform Python stays behind an experimental flag.
- Define the parts record (name, material, thickness, grain, how it’s made).
- List builder: cut list, material list, blank sizes for curved parts, board feet, waste.
- Hand-check lists against real/catalog dimensions.
- **Gate:** all three pieces → valid solids; lists within **5% on size**, **exact on quantity**; scripts succeed within **3 rounds on ≥80%** of runs.

---

## Phase 2: Loop and scoring (1–2 weeks)

- Automate sandbox (time/memory limits); return errors to Claude.
- Render front / side / iso (reuse STL IoU headless setup).
- Checker: bbox vs known dims, overlaps, silhouette IoU.
- Feedback loop with photo beside render; keep best; cache unchanged scripts.
- Expand to 5–6 pieces (add console + second case); repeatable eval.
- **Gate:** exact part count on **4 of 5**; IoU **≥ 0.55 (Close+)** on studio photos; **beats current Create** on the same photos. Raise IoU bar to **0.70** once fillet/helper coverage is in.

---

## Phase 3: Photo-to-spec with questions (~1 week)

- Intake: one known dimension, optional side photo, material brief.
- Read-first: Claude lists parts and what it can’t see.
- Question gate: 1–2 questions when scale or a hidden side is unknown.
- Assumptions list with the result.
- **Gate:** asks on every ambiguous photo and never on a clear one.

---

## Phase 4: Editable parts and lists (1–2 weeks)

- Named dimensions → edit size → rebuild.
- Parts table with live cut/material lists; stock sizes, species, waste.
- Export CSV, printable cut list, STEP, STL.
- **Gate:** dimension edit updates model + lists in **&lt; 5 s**.

---

## Phase 5: Integration and rollout (~1 week)

- New path behind a flag as main Create; keep current Create as dogfood fallback until the new loop wins on the same photos.
- Reuse telemetry + Match/Close/Wrong.
- Harden sandbox (isolation, rate limits, per-run spend cap).
- Docs/README with honest limits.
- **Gate:** majority of dogfood runs Match or Close.

---

## Phase 6: Hardening and coverage (ongoing)

- ≥20 pieces across chairs, tables, cabinets, shelving, organic shapes.
- Helpers from logged failures (e.g. two-profile tapered leg, tangent sweep) — building blocks, not templates.
- Multi-photo, plywood nesting, hardware lists, joinery guide on new parts.
- Cheaper model for repair rounds.

---

## Critical decisions (locked)

| Decision | Choice |
| --- | --- |
| Freeze set (Phase 0) | 2 dining/side chairs + 1 rectilinear case |
| Script policy | Allowlisted build123d API; freeform experimental only |
| IoU gate (Phase 2) | Close+ (0.55) first; Match (0.70) after helpers |
| Vercel proxy | Not for compile loops; container sandbox |
| Current Create | Baseline B + fallback through Phase 5 |
| Lab bespoke | Gold corpus / few-shot / tests — not the product path |

## Explicitly deferred until gates pass

- List builder before Phase 0 gate
- Questions UI before Phase 2 gate
- Retiring SPEC Create before new loop wins
- Multi-photo, CNC/DXF, printability report (fab backlog after likeness)
