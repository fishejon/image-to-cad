# furniture_cad (offline lab)

**Not deployed** — no Create / Vercel / `vision.js` wiring.

## Start here

→ **[NOW.md](NOW.md)** — one photo → hand params → compile → score. That is the active work.

Long-term roadmap (parked): [docs/plans/parametric-synthesis.md](../../docs/plans/parametric-synthesis.md)

## Setup (once)

```bash
cd lab/furniture_cad
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick commands

```bash
source .venv/bin/activate
pytest -q
python -m furniture_cad export --demo box
python -m furniture_cad compile --template four_leg_chair \
  --params examples/programs/four_leg_chair_demo.json --out out/demo_chair
```

## Parts

1. **Libraries:** build123d + trimesh  
2. **Blocks:** `tapered_leg`, `seat_panel`, `rail`, `back_panel`, `back_mid_slat`, `winged_top_rail`, `rounded_cushion`  
3. **Templates:** `four_leg_chair` (`back_style`: `panel` \| `mcm_rails`, optional cushion), `stool`

## Failure → next block

```bash
python -m furniture_cad fail --kind missing_block --need bent_panel \
  --photo-id chair_01 --notes "why"
```

Then implement **one** block, test, review. Do not `eval` freeform model scripts in the default path.
