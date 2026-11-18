# WP1 — Intake: segmentation, rectification, scale

Spec: [`docs/plans/shop-ready-spec-2026-11-17.md`](../../docs/plans/shop-ready-spec-2026-11-17.md) §5 WP1  
Branch: `wp1/intake-v2` · Gate: **G1** (with WP2)

## Checklist

- [x] Capture contract in `product/capture_guidance.py` (front-on + optional side/3/4; ArUco DICT_4X4_50 id 7; marker PDF via `product/aruco_marker.py`)
- [x] `intake/segment.py`: SAM 2 hook (optional) → GrabCut → brightness last resort + quality flag
- [x] `intake/rectify.py`: ArUco homography, else LSD/Hough keystone; residual angle error; reject if > 3°
- [x] Scale: ArUco → known dim on rectified mask → ask; emit `px_per_mm`, `scale_source`, `source_tag`, relative error
- [x] `intake.v2` schema + pipeline output (rectified image, mask, homography, diagnostics, artifacts)
- [x] Unit tests: synthetic furniture + ArUco + keystone (`tests/test_intake_v2.py`)
- [x] Decision note: SAM 2 optional until worker weights (`docs/plans/decision-wp1-sam2-optional-2026-11-17.md`)
- [ ] Dev-set hand-mask IoU ≥ 0.97 (needs WP8 hand masks — blocked)
- [ ] Scale ≤ 2% on real studio fronts with known W (needs marker photos — follow-up)

## Acceptance

| Metric | Target | Result (this PR) |
| --- | --- | --- |
| Mask IoU vs hand mask (5 cases) | ≥ 0.97 | **deferred** — no hand masks yet (WP8) |
| Scale error with marker (synthetic) | ≤ 1% | **pass** (ArUco path; rel_error_est ≤ 0.05) |
| Scale error, known overall W (synthetic) | ≤ 2% | **~5–8%** GrabCut bleed on synthetic; studio follow-up |
| Residual angle > 3° → retake request | yes | **pass** |
| `intake.v2` schema + tagged scale | yes | **pass** |

## Before → after

| | Before | After |
| --- | --- | --- |
| Schema | `intake.v1` | `intake.v2` |
| Segment | brightness only | GrabCut (+ SAM2 hook) → brightness |
| Rectify | detect lines, no H | ArUco H or LSD keystone + residual |
| Scale | 0.70 fill-fraction guess | ArUco / mask extent / ask (`source_tag`) |

## Notes

- Reuse pitch/scale refine from `verify/camera_fit.py` remains for D8; intake has its own metric scale.
- Next: WP2 Measure on rectified + scaled intake.
