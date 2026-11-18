# Image-to-CAD: Shop-Ready Technical Specification

Prepared for the fishejon/image-to-cad project · November 17, 2026 · Draft v1 for implementing agents

> **Status: ACTIVE.** Supersedes day-to-day sequencing in [`product-plan-2026-11-10.md`](product-plan-2026-11-10.md) for work after P4. Keep that doc for locked decisions D1–D12 and historical P0–P4 context.

## 1. Purpose and definition of done

The tool takes photos of a furniture piece plus one known dimension and produces a model, drawings and lists a woodworker can build from. Today it names features and fills a generic template. It does not measure the photo, it does not model real joinery, and it never checks its output against the photo. This spec closes those gaps.

**Shop-ready** means all of the following on held-out photos, blind, with one known overall dimension:

- Part recall ≥ 0.85 and cut-list size match ≥ 0.85 (each dimension within max(5 mm, 3%)).
- Board-feet error ≤ 10%, computed from blanks that include stock allowances and glue-ups.
- Front camera-matched silhouette IoU ≥ 0.80 and 95th-percentile boundary distance ≤ 4 mm after scaling to the known dimension.
- Joinery kind recall ≥ 0.80 for joints that are visible or strongly implied, and every joint carries a reason and a provenance tag.
- Dimensioned drawings (PDF and DXF) whose printed dimensions match the solid to 0.1 mm.
- A working woodworker rates the output buildable with minor fixes on a majority of held-out pieces.

**Non-goals for this spec:** a general mesh-to-CAD tool and 3D-print workflows. Chairs, cabriole legs, bent laminations and carved organic forms are in scope through WP10, which starts after gate G2.

## 2. Ground rules for implementing agents

1. The model never estimates lengths. Three prompt-tuning attempts (direct ratios, landmark rows, user-known sizes) all failed. Code measures. Claude labels, classifies and critiques from an enumerated vocabulary. Any number that reaches the IR must carry a source tag: `cv`, `user`, `snapped`, `default`, or `guessed`.
2. Never seed from golden IR. `examples/ir/console_01.ir.json` is for compile tests only. Any run that touches an answer key is flagged and excluded from scoring.
3. Held-out cases are locked. Nobody tunes prompts, priors or thresholds against `evals/photos/holdout/`. See WP8.
4. One work item per PR. Each PR ships code, unit tests, an eval re-run on the dev set, and an update to `evals/photos/P4_VERIFY.md` (or the new tracker) with before and after numbers. No PR merges with a regression on any dev-set metric greater than 0.02 unless the PR description explains it.
5. Stop rule. If a metric does not improve after two PRs aimed at it, write a decision note in `docs/plans/` and change approach. Do not keep tuning.
6. No new scaffolding without a gate (existing D12). UI work is limited to surfacing provenance, asks and recompile (WP9).
7. Deterministic compile (existing D11). Compile, Derive, Dimension and drawing export make no model calls and are tested offline.
8. Honest labels. Everything not measured is shown as Defaulted or Guessed in the UI, the drawings and the cut list.

## 3. Baseline (from the repo as of 2026-11-17 / post-#98)

| Stage | Current state | Gap |
| --- | --- | --- |
| Intake (`intake/pipeline.py`) | Brightness threshold mask; rectify detects lines only; scale assumes the subject fills 70% of image width | No real segmentation, no homography, scale is a guess |
| Perceive (`perceive/vision.py`) | Two Claude passes returning counts and style labels; Haiku default | No geometry, no detail attributes |
| Dimension (`dimension/anchor.py`) | Anchors overall W, D, H from user input; asks for leg and drawer-front heights | Nothing measured from the photo |
| Construct (`construct/from_observation.py`) | Class priors fill stock, overhang, leg size, bay fractions | Template instantiation, wrong massing on the console |
| Compile (`construct/compile.py`) | Boxes, sweeps, tapered and flared legs; joinery blanks opt-in; nightstand/bookcase frames | No real joinery, no fillets, no profile-driven parts |
| Verify (`verify/critic.py`, `repair.py`) | Compares bounding box to typed dims and feature counts to Perceive's own counts | Never compares to the photo (D8 camera-fit exists as a calibration ruler only) |
| Derive (`lists.py`) | Cut list and board feet from the solids | Blank allowances for carved parts too thin; no glue-ups, no nesting |
| Export (`export_shop.py`) | DXF is one rectangle per blank; PDF is a text dump | No dimensioned drawings |
| Ground truth | Console (real), credenza, bookcase, nightstand (Fusion), sideboard (synthetic) | Too few, and the headline 1.0 recall numbers use oracle counts |
| Honest console baseline | Part recall 0.77, cut-list match ~0.23, board-feet error ~0.53, human rating Close | Strict D8 IoU passed at 0.832 on one studio photo |

**Keep:** the staged architecture, IR patch repair loop, D8 camera-fit ruler (`verify/camera_fit.py`), scorer, blind protocol, failure log, and Fusion ground-truth discipline.

## 4. Target pipeline and contracts

