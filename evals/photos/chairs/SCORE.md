# Photo loop scores (silhouette-iou-v1)

**Wedge (frozen):** dining / side chairs with visible rake or continuous frames. See [`CREATE_SCORECARD.md`](CREATE_SCORECARD.md).

**One method for every chair** — same rubric as the app (`CAD.vision.scorePhotoChair`):

| Field | Meaning |
| --- | --- |
| **rating** | `Match` (IoU ≥ 0.70) · `Close+` (≥ 0.55) · `Close` (≥ 0.40) · `Wrong` (below or topology broken) |
| **topology_ok** | Part set / construction is basically right even if dims are off |
| **iou** | Silhouette overlap vs the reference photo. `*` = untrusted (room background fills the mask) |
| **Create** | Careful Create result in `chair_NN.score.json` → `create` (see scorecard) |
| **missing_block** | Construction gap to log in `failure_log.jsonl` |

```bash
npm run score:photos
npm run create:photos -- chair_04          # needs ANTHROPIC_API_KEY
# STL vs photo (bespoke):  npm i -D puppeteer-core && npm run measure:stl-iou -- chair_02 path/to.stl --write
# EXAMPLE vs photo:        npm run measure:chair-iou -- chair_04 --example lakin-chair --write
# Create SPEC vs photo:    npm run measure:chair-iou -- chair_04 --spec evals/photos/chairs/out/chair_04.create.json --write
```

| id | template / path | gold rating | topology_ok | gold iou | Create | missing_block? | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| chair_01 | four_leg_chair | Wrong | N | — | — | `bent_panel`, `seat_contour` | Commons Stuhl. Chrome + bentwood. |
| chair_02 | **bespoke** + Create | Close+ | Y | 0.11* | **Close+*** | — | Wedge. Create Careful 2026-11-01; stance OK; room IoU untrusted (0.95*). |
| chair_03 | tube + panels | Wrong | N | — | out of wedge | `tube_frame`, `panel_seat_back`, `footrest_ring` | Bar stool. |
| chair_04 | **SPEC** + Create | Close+ | Y | 0.64 | **Close+ 0.64** | `leg_apron_fillet` | **Primary wedge.** Create = gold IoU; stance profile correct. Gap to Match ≈ fillet. |
| chair_05 | organic walnut | Wrong | N | — | borderline | `organic_taper_leg`, `crisscross_underframe`, `floating_oval_back` | Log blocks; not wedge gate. |

**Goals:** (1) gold IoU on studio/clean photos; (2) **≥3/5 Create Close+** on the wedge (chair_04 Create within ~0.05 of 0.64).  
**Status 2026-11-01:** Wedge Create **2/2 Close+** so far (`chair_04` trusted 0.641 = gold; `chair_02` untrusted room). Next: Fix-stance not needed for Lakin; push Match via fillet / fuller example, or score `chair_01` carefully.
