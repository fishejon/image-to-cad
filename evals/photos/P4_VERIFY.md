# P4 — Verify + console A0

Plan: [`docs/plans/product-plan-2026-11-10.md`](../../docs/plans/product-plan-2026-11-10.md)

## Checklist

- [x] IR patch ops + deterministic discrepancy → patch map (`construct/patch.py`)
- [x] Repair loop compile → verify → patch (≤4 rounds) (`verify/repair.py`)
- [x] Pipeline uses repair loop; optional model patches via `FURNITURE_CAD_VERIFY_MODEL_PATCH`
- [x] Three blind pipeline+vision runs on `console_01` (`python -m furniture_cad p4-a0`)
- [x] Construct derives IR from Perceive (generic casegood template) — `construct/from_observation.py`
- [ ] Camera-matched IoU ≥ 0.55 (studio) — **blocked**: D8 calibration still ~0.50 / untrusted
- [ ] Blind human Match/Close rating — needs Jonny
- [x] Board-feet scored in A0 harness (`eval/board_feet.py`)
- [ ] More Fusion GT (sideboard / bookcase / nightstand) — **blocked on Jonny**; empty case folders scaffolded

## Honest Construct baseline (offline, 2026-11-13)

Pipeline default no longer seeds `console_01.ir.json`. IR is built from Perceive counts + dims.

| Metric | Answer-key seed (golden) | From-observation (honest) | P4 target |
| --- | --- | --- | --- |
| Part recall | 1.0 | **0.77** | ≥ 0.70 |
| Cut-list size match | 0.46 | **0.15** | ≥ 0.50 |
| Board-ft err | ~0.47 | **~0.32** | ≤ 0.15 |
| Feature counts | drawer=2, leg=4 | same when Perceive supplies them | — |
| `blind_construct` | false | **true** | true |

Golden IR remains at `examples/ir/console_01.ir.json` for compile tests only (`seed_ir=`). Joinery blanks (LT/W1/R1) are IR-opt-in, not invented by the compiler.

## Commands

```bash
cd lab/furniture_cad
pytest -q
python -m furniture_cad p4-a0 --runs 3
```

## Gate

**Partial.** Blind Construct is on; console part recall still clears 0.70 offline. Cut-list size match and board-ft need block fidelity + repair against the honest IR. Full P4 still needs IoU, human rating, and more Fusion GT.
