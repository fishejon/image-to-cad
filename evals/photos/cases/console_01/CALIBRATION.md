# console_01 — calibrated metric table (P0 / D8)

Recorded: `2026-11-18T04:20:00+00:00`

**D8 calibration (front):** PASS — camera-fit IoU **0.8316** (≥ 0.8) on `console_01_front_clean.jpg`.

**Clean iso diagnostic:** IoU **0.5582** (Close+) on `console_01_iso_clean.jpg` — not a D8 gate.

| Source | Legacy ortho IoU | Rating |
| --- | ---: | --- |
| GT STEP→STL | 0.179 | Wrong |
| IR stub | 0.393 | Wrong |
| A0 smoke | 0.245 | Wrong |

Front D8 is trusted for product gates. Iso / three-quarter remains diagnostic only.

Machine record: [`CALIBRATION.json`](CALIBRATION.json)