```
Intake → Measure → Perceive(labels) → Dimension → Construct → Compile → Verify(photo) → Derive → Drawings
```

- **Measure** is new and is pure computer vision on the rectified image.
- **Perceive** becomes a labeling and classification stage over Measure's candidate regions.
- **Verify** renders the compiled model from the photo's camera and compares it to the photo.
- Only Perceive and Verify call a model. Everything else is deterministic.
- New schemas: `observation.v2` (measurements with provenance), `furniture_ir.v3` (joints, profiles, stock), `verify.v2` (photo-grounded discrepancies), `provenance.v1` (per-value source and confidence). Put them in `lab/furniture_cad/contracts/schemas/` with JSON Schema tests. Keep v1 and v2 readers for the existing tests.

## 5. Work packages

Order matters. **WP1 and WP2 block everything.** WP3 and WP4 follow. WP5 and WP6 can run in parallel after WP4. WP7 needs WP5. WP8 runs continuously from day one. WP10 starts after G2 and reuses the outputs of WP1, WP2 and WP5.

Trackers live under `evals/photos/WP*_*.md`.

| WP | Name | Blocks |
| --- | --- | --- |
| WP1 | Intake: segmentation, rectification, scale | all |
| WP2 | Measure: geometry in code | Construct from photo |
| WP3 | Perceive v2: detail attributes | massing / style |
| WP4 | Dimension v2: snap + provenance | IR numbers |
| WP5 | IR v3 + joinery / profiles / stock | shop solids |
| WP6 | Verify v2: photo-grounded loop | IoU / repair |
| WP7 | Shop deliverables (PDF/DXF/lists) | drawings |
| WP8 | GT, eval, held-out set | continuous |
| WP9 | One path, honest UI, hardening | beta |
| WP10 | Curved / organic forms | after G2 |

Full acceptance criteria for each WP are in the sections below (implementing agents: do not weaken silently — open a decision note instead).

### WP1. Intake: real segmentation, rectification and scale

Gap: brightness mask, no homography, 0.70 fill-fraction scale.

Do exactly this (edit `intake/pipeline.py`, add `intake/rectify.py`, `intake/segment.py`):

1. **Capture contract.** Extend `product/capture_guidance.py` to require: a front-on photo (camera at mid-height of the piece, subject distance at least 2 m, 70 to 100 mm equivalent focal length, plain light background), plus optionally a side photo and a 3/4 photo. Ask for a printed ArUco marker (`DICT_4X4_50`, id 7, printed at a stated size, for example 100 mm) placed on the floor plane or flat against the piece. Provide the marker PDF in the app.
2. **Segmentation.** Run SAM 2 (hiera-small) on the worker CPU with an automatic box prompt equal to the central 80% of the image. Take the largest connected component that touches the image center. If SAM 2 is unavailable or confidence is under 0.8, fall back to OpenCV GrabCut seeded with the same box. Keep the existing brightness mask only as the last resort and flag quality as low.
3. **Rectification.** If the ArUco marker is found, compute the homography from its four corners to a fronto-parallel plane. Otherwise estimate vertical and horizontal vanishing points from LSD line segments inside the mask, pick the horizontal rail lines (top edge, case bottom, drawer reveals) and the vertical stile lines, and solve a keystone-correcting homography that makes both families orthogonal. Report residual angle error. Reuse the pitch and scale refine already in `verify/camera_fit.py` rather than duplicating it.
4. **Scale.** Replace the fill-fraction guess. Scale priority: ArUco size, then the user's known dimension measured against the rectified mask extent along its axis, then asked. Output `px_per_mm`, `scale_source`, and a relative error estimate (mask boundary uncertainty divided by the extent).
5. **Output** `intake.v2` including the rectified image path, mask path, homography, `px_per_mm` and diagnostics.

**Acceptance:** on the five dev cases, mask IoU against a hand-labeled mask ≥ 0.97; scale error ≤ 1% when a marker is present and ≤ 2% when anchored to a known overall width on front-on photos. Unit tests use synthetic keystoned renders of the STEP files with known homographies. Add a deterministic test that rejects photos where residual angle error exceeds 3 degrees by returning an actionable retake request.

### WP2. Measure: extract geometry in code

Gap: Perceive returns counts only; no geometry reaches Construct from the photo.

Do exactly this (new package `perceive/measure/`):

1. Edges and segments on the rectified image inside the mask (Canny + LSD; snap H/V; cluster).
2. Candidate regions as closed rectangles (drawer fronts, doors, open bays, end blocks, top band).
3. Width profile → leg width, taper, case bottom row, top thickness / overhang.
4. End outline (Douglas-Peucker + RANSAC arcs) → ≤24 segments for pill/wishbone/swept ends in WP5.
5. Set-of-marks labeling: Claude returns only labels + confidences keyed by overlay id — **no lengths**.
6. Convert to mm with `px_per_mm`; emit `observation.v2` with `source: cv`.
7. Unsure → ask (≤2 choices); max 3 asks per run.

