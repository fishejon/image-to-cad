# Photo loop scores (silhouette-iou-v1)

**One method for every chair** — same rubric as the app (`CAD.vision.scorePhotoChair`):

| Field | Meaning |
| --- | --- |
| **rating** | `Match` (IoU ≥ 0.70) · `Close+` (≥ 0.55) · `Close` (≥ 0.40) · `Wrong` (below or topology broken) |
| **topology_ok** | Part set / construction is basically right even if dims are off |
| **iou** | Silhouette overlap vs the reference photo (app render, iso). `—` until measured |
| **missing_block** | Construction gap to log in `failure_log.jsonl` |

Until IoU is measured, `ratingHint` in `chair_NN.score.json` stands in (eyeball). After an app **Create/revise** run against that photo, paste IoU into that file (or `--predictions`) and re-score.

```bash
npm run score:photos
# optional headless baseline (photo vs EXAMPLE mesh — not Create likeness; needs puppeteer-core + Chrome):
# npm run measure:chair-iou -- chair_02 --example dining-chair
# add --write only after you trust the fill stats
```

| id | template / path | rating | topology_ok | iou | missing_block? | notes |
| --- | --- | --- | --- | --- | --- | --- |
| chair_01 | four_leg_chair | Wrong | N | — | `bent_panel`, `seat_contour` | Commons Stuhl. Chrome tube + bentwood. Local photo: `chair_01.jpg` (gitignored). |
| chair_02 | **bespoke** `examples/bespoke/chair_02.py` | Close+ | Y | — | — | Designer + Gauntlet. Measure IoU in app next. |
| chair_03 | — | — | — | — | — | **Slot** — add photo + score |
| chair_04 | — | — | — | — | — | **Slot** — add photo + score |
| chair_05 | — | — | — | — | — | **Slot** — add photo + score |

**Goal:** 5–10 chairs scored with measured IoU before widening furniture categories. Browser Create now injects the curved `dining-chair` example as few-shot for seating. Keep bespoke lab scripts as gold corpus.
