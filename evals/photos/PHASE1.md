# Phase 1 — Cut-list-first spike (tool-use CLI)

Plan: [`docs/plans/photo-to-cutlist.md`](../../docs/plans/photo-to-cutlist.md) (option 1: Messages API tool-use on a worker)

**Note:** Phase 0 `case_01` photo is still open; list work uses the bookshelf **SPEC cut-list fixture** and chair gold corpus so we are not blocked on photography.

## Delivered in lab (`lab/furniture_cad`)

| Piece | Path |
| --- | --- |
| Helper / allowlist surface | `src/furniture_cad/allowlist.py` — blocks + build123d name surface (feeds `build` tool) |
| Parts record | `src/furniture_cad/parts.py` — `PartRecord` schema + load/dump |
| List builder | `src/furniture_cad/lists.py` — cut list, blanks, buy summary, board feet (`lists` tool) |
| CLI | `python -m furniture_cad lists --parts FILE [--out plan.json]` |
| Fixture | `examples/parts/bookshelf_parts.json` (from browser `CAD.cutList` on `examples/bookshelf.json`) |
| Tests | `tests/test_phase1_lists.py` |

## Next (tool-use runner)

- [ ] CLI runner on worker image: model calls `build` / `render` / `measure` / `check` / `compare` / `lists`
- [ ] `build(script)` executes helper-library scripts; tool errors → model as results (bad script = lost round)
- [ ] Caps: rounds, tokens, spend, wall time
- [ ] Run on freeze set (chair_04, chair_02, case_01 when photo exists)

## Gate checklist

- [x] Helper / allowlist surface for `build`
- [x] Parts record schema
- [x] List builder: cut + material summary + blank BF
- [x] Bookshelf fixture: **exact qty** (20 pieces / 10 types) and sizes within **5%** of gold cutList
- [ ] Hand-check lists vs a physical/catalog bookshelf photo (needs `case_01.jpg`)
- [ ] Tool-use CLI produces valid solids for freeze set (3 rounds / 80%)
- [ ] Curved blank sizing smoke on `chair_02` parts

## Commands

```bash
cd lab/furniture_cad
source .venv/bin/activate   # or: python3 -m venv .venv && pip install -e ".[dev]"
pytest -q tests/test_phase1_lists.py
python -m furniture_cad lists --parts examples/parts/bookshelf_parts.json --out out/bookshelf_plan.json
```
