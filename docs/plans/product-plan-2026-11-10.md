# Image to CAD: Plan and Technical Specification

> **Status: ACTIVE.** Day-to-day sequencing for the wired IR pipeline.  
> Supersedes sequencing in [`product-plan-2026-11-08.md`](product-plan-2026-11-08.md) (D1–D6 still locked; that doc remains historical context).  
> Nov 10, 2026 · Jonny Fisher.

## Bottom line

Pieces exist; one measured pipeline does not. The tool loop is still the only live path. IR modules are unwired. The console GT (STEP + cut list) is good, but orthographic IoU against a 3/4 photo is an untrusted ruler (GT STL scored **0.179** vs agent **0.245**).

**Direction:** wire **Intake → Perceive → Dimension → Construct → Compile → Verify → Derive**; make the console expressible in IR v2; trust IoU only after D8 calibration.

## Locked decisions

| Id | Decision | Choice |
| --- | --- | --- |
| **D1–D6** | (Nov 8) | Still locked — IR+build123d, casegoods first, capture guidance, Fusion GT, $2 cap, blind operator |
| **D7** | IR expressiveness | IR describes **profiles and layouts**, not only boxes — console expressible from day one |
| **D8** | Metric trust | Metric trusted only if GT STEP scores **≥ 0.8** against its own photo (camera-matched) |
| **D9** | Escape hatch | `custom_part` = isolated subprocess build123d script, flagged **Guessed** |
| **D10** | Model output | Model proposes **IR patches**, never scripts, on the product path |
| **D11** | Compile | Every compile is deterministic, offline, tested vs GT with **no model call** |
| **D12** | Scaffolding | No new scaffolding until a gate is met; stubs labeled stubs |

### Section 11 answers (locked for execution)

| # | Question | Answer |
| --- | --- | --- |
| 1 | Ask for front-on photo? | **Yes** (extends D3) — required for D8 calibration |
| 2 | Who models GT / cadence? | **Jonny**, ~1 piece / 1–2 weeks (D4) |
| 3 | Next three casegoods? | **Sideboard, bookcase, nightstand** |
| 4 | `custom_part` on product path? | **Yes**, isolated + Guessed (D9) |
| 5 | Outside tester timing? | After **P4 gate**; P6 hardens before private beta |

## Staged bar (Tier 1)

| Metric | P4 gate (console) | Final bar |
| --- | --- | --- |
| Overall dims (one known size) | within 3% | within 3% on 90% |
| Part recall / precision | 0.70 | 0.85 |
| Cut-list size match | 0.50 of matched | 5 mm or 3% on 85% |
| Feature recall | 0.90 | 0.90 |
| Camera-matched IoU (studio) | 0.55 | 0.70 |
| Board-feet error | 15% | 10% |
| Valid solid in round limit | 80% | 90% |
| Median cost / time | $1.50 / 6 min (hard $2 / 10) | same |
| Blind human rating | Match or Close on console | majority Match or Close |

## Phases

| Phase | Name | Gate |
| --- | --- | --- |
| **P0** | Ruler and ground truth | Calibration: GT STEP ≥ 0.8 on front-on photo |
| **P1** | Console expressible | Golden compile vs `console_01.step`; part recall ≥ 0.85 |
| **P2** | One wired pipeline | Photo + known size → IR + model + lists via job server |
| **P3** | Real Perceive + Dimension | Feature recall 0.90; dims within 3% on studio |
| **P4** | Verify + console A0 | P4 column of staged bar; 3 blind runs |
| **P5** | Generalize | 10-piece set @ 70% of final bar; A beats B majority |
| **P6** | Hardening + product | Safe private beta; security review clean |
| **P7** | Chairs / curves | Conditional on P5; IoU ≥ 0.55 or label Approximate |

## Architecture (short)

Only **Perceive** and **Verify** call a model. Compile/Derive/Dimension/Intake are deterministic. Tool loop = flagged fallback. Full stage/IO table, IR v2 sketch, block library, jobs API, and budgets live in the source brief; implement phase-by-phase without expanding UI scaffolding (D12).

## Trackers

| Phase | Tracker |
| --- | --- |
| P0 | [`evals/photos/P0_RULER.md`](../../evals/photos/P0_RULER.md) |
| P1 | [`evals/photos/P1_CONSOLE.md`](../../evals/photos/P1_CONSOLE.md) |
| P2 | [`evals/photos/P2_PIPELINE.md`](../../evals/photos/P2_PIPELINE.md) |
| P3 | [`evals/photos/P3_PERCEIVE.md`](../../evals/photos/P3_PERCEIVE.md) |
| P4 | [`evals/photos/P4_VERIFY.md`](../../evals/photos/P4_VERIFY.md) |
| P5–P7 | add as each phase starts |

## Stop doing

Shop UI polish, new stubs without a gate, treating orthographic IoU on 3/4 cluttered photos as a product gate, expanding chair work before P5.
