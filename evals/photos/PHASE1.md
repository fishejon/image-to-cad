# Phase 1 — Cut-list-first spike

Plan: [`docs/plans/photo-to-cutlist.md`](../../docs/plans/photo-to-cutlist.md)

**Note:** Phase 0 `case_01` photo is still open; Phase 1 list/allowlist work uses the bookshelf **SPEC cut-list fixture** and chair gold corpus so we are not blocked on photography.

## Delivered in lab (`lab/furniture_cad`)

| Piece | Path |
| --- | --- |
| Allowlist | `src/furniture_cad/allowlist.py` — blocks + build123d name surface; freeform via `experimental` |
| Parts record | `src/furniture_cad/parts.py` — `PartRecord` schema + load/dump |
| List builder | `src/furniture_cad/lists.py` — cut list, blanks, buy summary, board feet |
| CLI | `python -m furniture_cad lists --parts FILE [--out plan.json]` |
| Fixture | `examples/parts/bookshelf_parts.json` (from browser `CAD.cutList` on `examples/bookshelf.json`) |
| Tests | `tests/test_phase1_lists.py` |

## Gate checklist

- [x] Allowlisted API documented/enforced (import gate + block registry)
- [x] Parts record schema
- [x] List builder: cut + material summary + blank BF
- [x] Bookshelf fixture: **exact qty** (20 pieces / 10 types) and sizes within **5%** of gold cutList
- [ ] Hand-check lists vs a physical/catalog bookshelf photo (needs `case_01.jpg`)
- [ ] Claude→allowlisted script produces valid solids for freeze set (3 rounds / 80%) — next spike
- [ ] Curved blank sizing smoke on `chair_02` parts

## Commands

```bash
cd lab/furniture_cad
source .venv/bin/activate   # or: python3 -m venv .venv && pip install -e ".[dev]"
pytest -q tests/test_phase1_lists.py
python -m furniture_cad lists --parts examples/parts/bookshelf_parts.json --out out/bookshelf_plan.json
```
