# Phase 1 — Cut-list-first spike (tool-use CLI)

Plan: [`docs/plans/photo-to-cutlist.md`](../../docs/plans/photo-to-cutlist.md) (option 1: Messages API tool-use on a worker)

**Note:** Phase 0 `case_01` photo + Careful Create baseline B are in (`IoU 0.297 Wrong`). List gold still uses the drawer bookshelf **SPEC fixture** (`examples/parts/bookshelf_parts.json`) — different object than the MCM open case photo.

## Delivered in lab (`lab/furniture_cad`)

| Piece | Path |
| --- | --- |
| Helper / allowlist surface | `src/furniture_cad/allowlist.py` — blocks + build123d name surface (feeds `build` tool) |
| Parts record | `src/furniture_cad/parts.py` — `PartRecord` schema + load/dump |
| List builder | `src/furniture_cad/lists.py` — cut list, blanks, buy summary, board feet (`lists` tool) |
| CLI | `python -m furniture_cad lists --parts FILE [--out plan.json]` |
| Fixture | `examples/parts/bookshelf_parts.json` (from browser `CAD.cutList` on `examples/bookshelf.json`) |
| Tests | `tests/test_phase1_lists.py` |

## Tool-use runner (scaffolded)

| Piece | Path |
| --- | --- |
| Tool contract | `contracts/tools.v1.json` |
| Handlers | `src/furniture_cad/tools/handlers.py` — `build` / `lists` / `measure` live; `render` / `check` / `compare` stub |
| CLI | `python -m furniture_cad run …` (`tools/loop.py`) |
| Offline fixture | `examples/tools/bookshelf_offline.json` |
| Worker image stub | `Dockerfile` (limits env = Phase 0 freeze) |

- [x] CLI runner skeleton: offline `--script` + live `--prompt` Messages loop
- [x] `build(script)` executes helper-library scripts; tool errors → results (bad script = lost round)
- [x] Caps: rounds, tokens, spend, wall time (contract + env)
- [ ] Live model run on freeze set (chair_04, chair_02, case_01 when photo exists)
- [ ] `render` / `check` / `compare` beyond stubs (Phase 2)

## Gate checklist

- [x] Helper / allowlist surface for `build`
- [x] Parts record schema
- [x] List builder: cut + material summary + blank BF
- [x] Bookshelf fixture: **exact qty** (20 pieces / 10 types) and sizes within **5%** of gold cutList
- [x] Offline tool-use script: build → lists → measure on bookshelf fixture
- [x] Offline solid smoke: `seat_panel` via `build` → STL/STEP + lists (`examples/tools/seat_panel_solid.json`)
- [ ] Hand-check lists vs a physical/catalog bookshelf photo (needs `case_01.jpg`)
- [ ] Tool-use CLI produces valid solids for freeze set (3 rounds / 80%) — live model or authored scripts for chair_04 / chair_02 / case_01
- [ ] Curved blank sizing smoke on `chair_02` parts

## Commands

```bash
cd lab/furniture_cad
source .venv/bin/activate   # or: python3 -m venv .venv && pip install -e ".[dev]"
pytest -q tests/test_phase1_lists.py tests/test_tools_runner.py
python -m furniture_cad lists --parts examples/parts/bookshelf_parts.json --out out/bookshelf_plan.json
python -m furniture_cad run --contract
python -m furniture_cad run --work out/offline --script examples/tools/bookshelf_offline.json
# live (needs ANTHROPIC_API_KEY):
# python -m furniture_cad run --work out/live --prompt "Build an oak bookshelf from the fixture dims and emit lists."
```
