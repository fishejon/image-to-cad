# sideboard_01 — SYNTHETIC ground truth

Designed by `make_synthetic_gt.py`, not built or measured, and there is no real photo. Treat it as a generalisation stress test (straight ends, short tapered legs, three stacked drawers between two doors), not as real-world evidence like `console_01`.

Regenerate: `python evals/photos/cases/sideboard_01/make_synthetic_gt.py`.

To replace it with a real piece, put a Fusion export at `sideboard_01.step`, rewrite `cut_list.hand.json` from your plan, and set its `status` to `authoritative_hand_plan`.
