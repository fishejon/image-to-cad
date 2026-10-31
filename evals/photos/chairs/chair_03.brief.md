# Construction brief — chair_03 (bar stool, tube + wood)

Designer / CAD brief from user photo + tape. Implement as **bespoke** (or SPEC sweeps + panels), not wood `four_leg_chair`.

## Character
Standard-height **bar stool**: matte **black round metal tube** frame, **light oak/birch laminate** seat and back panels. Minimal. Four legs; rear uprights continue past the seat and curve into the backrest supports. Square **footrest ring** about one-third up the legs. Seat and back are separate flat plates with soft-rounded corners (back more pill-like).

## Members

| Member | Intent |
| --- | --- |
| Seat panel | Flat rectangle, lightly rounded corners; ~15.25″ W × 12.5″ D; ~½–¾″ thick laminate. Top ~24.5″ AFF. |
| Back panel | Wider horizontal pill / soft rectangle; same wood face; sits above seat on two tube supports that attach near the rear face of the panel. |
| Front legs | Straight round tube to floor; meet front seat-frame corners. Slight visual taper optional (photo reads nearly constant dia). |
| Rear uprights | Continuous floor → above seat → curve **back / out** into backrest mounts. Not a separate stick back. |
| Seat frame | Thin tube under seat edges tying the four uprights (hidden under panel overhang in places). |
| Footrest ring | Square perimeter of thinner rod/tube joining the four legs ~⅓ up from floor (structural + footrest). Front rail is the primary foot bar. |

## Side / ¾ reading (critical)

```text
  back panel (wood)
        |
        )  tube curves aft / out above seat
        |
  seat _____|
       |    |
       |    |  rear upright continuous
       |    |
  ring-+----+  footrest ~⅓ height
       |    |
     foot foot
```

Overall depth (~17″) > seat depth (12.5″) because the backrest and curved supports sit behind / overhang the seat rear.

## Tape (authoritative)

| Item | in | mm |
| --- | --- | --- |
| Overall height (incl. back) | 37.25 | 946 |
| Seat height (top of seat) | 24.5 | 622 |
| Seat depth | 12.5 | 318 |
| Overall depth (incl. back) | ~17 | 432 |
| Seat width | 15.25 | 387 |

Estimated (photo only, not taped): tube Ø ~⅝″ (16 mm); footrest ~8–10″ AFF; seat/back panel t ~16 mm; back clear above seat ~10–12″.

## Missing blocks / risks
- `tube_frame` continuous rear upright with bend into back supports
- `panel_seat_back` thin wood plates on metal (not pillow cushions)
- `footrest_ring` square stretcher at bar height
- Generic dining-chair few-shot (wood sweeps + crest + pillow) will **mis-steer** Create unless inventory tags metal tube + panels

## Export target
`lab/furniture_cad/examples/bespoke/chair_03.py` → `out/chair_03_bespoke/` (or browser Create with measured dims in hints).

## Bar
Blind compare to `chair_03.jpg`: tall stool proportions, wood seat + pill back, black tube, square foot ring, rear posts continuous into back.
