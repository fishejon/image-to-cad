# sideboard_01 — ground truth (template)

Drop in the Fusion export and fill the templates, then set `cut_list.hand.json` `status` to `"authoritative_hand_plan"`.

| File | What to add |
| --- | --- |
| `sideboard_01.step` | Fusion STEP export (answer key geometry) |
| `cut_list.hand.json` | one row per part type: `id`, `name`, `qty`, `finished_in` {t,w,l}, `thickness_mm`/`width_mm`/`length_mm` (finished), `blank_in` {t,w,l}, `stock`, `material`; plus `stock_buy` (per-stock `net_bf`) and `joinery` |
| `known_sizes.json` | overall W/D/H |
| `features.json` | feature counts |
| `views.json` + photo | a clean straight-on front photo (jpg files are gitignored) |

Part ids in the predicted cut list must match the hand ids for part matching to work.
