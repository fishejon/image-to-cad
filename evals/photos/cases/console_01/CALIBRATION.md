# console_01 — calibrated metric table (P0 / D8)

Recorded: `2026-11-11T01:23:59.979642+00:00`

**D8 calibration:** FAIL — camera-fit IoU **0.1126** (need ≥ 0.8).

Photo pose: `three_quarter_right` — front-on still **missing** for a trusted ruler.

| Source | Legacy ortho IoU | Rating |
| --- | ---: | --- |
| GT STEP→STL | 0.179 | Wrong |
| IR stub | 0.393 | Wrong |
| A0 smoke | 0.245 | Wrong |

Until D8 passes, product gates use **dims / parts / features / cut-list**, not IoU.

Machine record: [`CALIBRATION.json`](CALIBRATION.json)
