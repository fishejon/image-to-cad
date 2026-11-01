# Create scorecard (weekly)

**Product wedge (frozen):** dining / side chairs with **visible rake or continuous side frames**.  
Out of wedge for scoring goals: chrome tube stools, organic walnut underframes, multi-angle upload.

**Goal:** ≥3/5 chairs **Close+** from **Careful Create** (not gold SPEC / bespoke). Lakin Create within ~0.05 IoU of gold SPEC (0.64).

## How to run

```bash
# Uses Vercel proxy by default (CREATE_PROXY_URL / image-to-cad-gray.vercel.app),
# or local ANTHROPIC_API_KEY / .env if set.
npm run create:photos -- chair_04          # Careful Create + stance dump
npm run create:photos -- chair_04 chair_05 # multiple
npm run create:photos -- --all             # wedge chairs only (see below)
npm run score:photos                       # prints gold + Create columns when present
```

Writes:

- `out/chair_NN.create.json` — full SPEC from Create  
- Updates `chair_NN.score.json` → `create` block (stance, geometry, IoU if measured)

Then measure silhouette (studio photos):

```bash
npm run build
npm run measure:chair-iou -- chair_04 --spec evals/photos/chairs/out/chair_04.create.json --write
```

## Wedge chairs

| id | In wedge? | Why |
| --- | --- | --- |
| chair_01 | maybe | bentwood + chrome — hard; score but don’t block wedge |
| chair_02 | yes | wood dining / side, room photo (IoU often untrusted) |
| chair_03 | no | tube bar stool — missing_block path |
| chair_04 | **yes** | Lakin — primary stance / rake target |
| chair_05 | borderline | organic walnut — log missing_block; not wedge gate |

## After each Create change

1. Re-run Create on wedge chairs (`chair_04`, ideally `chair_02`).  
2. Record Create rating / IoU in score JSON.  
3. If Close+ but stance off → use in-app **Fix stance with Revise**.  
4. If Wrong with a construction gap → append `failure_log.jsonl` (`missing_block`).
