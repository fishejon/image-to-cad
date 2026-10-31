# Photo loop scores (silhouette-iou-v1)

**One method for every chair** — same rubric as the app (`CAD.vision.scorePhotoChair`):

| Field | Meaning |
| --- | --- |
| **rating** | `Match` (IoU ≥ 0.70) · `Close+` (≥ 0.55) · `Close` (≥ 0.40) · `Wrong` (below or topology broken) |
| **topology_ok** | Part set / construction is basically right even if dims are off |
| **iou** | Silhouette overlap vs the reference photo. `*` = untrusted (room background fills the mask) |
| **missing_block** | Construction gap to log in `failure_log.jsonl` |

```bash
npm run score:photos
# STL vs photo (bespoke):  npm i -D puppeteer-core && npm run measure:stl-iou -- chair_02 path/to.stl --write
# EXAMPLE vs photo:        npm run measure:chair-iou -- chair_04 --example lakin-chair --write
```

| id | template / path | rating | topology_ok | iou | missing_block? | notes |
| --- | --- | --- | --- | --- | --- | --- |
| chair_01 | four_leg_chair | Wrong | N | — | `bent_panel`, `seat_contour` | Commons Stuhl. Chrome + bentwood. |
| chair_02 | **bespoke** `lab/.../chair_02.py` | Close+ | Y | 0.11* | — | Room photo — raw IoU untrusted; keep Close+ until subject mask. |
| chair_03 | tube + panels | Wrong | N | — | `tube_frame`, `panel_seat_back`, `footrest_ring` | Bar stool. Tape ready. |
| chair_04 | **SPEC** `examples/lakin-chair.json` | Close+ | Y | 0.64 | `leg_apron_fillet` | Lakin catalog dims. Studio IoU vs lakin-chair example. |
| chair_05 | organic walnut | Wrong | N | — | `organic_taper_leg`, `crisscross_underframe`, `floating_oval_back` | Dual views; need own example (not Lakin). |

**Goal:** measured IoU on studio/clean photos; subject-masked IoU for room shots. Pack has 5 photos; 2 scored with numbers (1 trusted).
