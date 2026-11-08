# Corrected baselines (fixed-scale IoU v3)

Source: `BASELINES_FIXED_SCALE.json` via `python -m furniture_cad ab`.

| Piece | B Create IoU | O oracle IoU | O rating | Notes |
| --- | ---: | ---: | --- | --- |
| chair_04 | 0.641 | 0.484 | Close | Scale-search previously inflated O to 0.671 |
| chair_02 | 0.948\* | 0.572\* | Close+ | Room photo — untrusted |
| case_01 | 0.297 | 0.256 | Wrong | Both weak; dims path separate |

\*Untrusted room background.

**A0 (live blind agent):** not yet recorded under frozen prompts (run separately; spend capped).

Product gate uses **A**, not O. Fixed-scale metric is the stick going forward.
