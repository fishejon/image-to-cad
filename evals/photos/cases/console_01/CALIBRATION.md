# console_01 — calibrated metric table (P0 / D8)

Recorded: `2026-11-17T18:32:16.475841+00:00`

**D8 calibration (front):** FAIL — camera-fit IoU **0.7578** (need ≥ 0.8).

**Clean iso diagnostic:** IoU **0.5582** (Close+) on `console_01_iso_clean.jpg` — not a D8 gate, but shows white-bg helps.

D8 still wants a **front-on, no-props, plain-bg** shot (same as iso_clean but straight-on).

| Source | Legacy ortho IoU | Rating |
| --- | ---: | --- |
| GT STEP→STL | 0.179 | Wrong |
| IR stub | 0.393 | Wrong |
| A0 smoke | 0.245 | Wrong |

Until D8 passes, product gates use **dims / parts / features / cut-list**, not IoU.

Machine record: [`CALIBRATION.json`](CALIBRATION.json)
