# console_01 — walnut console ground truth

**Dims:** 47 × 12 × 30 in → **1193.8 × 304.8 × 762 mm** (W × D × H).  
Two drawers under an open cubby; carved ends/legs; Japanese joinery.

| Artifact | Status |
| --- | --- |
| Photo (front) | `console_01.jpg` (local; front-on — D8 still fails on mask quality) |
| Photo (iso) | `console_01_iso.jpg` (local; depth reference) |
| Views / features / sizes | [`views.json`](views.json), [`features.json`](features.json), [`known_sizes.json`](known_sizes.json) |
| Fusion STEP | [`console_01.step`](console_01.step) |
| Hand cut list + joinery | [`cut_list.hand.json`](cut_list.hand.json) + [`CUT_LIST_JOINERY.md`](CUT_LIST_JOINERY.md) |
| Calibration (P0) | [`CALIBRATION.md`](CALIBRATION.md) |
| Furniture IR (approx) | `lab/furniture_cad/examples/ir/console_stub.ir.json` — boxes only until P1 |

**Answer key:** STEP + hand cut list. IoU is **not** a product gate until D8 passes on a front-on photo.
