# Photo loop scores (silhouette-iou-v1)

**One method for every chair** — same rubric as the app (`CAD.vision.scorePhotoChair`):

| Field | Meaning |
| --- | --- |
| **rating** | `Match` (IoU ≥ 0.70) · `Close+` (≥ 0.55) · `Close` (≥ 0.40) · `Wrong` (below or topology broken) |
| **topology_ok** | Part set / construction is basically right even if dims are off |
| **iou** | Silhouette overlap vs the reference photo (app render, iso). `—` until measured |
| **missing_block** | Construction gap to log in `failure_log.jsonl` |

Until IoU is measured, `ratingHint` in `chair_NN.score.json` stands in (eyeball). After an app run, paste IoU into that file (or `--predictions`) and re-score.

```bash
npm run score:photos
# or: node tools/score-photo-chairs.js --predictions evals/photos/chairs/predictions.json
```

| id | template / path | rating | topology_ok | iou | missing_block? | notes |
| --- | --- | --- | --- | --- | --- | --- |
| chair_01 | four_leg_chair | Wrong | N | — | `bent_panel`, `seat_contour` | Commons Stuhl. Chrome tube + bentwood. |
| chair_02 | **bespoke** `examples/bespoke/chair_02.py` | Close+ | Y | — | — | Designer + Gauntlet. Measure IoU next. |

**Goal:** 5–10 chairs scored with this table before widening furniture categories. Prefer SPEC/`dining-chair` language in the browser path; keep bespoke scripts as gold corpus.
