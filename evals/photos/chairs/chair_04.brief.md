# Construction brief — chair_04 (Lakin oak dining)

Catalog / studio photo + published dims (Crate & Barrel Lakin). **Local eval only** — do not redistribute the product photo. Implement as **bespoke** (or rich SPEC), not generic `four_leg_chair`.

## Character
Blond **solid white oak** dining side chair. Mix of straight lines and soft curves: **tapered legs**, **angled / raked back**, **slanted stance**. **Inset** oatmeal flecked linen-like cushion (not a big overhang pillow). Single horizontal **back panel** (slight concave) between two continuous rear posts. Front apron↔leg junction reads as a deep organic fillet / sweep, not a butt joint.

## Members

| Member | Intent |
| --- | --- |
| Seat cushion | Inset into frame; rounded corners; ~1½″ visual thickness; oatmeal upholstery. |
| Seat rails / apron | Oak frame around cushion; side rails flow into front legs with a **curved transition**. |
| Front legs | Tapered (wider at seat → narrower at foot); slight outward/forward slant in stance; soft rectangular section (rounded edges). |
| Rear posts | **Continuous** floor → above back panel; rake backward above seat; flare outward/back below seat for stability. Tops slightly rounded. |
| Back panel | Horizontal oak board, slight scoop; grain runs sideways; spans between posts. |
| Glides | Small dark pads under feet (optional in CAD). |

## Side / ¾ reading (critical)

```text
  back panel
     |  |
     |  |  posts rake aft above seat
  seat|__|
     /    \
    /      \  rear flare out/back below seat
   /        \
 foot      foot

Front: leg ↔ apron is a **smooth curve**, not a sharp corner.
```

## Tape / catalog (authoritative)

| Item | in | mm |
| --- | --- | --- |
| Overall W | 18 | 457 |
| Overall D | 20.63 | 524 |
| Overall H | 32 | 813 |
| Seat height | 19.5 | 495 |
| Seat depth | 18.5 | 470 |
| Weight | 12.7 lb | — |

Estimated (photo only): cushion ~35–45 mm; back panel ~12–16 mm; post section ~35–45 mm at seat; taper to ~20–25 mm at foot.

## Missing blocks / risks
- `continuous_raked_post` rear leg+stile as one curved member
- `leg_apron_fillet` organic front junction (hard for stick boxes)
- `inset_cushion` (vs dining-chair overhang pillow)
- Studio white background → silhouette IoU is **favorable** vs room photos; still measure after build

## Export target
`lab/furniture_cad/examples/bespoke/chair_04.py` → `out/chair_04_bespoke/`

## Bar
Must read as Lakin: blond oak, inset cushion, raked continuous back, tapered front legs with curved apron junction, tall open back panel.
