# Decision: SAM 2 optional in WP1 (GrabCut is the default path)

Date: 2026-11-17 · WP1

## Context

Shop-ready spec WP1 requires SAM 2 (hiera-small) with GrabCut fallback. The Fly worker is CPU-only today; SAM 2 weights are large and not yet vendored.

## Decision

Ship WP1 with:

1. **GrabCut** (central 80% box) as the working segmenter when OpenCV is present.
2. **Brightness** last resort (flagged `quality=low`).
3. **SAM 2** as an optional import path (`intake/segment.py::_sam2_mask`) that returns `None` until weights + `sam2` package are installed on the worker.

## Evidence

- `opencv-python-headless` is now a hard dependency; GrabCut + ArUco + LSD run offline in CI.
- Synthetic WP1 tests pass without SAM 2.
- Spec §8 already lists SAM 2 CPU cost as an open risk.

## Follow-up

Measure GrabCut mask IoU on hand-labeled dev masks (WP8). If IoU < 0.97 on studio fronts, add a GPU worker or ship hiera-small weights and flip `_sam2_mask` to a real predictor in a dedicated PR.
