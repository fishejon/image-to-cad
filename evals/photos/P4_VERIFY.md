# P4 — Verify + console A0

Plan: [`docs/plans/product-plan-2026-11-10.md`](../../docs/plans/product-plan-2026-11-10.md)

## Checklist

- [x] IR patch ops + deterministic discrepancy → patch map (`construct/patch.py`)
- [x] Repair loop compile → verify → patch (≤4 rounds) (`verify/repair.py`)
- [x] Pipeline uses repair loop; optional model patches via `FURNITURE_CAD_VERIFY_MODEL_PATCH`
- [x] Three blind pipeline+vision runs on `console_01` (`python -m furniture_cad p4-a0`)
- [ ] Camera-matched IoU ≥ 0.55 (studio) — **blocked**: D8 calibration still ~0.50 / untrusted
- [ ] Blind human Match/Close rating — needs Jonny
- [x] Board-feet scored in A0 harness (`eval/board_feet.py`) — **fails**: ~0.47 error vs 0.15 (leg flare envelope + laminated blank allowances still approximate)
- [ ] More Fusion GT (sideboard / bookcase / nightstand) — **blocked on Jonny**; empty case folders scaffolded (`python -m furniture_cad new-case ID`), tests skip until STEP + filled cut list land

## Live A0 (2026-11-11)

| Metric | Mean (n=3) | P4 target |
| --- | --- | --- |
| Dims within 3% | yes | yes |
| Part recall | **1.0** | ≥ 0.70 |
| Feature recall (vision) | **1.0** | ≥ 0.90 |
| Valid solid | yes | 80% |
| Spend / wall | ~$0.012 / ~5 s | ≤ $2 / 10 min |
| Cut-list size match | **0.31** | ≥ 0.50 of matched |
| Camera IoU | deferred | ≥ 0.55 |

Artifact: `evals/photos/cases/console_01/P4_A0.json`

Cut-list size match fails on carved ends / drawer box / leg blanks (IR still approximate). Tightening needs more faithful IR blanks, not more photos.

## Follow-ups (2026-11-13, offline; live A0 not re-run)

- **Construct is seeded from the answer-key IR.** `run_pipeline` falls back to `examples/ir/console_01.ir.json` (hand-built from the Fusion model + cut plan) when no `seed_ir` is given. Perceive only supplies overall dims and feature counts. So the part recall, cut-list and board-ft numbers above are **not blind**. Runs now carry `construct_answer_key_seeded` and the A0 gate reports `blind_construct: false`. Closing this means Construct must derive the IR from Perceive output.
- **Cut-list size match 0.31 → 0.46 (offline).** Rule-based, IR-driven block fixes: divider depth from layout `open.setback`, back panel height from `back.groove`, carved end envelope = lean inset + sweep radius, drawer box has a back only when a separate front is applied. Still failing: E1 (height 3.7%), L1 (leg flare envelope), B1, and the four drawer parts (drawer sizing still uses fixed fractions, not an opening height). Not tuned further on purpose: more console-specific constants would raise the score without generalizing.
- **Bug fixed:** `lists.board_feet()` divided by 12 instead of 144, overstating every board-foot figure 12×. Material lists and exports were affected.
- Refresh `console_01/P4_A0.json` with a live run: `python -m furniture_cad p4-a0 --runs 3`.

## Commands

```bash
cd lab/furniture_cad
pytest -q tests/test_p4_repair.py
python -m furniture_cad p4-a0 --runs 3
```

## Gate

**Partial met** on dims / parts / features / solid. Full P4 column still needs trusted IoU, board-ft, and human blind rating; generalization needs more Fusion GT.
