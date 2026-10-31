# NOW — designer-led model (not param ping-pong)

**Parked:** generic `four_leg_chair` JSON tweaking for likeness. It improves knobs; it does not produce a designed chair.

**Active approach:** furniture-designer construction brief → **one bespoke build123d script per reference chair** → only later extract shared blocks from patterns that actually worked.

Long-term product roadmap (still parked): [docs/plans/parametric-synthesis.md](../../docs/plans/parametric-synthesis.md)

## Why the old loop stalled

A high-end wooden chair is a **joined assembly with intentional curves**, not a pile of independent boxes. Feedback like “rails don’t meet,” “stile inflection,” “top rail is a curved oval / crescent” is **design geometry**, not missing float parameters. A generic template cannot absorb that without becoming the bespoke model anyway.

## New loop (per photo)

1. **Read the piece** (front / side / plan in the mind’s eye): members, where they land, joinery faces, curve character.
2. Write a short **construction brief** under `evals/photos/chairs/chair_NN.brief.md`.
3. Implement **`examples/bespoke/chair_NN.py`** — one script that builds *this* chair (build123d), not template params.
4. Export STEP/STL; compare to photo; fix the **script** (construction), not a JSON soup.
5. After 2–3 good bespoke chairs, note recurring shapes → *then* promote to blocks.

## chair_02 status

- Brief: `evals/photos/chairs/chair_02.brief.md`
- Bespoke model: `examples/bespoke/chair_02.py` → `out/chair_02_bespoke/chair_02.stl`
- Gauntlet: R1 LOSE (sweep frame) → fixed. R2: back-post **WIN**; joinery/seat/rail LOSE → fixed front overhang, stretcher tenons, pill top rail, removed false spindles.
- Score with **silhouette-iou-v1** (same as the browser app): record IoU in `evals/photos/chairs/chair_02.score.json`, then `npm run score:photos`. See `evals/photos/chairs/SCORE.md`.