**Acceptance:** drawer-front H/W within 3 mm or 3%; case-bottom row within 10 mm; leg width top/foot within 3 mm; end outline p95 vs STEP front silhouette ≤ 4 mm.

### WP3. Perceive v2: detail attributes

Gap: counts and a few style labels; Close rating called out wrong case-to-leg massing and missing pill/wishbone.

Crops + fixed enums; self-consistency k=3; configurable model with A/B; remove heuristic `end_block_carved` invention → ask.

**Acceptance:** attribute accuracy ≥ 0.85; feature count recall ≥ 0.90 **blind**; median Perceive cost ≤ $0.35.

### WP4. Dimension v2: measurements, snapping, uncertainty

Merge by priority `user > ArUco > cv > snapped > default`; stock snap table; provenance.json; delete class priors for anything WP2 can measure.

**Acceptance:** ≥80% of IR dimensions carry `cv` or `user`; nothing untagged.

### WP5. IR v3 and compiler: joinery, profiles, edges, stock

Profile primitive from measured end outline; joint kinds with fill check; defaults with reasons; edges; drawer generator; stock allowances + glue-ups + carved blanks; `custom_part` escape hatch.

**Acceptance:** golden compile still passes; console blind part recall ≥ 0.85 including joinery blanks; cut-list match ≥ 0.50 (P4 stage); board-feet error ≤ 15% (final 10%).

### WP6. Verify v2: photo-grounded loop

Render with `camera_fit` camera; IoU + p95 boundary + per-region residuals; deterministic patches first; Claude selects among patches only (no numbers); ≤4 rounds; $2 / 10 min hard cap.

**Acceptance:** front IoU ≥ 0.80 and p95 ≤ 4 mm on ≥4/5 dev cases without golden seeding; repair never worsens a metric.

### WP7. Shop deliverables

Dimensioned PDF/DXF (ezdxf), part sheets, cut list + nesting, STEP/GLB. Printed dims match solid to 0.1 mm.

### WP8. Ground truth, evaluation, held-out set

Grow to 15 cases; 5 in `evals/photos/holdout/` with SHA-256 manifest; blind by default; photographer protocol in `CAPTURE.md`; woodworker review.

### WP9. One path, honest UI, hardening

`pipeline_vision` default; provenance badges + asks + Recompile; mandatory worker token; Langfuse + weekly regression.

### WP10. Curved and organic forms (after G2)

Multi-view ArUco capture; visual hull as envelope only; B-splines with continuity; organic block library; compound-angle joinery; per-view verify; hard geometry gates; curve manufacturing outputs.

## 6. Gates

| Gate | Condition |
| --- | --- |
| **G1** (after WP1–WP2) | Scale error ≤ 2%; WP2 measurement errors on all five dev cases; blind feature recall ≥ 0.90 |
| **G2** (after WP3–WP6) | Console blind: part recall ≥ 0.85, cut-list ≥ 0.50, board-ft err ≤ 15%, front IoU ≥ 0.80, p95 ≤ 6 mm; no regression on other dev cases |
| **G3** (after WP7) | Drawing/DXF tests pass; woodworker review of 3 dev pieces: majority minor fixes or better |
| **G4** (final, held-out) | Shop-ready definition (§1) on the 5 held-out cases |
| **G5** (after WP10) | Held-out curved cases: p95 ≤ 2 mm front / ≤ 3 mm side; tangent ≤ 2°; curvature corr ≥ 0.95; 100% valid solids; no unflagged Guessed; woodworker rates 1:1 templates buildable on majority |

## 7. Agent procedure

1. Read `evals/photos/P4_VERIFY.md`, `docs/plans/product-plan-2026-11-10.md` and this spec before starting.
2. Create a tracker file per work package in `evals/photos/` named `WPn_<name>.md` with a checklist copied from the acceptance text, and update it in every PR.
3. Branch names `wpN/short-name`. Run `cd lab/furniture_cad && pytest -q` and `npm test` before opening a PR. Include the dev-set metric table in the PR body.
4. If an acceptance item cannot be met, do not weaken it silently. Open a decision note in `docs/plans/` with the evidence and a proposed change for human review.
5. Never commit photos that lack a license or consent record; keep attribution files current.

## 8. Risks and open decisions

- **SAM 2 on CPU:** may be slow or heavy on the Fly worker. Option: a GPU worker or a smaller model. Decide after measuring latency in WP1.
- **Photo quality:** most user photos will not be studio-grade. Capture guidance and retake requests are part of the product. Consider a guided in-app camera later.
- **Dev set size:** 15 pieces is still small. Treat gate results as indicative until a second held-out round.
- **Joinery inference:** many joints are hidden. Defaults with reasons and an override, not false certainty. Decide whether the app asks about joinery preference up front.
- **Cost:** Opus-class Perceive and visual critic may break the $1.50 median. WP3 includes the A/B to find the cheapest passing model.
- **Curved and organic forms:** WP10 covers them. A photo does not fix the 3D shape behind it, so flawless is the G5 tolerances, with every unseen region tagged Guessed and confirmed by the user.
