# Phase 1 — Cut-list-first spike (tool-use CLI)

Plan: [`docs/plans/photo-to-cutlist.md`](../../docs/plans/photo-to-cutlist.md) · Recovery: [`docs/plans/photo-to-model-recovery.md`](../../docs/plans/photo-to-model-recovery.md)

**Status: TOOL-CALLING SMOKE ONLY (not a photo→model gate).**  
2026-11-07 “GATE PASSED” meant: offline oracle solids + lists, and a live Haiku run that called tools for **bookshelf parts+lists from a text prompt (no photo)**. That proves the Messages tool loop works. It does **not** prove photo accuracy.

## What actually landed

| Piece | Path |
| --- | --- |
| Helper / allowlist surface | `src/furniture_cad/allowlist.py` |
| Parts record | `src/furniture_cad/parts.py` |
| List builder | `src/furniture_cad/lists.py` |
| Tool contract | `contracts/tools.v1.json` |
| Handlers + loop | `src/furniture_cad/tools/` |
| **Oracle** scripts (was “freeze”) | `src/furniture_cad/tools/oracle_set.py` |
| Tests | `tests/test_phase1_lists.py`, `test_tools_runner.py`, `test_phase1_freeze.py` |

## Reinterpretation

- [x] Tool-use CLI can call `build` + `lists`
- [x] Oracle scripts export solids for the three-piece set
- [ ] Photo in the first message with image blocks — **R1**
- [ ] Lists derived from solids — **R2**

## Commands

```bash
cd lab/furniture_cad
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q tests/test_phase1_lists.py tests/test_tools_runner.py tests/test_phase1_freeze.py
python -m furniture_cad run --freeze-set --work out/oracle   # oracle scripts (alias --freeze-set)
```
