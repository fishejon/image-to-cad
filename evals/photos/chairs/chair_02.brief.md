# Construction brief — chair_02 (MCM dining)

Designer / CAD-engineer brief from the reference photo + tape dims. Implement as **one bespoke model**, not template knobs.

## Character
Walnut-toned MCM dining side chair. Continuous **back posts**. Open back: **crescent / soft pill top rail** + mid rail (+ optional vertical spindles). Upholstered seat with **recessed apron** under the cushion overhang. Low side + rear stretchers.

## Side elevation of the back post (critical — do not reverse)

```text
   top of rail
        |  posts stop ~3/4 up the top rail
        \
         \   sharper BACKWARD rake above seat (+Y)
          \
    midrail •
  seat _____|  seat rear
           /
          /  path comes FORWARD toward seat (−Y) as it rises
         /
   foot •──── foot sits BEHIND the seat rear edge (+Y past seat)
```

Foot is **aft of** the seat. Rising to the seat the post moves **forward**. Above the seat it rakes **backward** for a natural lean.

## Members

| Member | Intent |
| --- | --- |
| Seat cushion | Soft squircle / trap with rounded front; overhangs apron. One visual mass with substrate. ~¾″ thick. |
| Apron (side) | Wood rail under cushion, **inset** from cushion edge; thicker than stretchers; connects front leg ↔ back post just under seat. |
| Apron (front) | Shorter rail between front legs, mostly hidden by cushion overhang. |
| Front legs | Slight taper to floor; land at **front corners of the apron** (under cushion overhang). |
| Back posts | Continuous floor→backrest; path as above; terminate ~¾ up top-rail height; mount **behind** top rail (rail on front face of posts). |
| Side stretchers | ~9″ AFF; meet leg faces (connected, flush). |
| Rear stretcher | ~13″ AFF between back posts. |
| Mid rail | ~4–5¾″ above seat; tenoned into **inside** of posts; plan curve. |
| Top rail | ~21″ wide × ~⅝″ thick; **curved pill / soft rectangle** (not a bent flat board oval-wrong); plan curve cups sitter; posts die at ~¾ height. |
| Spindles | Two verticals mid→top rail if visible in photo (~1″), between posts. |

## Tape (mm)

| Item | mm |
| --- | --- |
| Seat height (cushion top) | 445 |
| Overall W / D / H | 445 / 470 / 794 |
| Midrail from seat | 102–146 |
| Stile outer span | 368 (1″ thick) |
| Mid→upper bottom / top (from mid bottom) | +114 / +254 → upper ~140 tall; back ~356 above seat |
| Top rail max width / thick | 533 / 16 |
| Cushion thick | 19 |
| Side stretcher / rear stretcher AFF | 229 / 330 |

## Export target
`lab/furniture_cad/examples/bespoke/chair_02.py` → `out/chair_02_bespoke/` (STEP + STL + optional preview PNG).

## Bar (Gauntlet)
Blind compare export / preview to `evals/photos/chairs/chair_02.jpg`. Must read as the same chair: post inflection direction, apron under overhang, connected rails, crescent top rail with posts stopping mid-rail height.
