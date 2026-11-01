# Chair / stool photo pack (local)

Drop **your** photos here. Nothing uploads to the server.

## Per photo

| File | Purpose |
| --- | --- |
| `chair_01.jpg` (or `.png` / `.webp`) | Reference photo |
| `chair_01.json` | Hand params for lab template, or notes for bespoke |
| `chair_01.score.json` | Topology + optional silhouette IoU for `npm run score:photos` |
| `chair_01.brief.md` | Construction brief (bespoke path) |

Start params from [`_params.template.json`](_params.template.json).

## Product wedge

Dining / side chairs with **visible rake or continuous frames**. Weekly Create process: [`CREATE_SCORECARD.md`](CREATE_SCORECARD.md). Tube stools and organic underframes stay in the pack for `missing_block` logging but do not gate the wedge.

## How to score (same method every time)

1. Build the chair (app Create from photo, `npm run create:photos`, or lab bespoke → STL).
2. In the app, load the model, set the reference image, run with photo match / silhouette (any Quality that can render) — or `measure:chair-iou --spec …`.
3. Read **Silhouette score** (IoU + Match/Close+/Close/Wrong) from the status / Inspect card.
4. Write IoU into `chair_NN.score.json` (`"iou": 0.62`, `"topology_ok": true`) or let Create tooling fill `create`.
5. Run `npm run score:photos` and update the row in [`SCORE.md`](SCORE.md).

Optional headless tools (`npm i -D puppeteer-core` once; local Chrome or `CHROME_PATH`):

```bash
npm run build
# photo vs EXAMPLE mesh (studio shots work; room shots often need subject masks):
npm run measure:chair-iou -- chair_04 --example lakin-chair --write
# photo vs lab STL:
npm run measure:stl-iou -- chair_02 lab/furniture_cad/out/chair_02_bespoke/chair_02.stl --write
```

Mark room-photo IoU with `"iou_quality": "untrusted_room_background"` in the score JSON so `score:photos` keeps the human `ratingHint`.

Rubric: IoU ≥ 0.70 Match · ≥ 0.55 Close+ · ≥ 0.40 Close · else Wrong (or topology_ok false → Wrong).

## Privacy

Keep this folder local if photos are private; do not commit images you do not want in git. Params/score JSON without photos is fine to commit.
