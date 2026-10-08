# Design spec reference

A design is one JSON object. The app, the AI, the checks, the exporter and the build guide all work from it. Units are **millimetres**, **Z is up**, **X is the long side**, the **front faces −Y**, and the origin is the centre of the footprint on the floor.

```jsonc
{
  "name": "Plant stand",
  "description": "free text",
  "assumptions": ["things you guessed"],
  "params":     { ... },      // numbers and derived values
  "materials":  { ... },
  "groups":     [ ... ],
  "steps":      [ ... ],      // assembly sequence
  "kinematics": { ... },      // sliders for moving parts
  "parts":      [ ... ],      // required
  "guide":      [ ... ]       // optional hand-written build-guide pages
}
```

## Expressions
Anywhere a number is expected you may write an expression string: `"W/2 - t"`.
Operators `+ - * / % ^ ( )` and comparisons `< > <= >= == !=` (true = 1). Functions: `min max abs round floor ceil sqrt pow mod sin cos tan atan2 clamp if(c,a,b)`. Trig uses **degrees**. Variables are the params, the part's `vars`, and the `repeat` variable. Expressions are parsed by a small hand-written parser; there is no `eval` and no access to anything outside the variables you define.

## params
```json
"params": {
  "W":  { "value": 900, "min": 600, "max": 1400, "step": 50, "label": "Width", "unit": "mm" },
  "n":  4,
  "t":  { "expr": "18" },
  "Wi": { "expr": "W - 2*t" }
}
```
* An object with `value`, or a bare number, becomes a **slider** in the Design tab (a bare number gets a ±50 % range).
* `{ "expr": ... }` (or a plain string) is a **derived** value with no slider.
* Params are evaluated **in order**: define a name before you use it.

## materials
Built-in ids: `wood` (walnut) `oak pine ply marble steel aluminium brass plastic glass rubber fabric concrete paint`. Redefine or add your own:
```json
"materials": { "oak": { "base": "oak" }, "shade": { "base": "fabric", "color": "#f1e7d3" },
               "enamel": { "color": "#d9d9d4", "metal": 0, "rough": 0.5, "rho": 700 } }
```
`rho` is density in kg/m³ (used for the weight estimate). `tex` can be `"wood"` or `"marble"` (procedural textures); `tint` multiplies the wood texture; `alpha` makes a material translucent.

## groups and steps
```json
"groups": [{ "id": "carcass", "name": "Carcass", "color": "#6aa6ff" }],
"steps":  ["Glue the sides", { "title": "Fit the back", "notes": ["Do not glue it."], "tools": ["Clamps"], "tip": "...", "check": "..." }]
```
`parts[].group` picks the group (unknown groups are created automatically). An instance's `step` number is the index into `steps`; the Assemble timeline, the exploded view and the build guide all follow it.

## kinematics
```json
"kinematics": {
  "drawer": { "label": "Drawer", "axis": [0,-1,0], "range": [0, 300] },
  "door":   { "label": "Door", "unit": "deg", "axis": [0,0,1], "pivot": [0,-190,100], "range": [0, 110] }
}
```
Give instances `"kin": "drawer"` and they move with that slider (translation along `axis`, or rotation about `axis` through `pivot` when `unit` is `"deg"`). Checks run at the home position (value = range start).

## parts
One entry per **physical part type**; place it many times with `instances`.
```json
{ "id": "leg", "name": "Leg", "group": "legs", "material": "oak", "kind": "solid", "grain": "z",
  "spec": "40 × 40 mm", "notes": ["Cut the tenon 20 × 20 × 15."], "tools": ["Tenon saw"],
  "vars": { "legH": "H - 20" },
  "ops": [ ... ],            // kind "solid"
  "prims": [ ... ],          // kind "mesh"
  "instances": [ ... ] }
```

### kind "solid" (exact boolean geometry)
```json
"ops": [
  { "add": [0,0,0, 40,40,"legH"] },
  { "add": [10,10,"legH", 30,30,"legH+15"], "tag": "tenon", "label": "Tenon 20 × 20 × 15" },
  { "cut": [10,10,5, 30,30,25], "tag": "mortise", "label": "Mortise 20 × 20 × 20", "fill": true }
]
```
* A box is `[x0,y0,z0, x1,y1,z1]` in the part's **local** frame; corners are normalised.
* All `add` boxes are united, then all `cut` boxes are removed. The result is a watertight mesh with exact volume.
* `tag` + `label` document a joint. The **build guide** highlights them (cuts orange, adds green) and the **Inspect** tab lists them.
* `"fill": true` on a cut says *a mating part must completely occupy this void* (mortise, dado, groove, rabbet). The **joint-fill check** measures how much of it is filled by other parts. Leave it off for deliberate voids (finger pulls, door tracks, hand holes).
* Solid parts should only be rotated by multiples of 90° (so their boxes stay axis-aligned for the exact checks).
* Only solid parts can be **auto-split** for 3D printing.

### kind "mesh" (round, turned, sloped parts)
```json
"prims": [
  { "type": "cylinder", "base": [0,0,0], "axis": "+z", "length": 400, "r": 15, "seg": 28 },
  { "type": "cone",   "base": [0,0,0], "axis": "+z", "length": 50, "r0": 20, "r1": 10 },
  { "type": "tube",   "base": [0,0,100], "axis": "+z", "length": 20, "ro": 90, "ri": 70 },
  { "type": "sphere", "r": 30, "center": [0,0,200] },
  { "type": "revolve", "at": [0,0,0], "axis": "+z", "profile": [[0,0],[80,0],[80,6],[0,48]] },
  { "type": "extrude", "plane": "xy", "profile": [[0,0],[100,0],[100,50]], "range": [0,20], "holes": [{ "c": [30,10], "r": 4 }] },
  { "type": "box", "min": [0,0,0], "max": [10,10,10] }
]
```
`axis` is one of `+x -x +y -y +z -z`. `revolve` profiles are `[radius, height-along-axis]` pairs. One material per part. Mesh parts render, export to STL (whole) and count in mass, but are **excluded from interference and joint-fill checks** (they are approximated by their bounding box for explode and clash display).

### instances
```json
"instances": [
  { "pos": [0,0,0], "rot": [0,0,90], "step": 0, "explode": [0,0,120], "kin": "drawer",
    "repeat": { "var": "i", "count": 4 } }
]
```
Placement = `translate(pos) · Rz · Ry · Rx` (degrees). Omit `explode` for an automatic exploded view (radial from the model centre, longer for later steps). `repeat` also works on `ops` and `prims`; use the variable inside expressions: `"pos": ["i*50", 0, 0]`. Omit `instances` entirely to place one copy at the origin.

## guide (optional)
If present, `guide` replaces the auto-generated build guide. Each page: `{ "kind": "hero|flat|cutlist|part|asm|subset|text", "phase", "title", "text": ["html bullets"], "tools": [], "tip", "chk" }` plus kind-specific keys (`focus`+`tags`+`dir`+`zoom` for `part`, `asm` for `asm`, `show` for `subset`). See `examples/sideboard.json`. **HTML in guide text is only honoured for the built-in examples**; for any other spec only `<b>`, `<i>` and `<br>` survive.

## Validation
Every problem is reported with its path, e.g. `parts[3] (shelf).ops[2]: unknown variable "Wc"`. Errors skip the offending item and the rest still builds when possible; the Spec tab lists them. Checks: watertight meshes, exact part-to-part interference, joint fill, print-bed fit, STL round trip.
