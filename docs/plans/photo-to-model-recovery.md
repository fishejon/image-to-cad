# Photo to Model: Recovery and Next-Phase Plan

> **Status: ACTIVE (R0).** Supersedes “everything landed” claims in older Phase trackers.  
> Full product bar and R0–R7 sequence live here. Legacy phase docs are historical + corrected status only.

**Author:** Jonny Fisher · **Date:** 2026-11-08

## TLDR

Infrastructure is real; proof that an agent turns a photo into an accurate model + cut/material lists is missing. Measure the **live** loop (A), not hand-tuned oracle scripts (O). Classic Create remains baseline **B**. Critical path: **R0 → R1 → R2∥R3 → R4**. Do not expand shop UI before R4 reports.

## Labels (locked)

| Label | Meaning |
| --- | --- |
| **B** | Classic browser SPEC Create on the same photo |
| **O** | Oracle — hand-written scripts in `tools/oracle_set.py` (ceiling / answer key) |
| **A** | Live tool-use agent given photo + known size + materials brief only (blind protocol) |
| **A0** | Today’s live loop under that protocol (expected poor until R1) |

## Phase overview

| Phase | Name | Gate |
| --- | --- | --- |
| **R0** | Truth reset | Docs honest; blind protocol; B/O/A0 table committed |
| **R1** | Give the loop eyes | Blind E2E on 3 photos with real renders + numeric checks |
| **R2** | Lists from geometry | Derived lists match oracle within 5% / exact qty |
| **R3** | Helper library | Console, chair, case from helpers (no templates in default ns) |
| **R4** | Blind evaluation | Real gate + recorded decision |
| **R5** | Honest product wiring | UI runs real jobs; labels match behavior |
| **R6** | Hardening | Safe to expose to testers |
| **R7** | Coverage and quality | ≥20 pieces, cost tuned |

See the Nov 8 recovery note in chat / this file’s source for full task lists, metrics, risks, and decisions.

## Tracker

| Phase | Status |
| --- | --- |
| R0 | **In progress** — see [`evals/photos/R0.md`](../../evals/photos/R0.md) |
| R1–R7 | Not started |

## Product bar (blind eval ~10 pieces)

| Metric | Target |
| --- | --- |
| Key dims (one known size given) | Within 5% |
| Part count | Exact on ≥70% of pieces |
| Silhouette IoU (studio) | Mean ≥0.55 Close+, then 0.70 |
| Cut list vs hand build | Within 5% size, exact qty, **from geometry** |
| Valid solid in round limit | ≥80% of runs |
| Vs Classic Create (B) | Better on the majority |
| Cost / time | Median ≤$2 and ≤10 min |
| Dogfood | Majority Match or Close |

## Principles (short)

1. Measure the product, not the answer key.  
2. The loop must see (photo + its own renders; checks on real geometry).  
3. Geometry is the source of truth for lists.  
4. Say only what is true.  
5. Security before exposure.  
6. Generalize with helpers, not templates.

## Open decisions

1. Keep $25/day and $2/run caps once the loop sends images?  
2. Which ten pieces for the eval set, and who supplies real dims?  
3. Is image-to-mesh acceptable as a fallback if helpers fall short?  
4. Who runs the blind eval (separate from whoever tunes helpers)?  
5. Earliest tester access date (sets R6 deadline)?

## First ten days

Days 1–2: finish R0. Days 3–5: photo input + real render + check unit tests. Days 6–8: real check/compare + new system prompt + first blind runs. Days 9–10: record true A0; start R2 and R3 from failures.
