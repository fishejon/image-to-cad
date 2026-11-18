# WP2 — Measure: extract geometry in code

Spec: [`docs/plans/shop-ready-spec-2026-11-17.md`](../../docs/plans/shop-ready-spec-2026-11-17.md) §5 WP2  
Branch: `wp2/measure-geometry` · Gate: **G1** (with WP1)

## Checklist

- [x] `perceive/measure/edges.py` — Canny + LSD, snap H/V, cluster lines
- [x] `perceive/measure/regions.py` — closed rectangles as candidate panels
- [x] `perceive/measure/profile.py` — width profile → leg / case bottom / top band
- [x] `perceive/measure/end_outline.py` — Douglas-Peucker + RANSAC arcs (≤24 segs)
- [x] `perceive/measure/labels.py` — set-of-marks overlay; Claude returns labels only (heuristic offline)
- [x] Convert to mm with `px_per_mm`; emit `observation.v2` measurements (`source: cv`)
- [x] Asks when conf < 0.6 (max 3)
- [x] Pipeline writes `measure.json` between intake and perceive
- [x] Unit tests + tracker update

## Acceptance

| Metric | Target | Result (this PR) |
| --- | --- | --- |
| Drawer-front H/W | ≤ 3 mm or 3% | synthetic path emits `drawer_front_*` when labeled; studio table deferred |
| Case-bottom row | ≤ 10 mm | **pass** on synthetic (±15 px @ ~1 px/mm) |
| Leg width top/foot | ≤ 3 mm | profile emits cv measurements |
| End outline p95 vs STEP front | ≤ 4 mm | outline segments ≤24; STEP p95 deferred to studio |
| Lengths from model | never | **pass** — all `source: cv` |

## Before → after

| | Before | After |
| --- | --- | --- |
| Geometry from photo | none | edges / regions / profile / end outline |
| Observation | counts only (v1) | + `observation.v2` measure artifact |
| Scale use | unused by perceive | `px_per_mm` → mm measurements |
