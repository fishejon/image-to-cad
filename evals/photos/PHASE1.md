# Phase 1 — Cut-list-first spike (tool-use CLI)

Plan: [`docs/plans/photo-to-cutlist.md`](../../docs/plans/photo-to-cutlist.md) (option 1: Messages API tool-use on a worker)

**Status: GATE PASSED (2026-11-07).** Freeze-set solids + lists offline; live tool-use **5/5** within 3 rounds (Haiku); curved blanks on `chair_02`; `case_01` MCM qty hand-check vs photo inventory.

## Delivered in lab (`lab/furniture_cad`)

| Piece | Path |
| --- | --- |
| Helper / allowlist surface | `src/furniture_cad/allowlist.py` |
| Parts record | `src/furniture_cad/parts.py` |
| List builder | `src/furniture_cad/lists.py` |
| Tool contract | `contracts/tools.v1.json` |
| Handlers + loop | `src/furniture_cad/tools/` |
| Freeze scripts | `src/furniture_cad/tools/freeze_set.py` — `chair_04`, `chair_02`, `case_01` |
| Curved blanks | `examples/parts/chair_02_curved.json` |
| MCM case parts | `examples/parts/case_01_mcm.json` (photo inventory qty) |
| Worker image stub | `Dockerfile` |
| Tests | `tests/test_phase1_lists.py`, `test_tools_runner.py`, `test_phase1_freeze.py` |

## Gate checklist

- [x] Helper / allowlist surface for `build`
- [x] Parts record schema
- [x] List builder: cut + material summary + blank BF
- [x] Bookshelf fixture: **exact qty** (20 pieces / 10 types) and sizes within **5%** of gold cutList
- [x] Offline tool-use script: build → lists → measure on bookshelf fixture
- [x] Offline solid smoke: `seat_panel` via `build` → STL/STEP
- [x] Tool-use CLI produces valid solids for freeze set (`--freeze-set` → STL/STEP + lists for all 3)
- [x] Live scripts succeed within **3 rounds on ≥80%** — measured **5/5 (100%)** Haiku bookshelf parts+lists
- [x] Curved blank sizing smoke on `chair_02` parts (blank > finished; BF increases)
- [x] Hand-check `case_01` lists qty vs photo inventory (4 posts, 5 shelves, 2 sled feet; 31 pcs incl. rails)

## Commands

```bash
cd lab/furniture_cad
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q tests/test_phase1_lists.py tests/test_tools_runner.py tests/test_phase1_freeze.py
python -m furniture_cad run --freeze-set --work out/freeze
# live (ANTHROPIC_API_KEY in repo-root .env):
python -m furniture_cad run --work out/live --max-rounds 3 --prompt "…"
```
