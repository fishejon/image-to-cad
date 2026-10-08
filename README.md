# Image → CAD

Feed it a picture. Get a **parametric 3D model** built from real parts and joints, a **Lego-style build guide**, a **cut list**, and **print-ready STL files** that are split to fit your printer bed. Everything runs in the browser with Three.js.

* **Spec-driven CAD workspace**: assembly tree, explode, assembly-sequence animation, section plane, measure (vertex snapping), sliders for dimensions and moving parts, inspector with joinery.
* **Exact boolean engine** for rectilinear parts: mortises, dados, grooves, rabbets and box joints are real geometry; parts are watertight by construction.
* **Design checks**: part-to-part interference, *joint fill* (is every mortise/dado actually filled by its tenon/tongue?), watertightness, bed fit, STL round trip.
* **3D-printing export**: any scale (1:1 … 1:20), parts oriented flat, oversize parts **auto-split with alignment keys** (0.2 mm clearance), parts **nested onto bed plates**, one STL per plate or per part, cut-list CSV, spec JSON.
* **Build guide**: step-by-step pages with parts-needed callouts, exploded arrows, joinery highlighted (material to remove in orange, tenons in green) with dimensions; save as HTML or print to PDF.
* **Picture → design with a built-in critic loop** (Claude): the model writes the spec, the geometry checker audits it, findings go back to the model until it passes.

## Quick start
```bash
npm install            # only needed for tests/build (three.js)
npm run build          # → dist/image-to-cad.html (single file, examples embedded)
open dist/image-to-cad.html          # works from file://
# or serve the source tree (examples are fetched):
npm run serve          # http://localhost:8787
```
Deploying to GitHub Pages: see `.github/workflows/pages.yml` (publishes the single-file build).

## Designing from a picture
Open the **AI** tab, drop/paste a picture, optionally add a brief ("height 850 mm, solid oak, no screws"), choose a provider and press **Generate**.

| Provider | Use when |
|---|---|
| **Claude API key (browser)** | Quick personal use. Your key stays in the page (optionally in localStorage) and calls `api.anthropic.com` directly. Anyone with access to your browser can read it. |
| **Local proxy** | Recommended for sharing: `ANTHROPIC_API_KEY=… npm run serve`. The key never reaches the browser. |
| **Claude (inside claude.ai)** | When the built page is opened as a Claude artifact, it uses the viewer's own Claude account. |

Each round the critic reports spec errors, overlapping parts, unfilled joints and non-watertight parts back to the model. Tick **visual critic** to also send a render next to your picture. The result opens in the viewer and in the **Spec** tab, where you can edit it by hand.
The picture is sent to the provider you choose and nowhere else. A multi-round run with a large model costs real money on your account.

## The spec language
A design is a small JSON file: parametric expressions, parts made of boxes you add and cut (with `fill`-checked joints) or of mesh primitives (cylinders, revolves, extrusions), instances, steps and kinematics. Full reference: [docs/SPEC.md](docs/SPEC.md). Examples in `examples/`:

| Example | Shows |
|---|---|
| `sideboard.json` | 26 part types, pegged mortise-and-tenon, housed dados, box joints, sliding doors, 4 moving parts, a hand-written 35-page guide (auto-exported from `tools/legacy`). |
| `bookshelf.json` | Fully parametric (width, height, depth, shelf count), stopped dados, floating back, rabbeted drawers, drawer sliders. |
| `stool.json` | Mesh primitives with arbitrary rotations (splayed legs). |
| `lamp.json` | Revolves, spheres, custom materials. |

## Tests
```bash
npm test                      # 28 core tests + proxy tests, zero dependencies beyond three
npm run test:browser          # optional UI tests in headless Chromium (see package.json)
```
Core tests cover: the expression parser (including injection attempts), spec validation messages, every example (watertight / 0 interference / every joint filled), fidelity of the sideboard spec against the original generator, **parameter sweeps** (every slider at min, max and mid, all-min and all-max), export at 8 scale/bed combinations (watertight pieces, nothing oversize, volume conserved, everything nests), ZIP/STL round trip with CRC, and the AI loop with a mock model (feedback delivery, parse-failure retry, visual round, best-spec fallback). Browser tests drive the real UI against a fake Anthropic endpoint and attack it with a hostile spec.

## Honest limits
* Solid parts are **axis-aligned boxes** (rotate by 90° steps): no dovetails, mitres, fillets or chamfers. Round or sloped parts use mesh primitives, which render and export fine but are **not** covered by the interference/joint-fill checks and are never split for printing.
* The critic guarantees the model is *geometrically consistent* (no clashes, joints filled), not that it *looks like* your picture. Dimensions come from proportions in the picture unless you give hints; the optional visual critic is the model's own judgement.
* The AI loop is covered by mock-provider and fake-endpoint tests; results with the live API depend on the model you choose.
* Three.js is pinned to r128 (the last build with an official non-module bundle). Porting to ES modules is straightforward.
* Weight estimates multiply volume by density; mesh parts and overlapping boxes can over-count slightly.

## License
MIT. See `LICENSE`.
