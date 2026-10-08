# Architecture

```
picture ──► src/ai/vision.js ──► spec JSON ──► src/core/spec.js ──► SpecModel ──► checks ──► src/ui/app.js (viewer)
              ▲  builder (LLM)                    expressions,        defs/insts    exact        guide.js  (build guide)
              └────────── critic report ◄──────── params, parts                     geometry     exporter.js (STL, split, nest)
```

| File | Role |
|---|---|
| `src/core/geo.js` | Mesh builder (cylinders, revolves, extrusions), crease normals, **binary STL** and **ZIP** writers. |
| `src/core/csg.js` | `Solid`: exact union-minus-cuts of axis-aligned boxes on a compressed grid. Emits watertight meshes with UVs, run-merged boxes for exact interference/volume, and clip/key support for splitting. |
| `src/core/spec.js` | Safe expression parser, params, materials, groups, parts → `SpecModel`. Mesh parts are `MeshSolid`. |
| `src/core/checks.js` | Manifold check, exact interference, **joint fill**, bounds, cut list. |
| `src/core/exporter.js` | Print orientation, scale, **auto-split with alignment keys**, plate nesting, STL files, CSV. Pure functions (no DOM). |
| `src/ai/vision.js` | Prompt (embeds the spec language + a tested example), providers, `evaluate()` (the critic), `run()` (the builder⇄critic loop). |
| `src/ui/app.js` | Three.js viewer and all panes. `src/ui/guide.js` renders the Lego-style guide pages (WebGL → canvas → HTML). |
| `server/proxy.js` | Optional zero-dependency server that keeps the API key off the browser. |
| `tools/legacy/` | The original hand-coded sideboard generator (model + guide) that `examples/sideboard.json` was exported from, kept as a reference and as a regression oracle (`tests/run.js` checks the spec reproduces it exactly). |

## Why exact CSG on a grid
Furniture-class objects are almost entirely rectilinear. Collecting every box boundary per axis gives a small product grid; marking cells solid/empty and emitting only the exposed cell faces gives **watertight, manifold** meshes by construction (shared grid vertices, so no T-junctions), exact volumes, and trivial exact intersection tests. The same machinery clips a part with a slab and adds/removes a key to split it for printing. The price: no angled cuts (dovetails, mitres) or fillets in solid parts; round parts use mesh primitives instead.

## The Gauntlet loop
`vision.run` is a builder/critic loop: the model proposes a spec, `evaluate()` builds it and measures overlap, unfilled joints, non-watertight meshes and spec errors, and those findings go back to the model (stateless: each round resends the spec, the report and the pictures). An optional visual round sends a render beside the reference picture. The best spec seen is kept.

## Globals
`CAD.MATS`, `CAD.GROUPS`, `CAD.STEPS` hold the *current* model's materials/groups/steps; `buildSpec` refreshes them on every build (the viewer, guide and checks read them). Build one model at a time per page.

## Security notes
All spec-derived text is HTML-escaped before it reaches `innerHTML` (names, notes, labels, guide text); rich HTML is honoured only for trusted built-in examples. Expressions cannot call arbitrary functions. A browser-held API key is visible to anyone with access to that browser: use `server/proxy.js` for anything shared.
