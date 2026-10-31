/* vision.js — picture → design spec, with the Gauntlet loop built in:
   inventory (structured vision) → builder (LLM writes a spec) ⇄ critic (geometry + likeness) until satisfied. */
(function (root) {
'use strict';
const CAD = root.CAD, V = CAD.vision = {};

/* A tiny but complete example. It is embedded in the prompt AND unit-tested, so the prompt can never drift from the engine. */
V.EXAMPLE = {
  name: 'Plant stand', units: 'mm', description: 'Square oak top with four legs, each leg tenoned into a blind mortise.', assumptions: ['Overall size guessed from the picture.'],
  params: { S: { value: 300, min: 200, max: 500, step: 10, label: 'Top size' }, H: { value: 420, min: 250, max: 700, step: 10, label: 'Height' } },
  materials: { oak: { base: 'oak' } }, groups: [{ id: 'legs', name: 'Legs' }, { id: 'top', name: 'Top' }], steps: ['Glue the legs into the top'],
  parts: [
    { id: 'leg', name: 'Leg', group: 'legs', material: 'oak', grain: 'z', spec: '40 × 40 mm, 15 mm tenon', notes: ['Cut the tenon 20 × 20 × 15 mm.'], ops: [{ add: [0, 0, 0, 40, 40, 'H-20'] }, { add: [10, 10, 'H-20', 30, 30, 'H-5'], tag: 'tenon', label: 'Tenon 20 × 20 × 15' }],
      instances: [{ pos: ['if(mod(i,2)==0,-1,1)*(S/2-35)-20', 'if(i<2,-1,1)*(S/2-35)-20', 0], step: 0, repeat: { var: 'i', count: 4 } }] },
    { id: 'top', name: 'Top', group: 'top', material: 'oak', grain: 'x', spec: 'S × S × 20 mm', notes: ['Chop four blind mortises 20 × 20 × 15 mm.'],
      ops: [{ add: ['-S/2', '-S/2', 'H-20', 'S/2', 'S/2', 'H'] }, { cut: ['if(mod(i,2)==0,-1,1)*(S/2-35)-10', 'if(i<2,-1,1)*(S/2-35)-10', 'H-20', 'if(mod(i,2)==0,-1,1)*(S/2-35)+10', 'if(i<2,-1,1)*(S/2-35)+10', 'H-5'], repeat: { var: 'i', count: 4 }, tag: 'mortise', fill: true, label: 'Mortise 20 × 20 × 15' }],
      instances: [{ pos: [0, 0, 0], step: 0 }] },
  ],
};

V.SPEC_DOC = `
# DESIGN SPEC (JSON) — numeric geometry is millimetres (the engine's unit). Z is up, X is the long side, the FRONT faces -Y, origin is the centre of the footprint on the floor. User-facing text (name, description, spec, notes, labels, param labels) MUST use inches to the nearest 1/16, written as fractions under 1" (3/4\" not 0.75\") and mixed numbers above (12 3/16\"). Lumber thickness in user-facing text uses quarters only (7/4\" not 1 3/4\"). Convert: 1 inch = 25.4 mm.
Top-level keys: name, description, reasoning (string), assumptions[], params{}, materials{}, groups[], steps[], kinematics{}, parts[] (required).
reasoning: 4–8 sentences explaining what you see in the picture (or what you changed on revise), key proportions, major parts counted, and joinery assumptions for hidden structure. Always include this field.
Every NUMBER may be an arithmetic expression string using params, part "vars", and the repeat variable. Operators + - * / % ^ ( ) comparisons < > <= >= == != ; functions min max abs round floor ceil sqrt pow mod sin cos tan atan2 clamp if(c,a,b). Angles are in degrees.
params: { "W": {"value":900,"min":600,"max":1400,"step":50,"label":"Width"}, "t": {"expr":"18"}, "Wi": {"expr":"W-2*t"} }  (objects with "value" become UI sliders; "expr" are derived values; params are evaluated in order, so define a name before using it).
materials: { "oak": {"base":"oak"}, "paint": {"color":"#d9d9d4","metal":0,"rough":0.5,"rho":700} }. Built-in ids: wood(walnut) oak pine ply marble steel aluminium brass plastic glass rubber fabric concrete paint.
groups: [{"id":"carcass","name":"Carcass","color":"#6aa6ff"}]. steps: ["Glue the sides", {"title":"...","notes":["..."],"tools":["..."],"tip":"...","check":"..."}] — index = the "step" number of the parts placed in that step.
kinematics: { "drawer": {"label":"Drawer","axis":[0,-1,0],"range":[0,300],"unit":"mm"} }  or rotation: {"unit":"deg","axis":[0,0,1],"pivot":[x,y,z],"range":[0,110]}. Instances with "kin":"drawer" move with it.
parts[]: each part is ONE physical piece type: { "id","name","group","material","kind":"solid"|"mesh","grain":"x"|"y"|"z","spec":"size text","notes":[...],"tools":[...], "vars":{...}, "instances":[...] }.
  kind "solid" (default; rectilinear parts, EXACT boolean geometry): "ops":[ {"add":[x0,y0,z0,x1,y1,z1]}, {"cut":[x0,y0,z0,x1,y1,z1],"tag":"mortise","label":"Mortise 24 × 8 × 40","fill":true} ]. Boxes are axis-aligned in the part's LOCAL frame. All "add" boxes are united, then all "cut" boxes removed. "fill":true means a mating part MUST completely occupy that void (mortise, dado, groove, rabbet). "tag"+"label" document a joint so the build guide can show it. Leave "fill" off for deliberate voids (finger pulls, door tracks).
  kind "mesh" (round / turned / angled / non-rectilinear parts): "prims":[ {"type":"box","min":[..],"max":[..],"rot":[rx,ry,rz]}, {"type":"wedge","min":[..],"max":[..],"tip":"+x","angle":45}, {"type":"cylinder","base":[x,y,z],"axis":"+z","length":L,"r":R,"seg":32}, {"type":"cone","base","axis","length","r0","r1"}, {"type":"tube","base","axis","length","ro","ri"}, {"type":"sphere","r":R,"center":[..]}, {"type":"revolve","at":[x,y,z],"axis":"+z","profile":[[radius,height],...],"seg":48}, {"type":"extrude","plane":"xy"|"xz"|"yz","profile":[[u,v],...],"range":[w0,w1],"holes":[{"c":[u,v],"r":R}]}, {"type":"sweep","path":[[x,y,z],...],"curve":"catmull"|"polyline","section":{"type":"rrect"|"ellipse"|"poly","w":W,"h":H,"r":R},"taper":[{"t":0,"scaleW":1,"scaleH":1}],"up":[0,0,1],"frame":"up"|"rmf","twist":0,"caps":"both"|"none","tol":0.15}, {"type":"pillow","size":[X,Y,Z],"planR":R,"edgeR":R,"bulge":{"top":0,"bottom":0},"taper":{"k":0},"bend":0,"tol":0.15}, {"type":"panel","size":[W,H],"t":T,"outline":{"shape":"rect"|"superellipse","fmin":0.55,"n":2.5},"bend":{"radius":R,"sagitta":S,"direction":1},"edgeR":0,"arch":0,"tol":0.15}, {"type":"seam","size":[X,Y,Z],"r":2.5,"inset":12,"side":"top"|"bottom","planR":R,"edgeR":R,"bulge":{"top":0,"bottom":0}} ]. Optional box "rot" is Euler degrees about the box centre. "wedge" is a mitred board. "sweep" = tapered/curved members (fold guard rejects too-tight bends). "pillow" = cushions. "panel" = developable bent sheet (flat blank = cut size). "seam" = welt/piping as its OWN part (different material from the pillow). Prefer kind "solid" for rectilinear carcass so joint-fill stays exact; use mesh for curves, cushions, bent panels, seams.
  instances: [{"pos":[x,y,z],"rot":[rx,ry,rz],"step":0,"explode":[dx,dy,dz],"kin":"name","repeat":{"var":"i","count":4}}]. Placement = translate(pos) · Rz · Ry · Rx. Solid parts should be rotated only by multiples of 90°. "repeat" also works on ops and prims. Omit "explode" to get an automatic exploded view.
Modelling rules: (1) Parts must NOT overlap each other except where a tenon/tongue fills a "fill":true void exactly. (2) Joint voids and the tenon that fills them must have identical dimensions. (3) Model the object as separate real-world parts joined the way the real object is built (mortise & tenon, dados, rabbets, box joints, mitres, bolted flanges...). (4) Use params for the main dimensions so the user can resize. (5) Prefer "solid" parts; use "mesh" for round/turned/sloped/mitred/continuous shapes. (6) Put the object on the floor (min z = 0). (7) Give each part a short real-world "spec" and, when there is a joint to cut, "notes" saying how. (8) Honor inventory.structure: if memberContinuity is continuous, model primary side/frame members as one piece (or mirrored pair), not separate stick legs+arms+posts with magic butt joints. (9) Match inventory section (round vs square vs tapered); do not mix cylinder legs with square posts unless inventory says mixed. (10) Every structural wood–wood meeting needs tag+label joinery (and fill:true on receiving cuts); unlabeled contacts fail the critic. (11) STANCE / RAKE — never default raked or splayed members to vertical sticks. If inventory.structure.legStance is raked/splayed/canted or backRake is aft/forward, legs and posts MUST be mesh "sweep" (or cylinder with non-+Z axis / instance rot). Sweep path: +Z is up, FRONT is −Y, BACK is +Y. Aft rake above the seat means Y increases as Z rises (e.g. path [[0,0,0],[0,8,"Hs"],[0,55,"Hb"]]). Forward lean or front-leg slant uses negative Y as Z rises. Outward splay uses ±X along the path. Do NOT use solid AABB boxes or axis:"+z" cylinders for visibly leaning members.
`;
V.EXAMPLE_JSON = JSON.stringify(V.EXAMPLE);

V.INVENTORY_DOC = `{
  "object": "short name of the object",
  "aspect": {"w": <relative width>, "d": <relative depth>, "h": <relative height>},
  "counts": {"legs": N, "drawers": N, "doors": N, "shelves": N, "slats": N, "other": N},
  "structure": {
    "memberContinuity": "continuous|separate|mixed|unknown",
    "dominantSection": "round|square|rect|tapered|slab|mixed|unknown",
    "legStance": "vertical|splayed|raked|canted|unknown",
    "backRake": "none|aft|forward|unknown",
    "notes": "optional: continuity + stance (e.g. rear posts rake aft above seat; front legs slant outward)"
  },
  "parts": [{"role":"leg|top|side|drawer|door|shelf|rail|panel|stretcher|arm|seat|back|frame|cushion|other","count":N,"shape":"square|rect|turned|panel|tapered|slab|continuous|curved","section":"round|square|rect|tapered|oval|unknown","continuity":"separate|continuous|unknown","lean":"vertical|aft|forward|outboard|inboard|unknown","curved":false,"upholstered":false,"provenance":"measured|assumed|unknown","notes":"optional"}],
  "materialsGuess": ["oak"],
  "joineryGuess": ["mortise and tenon legs into top"],
  "overallGuessMm": {"w":0,"d":0,"h":0},
  "curvedFeatures": [{"part":"crest|leg|seat|back","kind":"sweep|panel|pillow|seam","note":"optional"}],
  "notes": "1–3 sentences on what stands out in the photo"
}`;

/** Parse a length string → mm. Bare numbers and inch marks are inches; explicit "mm" stays millimetres. */
V.parseInch = function (s) {
  s = String(s == null ? '' : s).trim();
  if (!s) return NaN;
  const mmPer = CAD.MM_PER_IN || 25.4;
  const mmSuffix = /\bmm\b/i.test(s);
  s = s.replace(/["″''′]/g, '').replace(/\b(mm|in|inch|inches)\b/gi, '').trim();
  if (!s) return NaN;
  let n;
  const mixed = s.match(/^(\d+)\s+(\d+)\s*\/\s*(\d+)$/);
  if (mixed) n = +mixed[1] + (+mixed[2] / +mixed[3]);
  else {
    const frac = s.match(/^(\d+)\s*\/\s*(\d+)$/);
    if (frac) n = +frac[1] / +frac[2];
    else n = parseFloat(s.replace(/,/g, ''));
  }
  if (!isFinite(n)) return NaN;
  return mmSuffix ? n : n * mmPer;
};
/** Pull W×D×H (mm) from free-text hints and/or structured fields. */
V.parseDims = function (hints, fields) {
  const out = { wMm: 0, dMm: 0, hMm: 0, source: [] };
  const take = (key, v) => {
    const mm = typeof v === 'number' ? v : V.parseInch(v);
    if (mm > 1 && isFinite(mm)) { out[key] = Math.round(mm * 100) / 100; return true; }
    return false;
  };
  fields = fields || {};
  if (fields.w != null && String(fields.w).trim()) take('wMm', fields.w);
  if (fields.d != null && String(fields.d).trim()) take('dMm', fields.d);
  if (fields.h != null && String(fields.h).trim()) take('hMm', fields.h);
  const text = String(hints || '');
  const labeled = [
    [/overall\s*width\s*[:=]?\s*([\d\s./]+(?:\s*(?:mm|in|inch|inches|["″]))?)/i, 'wMm'],
    [/overall\s*depth\s*[:=]?\s*([\d\s./]+(?:\s*(?:mm|in|inch|inches|["″]))?)/i, 'dMm'],
    [/overall\s*height\s*[:=]?\s*([\d\s./]+(?:\s*(?:mm|in|inch|inches|["″]))?)/i, 'hMm'],
    [/\bW\s*[:=]\s*([\d\s./]+(?:\s*(?:mm|in|inch|inches|["″]))?)/i, 'wMm'],
    [/\bD\s*[:=]\s*([\d\s./]+(?:\s*(?:mm|in|inch|inches|["″]))?)/i, 'dMm'],
    [/\bH\s*[:=]\s*([\d\s./]+(?:\s*(?:mm|in|inch|inches|["″]))?)/i, 'hMm'],
    [/\bwidth\s*[:=]?\s*([\d\s./]+(?:\s*(?:mm|in|inch|inches|["″]))?)/i, 'wMm'],
    [/\bdepth\s*[:=]?\s*([\d\s./]+(?:\s*(?:mm|in|inch|inches|["″]))?)/i, 'dMm'],
    [/\bheight\s*[:=]?\s*([\d\s./]+(?:\s*(?:mm|in|inch|inches|["″]))?)/i, 'hMm']
  ];
  labeled.forEach(([re, key]) => {
    if (out[key]) return;
    const m = text.match(re);
    if (m) take(key, m[1]);
  });
  if (!out.wMm || !out.dMm || !out.hMm) {
    const trip = text.match(/([\d]+(?:\s+[\d]+\/[\d]+|\/[\d]+)?(?:\.\d+)?)\s*[×xX]\s*([\d]+(?:\s+[\d]+\/[\d]+|\/[\d]+)?(?:\.\d+)?)\s*[×xX]\s*([\d]+(?:\s+[\d]+\/[\d]+|\/[\d]+)?(?:\.\d+)?)(?:\s*(mm|in|inch|inches|["″]))?/i);
    if (trip) {
      const unit = trip[4] || '';
      const wrap = u => unit ? u + ' ' + unit : u;
      if (!out.wMm) take('wMm', wrap(trip[1]));
      if (!out.dMm) take('dMm', wrap(trip[2]));
      if (!out.hMm) take('hMm', wrap(trip[3]));
      out.source.push('triplet');
    }
  }
  if (out.wMm || out.dMm || out.hMm) out.source.push('parsed');
  return out;
};
V.formatMetrics = function (m) {
  if (!m) return '';
  const bits = [];
  const inch = CAD.fmtInch || (v => (Math.round(v / 25.4 * 16) / 16) + '"');
  if (m.wMm > 0) bits.push('W=' + inch(m.wMm) + ' (' + Math.round(m.wMm) + ' mm)');
  if (m.dMm > 0) bits.push('D=' + inch(m.dMm) + ' (' + Math.round(m.dMm) + ' mm)');
  if (m.hMm > 0) bits.push('H=' + inch(m.hMm) + ' (' + Math.round(m.hMm) + ' mm)');
  return bits.join(', ');
};
/** Merge free-text hints with structured W×D×H into one constraint string for prompts. */
V.composeHints = function (hints, metrics) {
  const t = String(hints || '').trim();
  const m = V.formatMetrics(metrics);
  if (!m) return t;
  const block = 'TARGET OVERALL SIZE (authoritative millimetres; params W/D/H must match within ~2%): ' + m;
  return t ? t + '\n' + block : block;
};

V.buildInventoryPrompt = function (o) {
  o = o || {};
  const drawing = o.inputMode === 'drawing';
  const parts = [
    drawing
      ? 'You are a careful inventory agent reading a TECHNICAL DRAWING or dimensioned sketch for furniture/product CAD. Prefer printed/handwritten dimensions and callouts over photographic guessing. Return ONE JSON object (no commentary, no markdown fences) with this shape:'
      : 'You are a careful visual inventory agent for furniture/product CAD. Study the attached picture and return ONE JSON object (no commentary, no markdown fences) with this shape:',
    V.INVENTORY_DOC,
    drawing
      ? 'Rules: (1) Prefer dimensions readable on the drawing; put them in overallGuessMm (millimetres). (2) aspect ratios should match the drawing proportions; normalize so the smallest of w/d/h is about 1. (3) counts are integers for labeled or clearly drawn features. (4) If USER METRICS are provided, copy them into overallGuessMm and treat them as ground truth. (5) parts[].role should cover every distinct piece type needed in a CAD model. (6) structure.memberContinuity: continuous = primary members are one piece (e.g. side frame that is leg+arm+post); separate = discrete sticks joined; mixed = both. (7) structure.dominantSection and parts[].section must match visible cross-sections. (8) STANCE: set structure.legStance (vertical|splayed|raked|canted) and structure.backRake (none|aft|forward); set parts[].lean when a member leans. (9) Mark curved/upholstered parts and curvedFeatures; set provenance measured vs assumed.'
      : 'Rules: (1) Match what you SEE — do not invent a generic piece of the same category. (2) aspect ratios must reflect the photo; normalize so the smallest of w/d/h is about 1. (3) counts are integers for visible or strongly implied features; prefer under-counting hidden structure over inventing parts. (4) overallGuessMm is optional; leave zeros if scale is unknown — but if USER METRICS are provided, copy them into overallGuessMm. (5) parts[].role should cover every distinct piece type you will need in a CAD model. (6) structure.memberContinuity: continuous = primary members read as one sculpted/laminated piece; separate = discrete sticks; mixed = both. Never report separate stick construction when the photo shows continuous frames. (7) structure.dominantSection and parts[].section must match visible cross-sections. (8) STANCE (critical): if rear legs/posts lean backward above the seat, set backRake="aft" and legStance="raked" (not vertical). If legs flare outward toward the floor, legStance="splayed". Set parts[].lean when a member leans. Never mark vertical when the photo shows a clear rake or slant. (9) Flag curved/upholstery via curvedFeatures; mark provenance measured|assumed.'
  ];
  if (o.metrics && (o.metrics.wMm || o.metrics.dMm || o.metrics.hMm)) {
    parts.push('USER METRICS (ground truth overall size): ' + V.formatMetrics(o.metrics));
  }
  if (o.pastExampleText) parts.push(o.pastExampleText);
  if (o.hints) parts.push('USER HINTS (they override guesses from the picture): ' + o.hints);
  return parts.join('\n\n');
};

V.STAGES = [
  { id: 'carcass', label: 'carcass', focus: 'Build ONLY the primary structure: sides, top, bottom, back, legs, stretchers, rails, frames, and fixed panels. Honor inventory.structure (continuity, section, legStance, backRake). If memberContinuity is continuous: each side must be ONE mesh sweep (mirrored L/R) — NEVER four separate stick legs. RAKE/SPLAY: if legStance is raked/splayed/canted or backRake is aft/forward, every leaning leg/post is a mesh sweep whose path changes Y (aft = +Y, forward = −Y) and/or X (splay) as Z rises — never a vertical solid box or axis:+z cylinder. Example aft back post: path [[0,0,0],[0,10,"Hs"],[0,60,"Hb"]]. Use panel for bent backs; cross rails as solid boxes. No drawers/doors/shelves/cushions yet. Match aspect. Labeled joinery on meetings.' },
  { id: 'interiors', label: 'interiors', focus: 'ADD drawers, doors, shelves, dividers, cushions (pillow prim), seams (separate part), arms (if separate), and other secondary parts from the inventory. Keep every carcass part that is still correct — do not straighten raked sweeps into vertical sticks. Pillow instance pos is the CENTER of the pillow (not a corner) — place it on the seat deck without floating forward. Update mating joinery. Return the COMPLETE updated spec.' },
  { id: 'refine', label: 'refine', focus: 'Polish the COMPLETE design: fix joinery fill, interference, unlabeled contacts, inventory mismatches, floating cushions, missing rake/splay, and curved-prim errors. If inventory says continuous or raked, reject vertical stick legs. Do not remove correct parts. Return the COMPLETE corrected spec.' }
];
V.needsStages = function (inventory) {
  if (!inventory || typeof inventory !== 'object') return false;
  const c = inventory.counts || {};
  const complex = (+c.drawers || 0) + (+c.doors || 0) + (+c.shelves || 0) + (+c.slats || 0);
  const nParts = Array.isArray(inventory.parts) ? inventory.parts.length : 0;
  const st = inventory.structure || {};
  const continuity = String(st.memberContinuity || '').toLowerCase();
  const roles = (inventory.parts || []).map(p => String((p && p.role) || '').toLowerCase());
  const richRoles = roles.some(r => /arm|seat|back|frame|cushion|rail|stretcher/.test(r));
  return complex >= 1 || nParts >= 5 || continuity === 'continuous' || continuity === 'mixed' || richRoles;
};
/** Merge next into base by part id (next wins). Keeps base parts the next draft omitted. */
V.mergeSpecs = function (base, next) {
  if (!next) return base; if (!base) return next;
  const out = Object.assign({}, base, next);
  const map = new Map();
  (base.parts || []).forEach(p => { if (p && p.id != null) map.set(p.id, p); });
  (next.parts || []).forEach(p => { if (p && p.id != null) map.set(p.id, p); });
  out.parts = [...map.values()];
  out.materials = Object.assign({}, base.materials || {}, next.materials || {});
  out.params = Object.assign({}, base.params || {}, next.params || {});
  out.kinematics = Object.assign({}, base.kinematics || {}, next.kinematics || {});
  const gmap = new Map();
  [].concat(base.groups || [], next.groups || []).forEach(g => { if (g && g.id != null) gmap.set(g.id, Object.assign({}, gmap.get(g.id) || {}, g)); });
  if (gmap.size) out.groups = [...gmap.values()];
  if (Array.isArray(next.assumptions) && next.assumptions.length) out.assumptions = next.assumptions;
  if (Array.isArray(next.steps) && next.steps.length) out.steps = next.steps;
  return out;
};

V.metricsBlock = function (metrics) {
  if (!metrics || !(metrics.wMm || metrics.dMm || metrics.hMm)) return '';
  return 'USER METRICS (authoritative overall size in millimetres — set params so the finished model AABB is within ~2% of these): ' + V.formatMetrics(metrics) +
    '. Prefer params named W, D, H (or Width/Depth/Height) with those values.';
};
V.buildPrompt = function (o) {
  o = o || {}; const parts = [];
  const drawing = o.inputMode === 'drawing';
  const pushMetrics = () => { const b = V.metricsBlock(o.metrics); if (b) parts.push(b); };
  const pushPast = () => { if (o.pastExampleText) parts.push(o.pastExampleText); };
  if (o.task === 'revise' && o.prevSpec && (o.round === 1 || !o.report)) {
    parts.push('You are revising an existing CAD design spec. Apply the user\'s requested changes and return the COMPLETE updated spec as ONE JSON object (no commentary, no markdown fences). Keep everything that is not mentioned. Preserve joinery: if you move or resize a part, update its mating mortises/tenons so they still fill. Include an updated "reasoning" field describing what you changed and why.');
    parts.push(V.SPEC_DOC); parts.push('CURRENT SPEC:\n' + JSON.stringify(o.prevSpec));
    parts.push('REQUESTED CHANGES: ' + (o.hints || '(none)'));
    pushMetrics(); pushPast();
    if (o.focusJoint) {
      const j = o.focusJoint;
      const cur = j.method || 'unknown';
      const req = j.requestedMethod || null;
      const reqLab = req && CAD.jointMethodLabel ? CAD.jointMethodLabel(req) : req;
      const curLab = CAD.jointMethodLabel ? CAD.jointMethodLabel(cur) : cur;
      let fj = 'FOCUS JOINT: cut "' + (j.cutId || '') + '"' + (j.cutTag ? ' tag ' + j.cutTag : '') +
        ' ↔ add "' + (j.addId || '') + '"' + (j.addTag ? ' tag ' + j.addTag : '') +
        '; current method ' + cur + (curLab ? ' (' + curLab + ')' : '') +
        (j.label ? '; label "' + j.label + '"' : '') +
        (req ? '; requested: ' + req + (reqLab ? ' (' + reqLab + ')' : '') : '') +
        '. Rewrite only this connection and its mating ops on those two parts; keep unrelated parts.';
      if (req && CAD.jointInterlockingHint) {
        const hint = CAD.jointInterlockingHint(req);
        if (hint) fj += ' ' + hint;
      }
      parts.push(fj);
    }
    if (o.focusParts && o.focusParts.length) parts.push('FOCUS: Prefer changing only these parts (and any joints that mate with them). Leave unrelated parts alone unless the change requires it: ' + o.focusParts.map(p => p.id + ' ("' + p.name + '")').join(', ') + '.');
  } else if (o.stage) {
    parts.push('You are an expert CAD engineer building a furniture/product design in stages. Current stage: ' + o.stage.label.toUpperCase() + '.');
    parts.push('STAGE FOCUS: ' + o.stage.focus);
    parts.push('Return ONE COMPLETE JSON design spec for this stage (no commentary, no markdown fences). Include "reasoning" describing what you added or changed in this stage.');
    parts.push(V.COMPACT_JSON_RULES);
    if (o.inventory) parts.push('INVENTORY (authoritative for counts, proportions, and structure — honor memberContinuity and dominantSection):\n' + JSON.stringify(o.inventory));
    parts.push(V.SPEC_DOC); parts.push('Minimal valid example:\n' + V.EXAMPLE_JSON);
    if (o.prevSpec) parts.push('SPEC SO FAR (build on this; keep correct parts):\n' + JSON.stringify(o.prevSpec));
    if (o.hints) parts.push('USER HINTS: ' + o.hints);
    pushMetrics(); pushPast();
    if (o.report) parts.push('CRITIC REPORT from the previous attempt — fix these issues:\n' + o.report.text);
  } else if (o.round === 1 || !o.prevSpec) {
    if (drawing) {
      parts.push('You are an expert CAD engineer. The attached image is a TECHNICAL DRAWING or dimensioned sketch (not a photo). Read dimensions, callouts, and part counts carefully and write a design spec for THAT object as ONE JSON object that follows the DESIGN SPEC below.');
      parts.push('Prefer printed/handwritten sizes over guessed scale. Match labeled overall width×depth×height when present. Count drawers/doors/legs/shelves from the drawing. Honor inventory.structure (continuous vs separate members; section). Where a dimension is missing, choose a plausible construction and list it in "assumptions". Always include top-level "reasoning" (2–4 sentences) covering: (1) what the drawing shows, (2) key dimensions, (3) major parts and continuity, (4) joinery assumptions. Return ONLY the JSON object: no commentary, no markdown fences.');
    } else {
      parts.push('You are an expert CAD engineer and furniture/product designer. Study the attached picture carefully and write a design spec for a 3D model of THAT object, as ONE JSON object that follows the DESIGN SPEC below.');
      parts.push('Match what you SEE — not a generic piece in the same category. Count drawers/doors/legs/shelves/slats; match overall width:depth:height proportions from the photo; match member continuity and cross-section from inventory.structure; match leg shape, top overhang, and visible joinery or hardware. Where something is hidden, choose the most plausible construction and list it in "assumptions". Always include top-level "reasoning" (2–4 sentences) covering: (1) what object you see, (2) proportions, (3) major parts and continuity/section, (4) joinery assumptions. Return ONLY the JSON object: no commentary, no markdown fences.');
    }
    parts.push(V.COMPACT_JSON_RULES);
    if (o.inventory) parts.push('INVENTORY (authoritative for object identity, part counts, proportions, and structure — your spec MUST match these counts, aspect ratios, memberContinuity, and dominantSection):\n' + JSON.stringify(o.inventory));
    parts.push(V.SPEC_DOC); parts.push('Minimal valid example:\n' + V.EXAMPLE_JSON);
    if (o.hints) parts.push('USER HINTS (they override anything you guess from the picture): ' + o.hints);
    pushMetrics(); pushPast();
    if (o.report) parts.push('YOUR PREVIOUS REPLY WAS REJECTED:\n' + o.report.text);
  } else {
    parts.push('You are the BUILDER in a builder/critic loop. Below are your previous spec and the CRITIC report from an exact geometry checker' + (o.mode === 'visual' ? ' plus a render of your model next to the reference picture' : '') + '. Fix every issue and return the COMPLETE corrected spec as ONE JSON object (no commentary, no fences). Keep everything that was already correct. Refresh "reasoning" if you change the design.');
    parts.push(V.COMPACT_JSON_RULES);
    parts.push(V.SPEC_DOC); if (o.hints) parts.push('USER HINTS: ' + o.hints);
    pushMetrics(); pushPast();
    if (o.inventory) parts.push('INVENTORY (still authoritative for counts, proportions, and structure):\n' + JSON.stringify(o.inventory));
    parts.push('PREVIOUS SPEC:\n' + JSON.stringify(o.prevSpec)); parts.push('CRITIC REPORT:\n' + (o.report ? o.report.text : ''));
    if (o.focusJoint) {
      const j = o.focusJoint;
      parts.push('FOCUS JOINT (still authoritative): ' + (j.cutId || '') + ' ↔ ' + (j.addId || '') +
        (j.requestedMethod ? '; requested method ' + j.requestedMethod : '') +
        '. Keep fixing this connection until joinery is labeled and filled.');
    }
    if (o.mode === 'visual') parts.push('VISUAL CRITIQUE: image 1 is the reference picture, image 2 is the render of your spec. Compare proportions (width : depth : height), number and size of parts (legs, drawers, shelves, slats), member continuity and cross-section, leg/foot shape and any visible details. If they differ materially, correct the spec. If it already matches, return the spec unchanged.');
  }
  return parts.join('\n\n');
};
V.extractJSON = function (text) {
  if (typeof text !== 'string') throw new Error('empty model response'); let s = text.replace(/```(?:json)?/gi, '').trim(); const a = s.indexOf('{'); if (a < 0) throw new Error('no JSON object found in the model response');
  let depth = 0, inStr = false, esc = false, end = -1; for (let i = a; i < s.length; i++) { const c = s[i]; if (inStr) { if (esc) esc = false; else if (c === '\\') esc = true; else if (c === '"') inStr = false; } else if (c === '"') inStr = true; else if (c === '{') depth++; else if (c === '}') { depth--; if (!depth) { end = i; break; } } }
  if (end < 0) throw new Error('JSON object is truncated (the model ran out of space). Ask for a smaller design.'); return JSON.parse(s.slice(a, end + 1));
};
V.dataUrlToImage = function (u) { const m = /^data:([^;]+);base64,(.*)$/.exec(u); if (!m) throw new Error('bad data URL'); return { mediaType: m[1], base64: m[2] }; };

/* ---------- likeness: inventory + silhouette ---------- */
V.normalizeAspect = function (w, d, h) {
  const a = [Math.max(1e-6, +w || 0), Math.max(1e-6, +d || 0), Math.max(1e-6, +h || 0)];
  const m = Math.min(a[0], a[1], a[2]);
  return { w: a[0] / m, d: a[1] / m, h: a[2] / m };
};
V.maskIoU = function (a, b) {
  if (!a || !b || a.length !== b.length || !a.length) return 1;
  let inter = 0, uni = 0;
  for (let i = 0; i < a.length; i++) {
    const A = a[i] > 0, B = b[i] > 0;
    if (A && B) inter++;
    if (A || B) uni++;
  }
  return uni ? inter / uni : 1;
};
/** Infer instance counts by coarse role from part ids/names/groups. */
V.countRoles = function (M) {
  const roles = { legs: 0, drawers: 0, doors: 0, shelves: 0, slats: 0, other: 0 };
  if (!M || !M.defs) return roles;
  M.defs.forEach(d => {
    const blob = ((d.id || '') + ' ' + (d.name || '') + ' ' + (d.grp || '')).toLowerCase();
    const n = d.qty || 0;
    if (/leg|foot|post/.test(blob)) roles.legs += n;
    else if (/drawer/.test(blob)) roles.drawers += n;
    else if (/door/.test(blob)) roles.doors += n;
    else if (/shelf|shelve/.test(blob)) roles.shelves += n;
    else if (/slat|spindle|dowel/.test(blob)) roles.slats += n;
    else roles.other += n;
  });
  return roles;
};
/**
 * Measure lean in a sweep path: lateral travel vs height (Y = depth, X = width, Z = up).
 * Returns { dy, dx, dz, aftLean, splay } in mm when numbers are numeric; exprs ignored as 0.
 */
V.pathLean = function (path) {
  const num = (v) => { const n = +v; return isFinite(n) ? n : 0; };
  if (!Array.isArray(path) || path.length < 2) return { dy: 0, dx: 0, dz: 0, aftLean: false, splay: false };
  let minZ = Infinity, maxZ = -Infinity, yAtMin = 0, yAtMax = 0, xAtMin = 0, xAtMax = 0;
  path.forEach(pt => {
    if (!Array.isArray(pt) || pt.length < 3) return;
    const x = num(pt[0]), y = num(pt[1]), z = num(pt[2]);
    if (z <= minZ) { minZ = z; yAtMin = y; xAtMin = x; }
    if (z >= maxZ) { maxZ = z; yAtMax = y; xAtMax = x; }
  });
  const dz = maxZ - minZ, dy = yAtMax - yAtMin, dx = xAtMax - xAtMin;
  return { dy, dx, dz, aftLean: dz > 20 && Math.abs(dy) / dz > 0.04, splay: dz > 20 && Math.abs(dx) / dz > 0.04 };
};
/** Infer stance from the raw SPEC (sweep paths / vertical cylinders). */
V.analyzeStance = function (spec) {
  const out = { leanSweeps: 0, verticalLegs: 0, stance: 'unknown', detail: [] };
  if (!spec || !Array.isArray(spec.parts)) return out;
  spec.parts.forEach(p => {
    if (!p) return;
    const blob = ((p.id || '') + ' ' + (p.name || '') + ' ' + (p.role || '')).toLowerCase();
    const isLeggy = /leg|post|stile|frame|upright/.test(blob);
    if (!isLeggy) return;
    let leaned = false;
    (p.prims || []).forEach(pr => {
      if (!pr) return;
      if (pr.type === 'sweep' && Array.isArray(pr.path)) {
        const lean = V.pathLean(pr.path);
        if (lean.aftLean || lean.splay) { leaned = true; out.leanSweeps++; out.detail.push({ id: p.id, lean }); }
        else if (lean.dz > 20) out.detail.push({ id: p.id, lean, verticalPath: true });
      }
      if (pr.type === 'cylinder' || pr.type === 'cone' || pr.type === 'tube') {
        const ax = String(pr.axis || '+z').toLowerCase();
        if (ax === '+z' || ax === 'z' || ax === '-z') out.verticalLegs++;
      }
    });
    if ((!p.prims || !p.prims.length) && (p.kind === 'solid' || p.ops) && isLeggy) out.verticalLegs += (p.instances && p.instances.length) || 1;
    if (leaned) return;
    if (p.kind === 'mesh' && (p.prims || []).some(pr => pr && pr.type === 'sweep')) {
      /* sweep without measurable numeric lean (expr-heavy) — do not count as vertical */
    } else if (isLeggy && !(p.prims || []).some(pr => pr && pr.type === 'sweep')) {
      out.verticalLegs += (p.instances && p.instances.length) || 1;
    }
  });
  if (out.leanSweeps >= 1) out.stance = out.detail.some(d => d.lean && d.lean.splay && !d.lean.aftLean) ? 'splayed' : 'raked';
  else if (out.verticalLegs >= 3) out.stance = 'vertical';
  return out;
};
/** Infer section / continuity signals from a built SpecModel (category-agnostic). */
V.inferStructure = function (M) {
  const out = { memberContinuity: 'unknown', dominantSection: 'unknown', partSections: [], mixedSection: false };
  if (!M || !M.defs || !M.defs.size) return out;
  const sections = [];
  M.defs.forEach(d => {
    const blob = ((d.id || '') + ' ' + (d.name || '') + ' ' + (d.grp || '')).toLowerCase();
    let section = 'unknown';
    if (d.solid && d.solid.exact === false) {
      /* mesh: look at prim types via size aspect of bbox as weak hint; cylinder-like → round */
      const sz = d.size || [0, 0, 0];
      const sorted = sz.slice().sort((a, b) => a - b);
      if (sorted[0] > 1 && Math.abs(sorted[0] - sorted[1]) / sorted[1] < 0.25 && sorted[2] > sorted[1] * 1.5) section = 'round';
      else if (/cyl|turn|dowel|spindle|round/.test(blob)) section = 'round';
      else section = 'mixed';
    } else {
      const sz = d.size || [0, 0, 0];
      const sorted = sz.slice().sort((a, b) => a - b);
      if (sorted[0] > 1 && Math.abs(sorted[0] - sorted[1]) / Math.max(sorted[1], 1) < 0.2) section = 'square';
      else section = 'rect';
    }
    out.partSections.push({ id: d.id, section, qty: d.qty || 0 });
    if (d.qty) for (let i = 0; i < d.qty; i++) sections.push(section);
  });
  const uniq = [...new Set(sections.filter(s => s !== 'unknown'))];
  out.dominantSection = uniq.length === 1 ? uniq[0] : (uniq.length > 1 ? 'mixed' : 'unknown');
  out.mixedSection = uniq.indexOf('round') >= 0 && (uniq.indexOf('square') >= 0 || uniq.indexOf('rect') >= 0);
  /* continuous heuristic: few structural defs that span height, named frame/side, or mesh with large extent */
  let tallMesh = 0, stickLegs = 0;
  M.defs.forEach(d => {
    const blob = ((d.id || '') + ' ' + (d.name || '')).toLowerCase();
    const h = d.size ? d.size[2] : 0;
    if (/frame|side.?frame|arm.?leg|continuous/.test(blob)) tallMesh += d.qty || 0;
    if (d.solid && d.solid.exact === false && h > (M.size ? M.size[2] * 0.55 : 0)) tallMesh += d.qty || 0;
    if (/leg|post|dowel/.test(blob) && !(d.solid && d.solid.exact === false && h > (M.size ? M.size[2] * 0.7 : 99999))) stickLegs += d.qty || 0;
  });
  if (tallMesh >= 2 && stickLegs <= 2) out.memberContinuity = 'continuous';
  else if (stickLegs >= 3) out.memberContinuity = 'separate';
  else if (tallMesh && stickLegs) out.memberContinuity = 'mixed';
  return out;
};
V.likeness = function (M, inventory, o) {
  o = o || {};
  const out = { penalty: 0, aspectErr: 0, countMismatches: [], structureIssues: [], iou: null, text: '' };
  if (!inventory || typeof inventory !== 'object') return out;
  const L = [];
  if (inventory.aspect && M && M.size && M.size[0] > 0) {
    const want = V.normalizeAspect(inventory.aspect.w, inventory.aspect.d, inventory.aspect.h);
    const got = V.normalizeAspect(M.size[0], M.size[1], M.size[2]);
    const err = Math.abs(want.w - got.w) + Math.abs(want.d - got.d) + Math.abs(want.h - got.h);
    out.aspectErr = err;
    if (err > 0.45) {
      const pen = Math.min(40, Math.round(err * 18));
      out.penalty += pen;
      L.push('LIKENESS aspect: inventory w:d:h ≈ ' + [want.w, want.d, want.h].map(x => x.toFixed(2)).join(':') +
        ' but model is ' + [got.w, got.d, got.h].map(x => x.toFixed(2)).join(':') + ' (err ' + err.toFixed(2) + '). Resize params to match the photo proportions.');
    }
  }
  const gotCounts = V.countRoles(M);
  const wantCounts = inventory.counts || {};
  ['legs', 'drawers', 'doors', 'shelves', 'slats'].forEach(k => {
    const want = wantCounts[k];
    if (want == null || !isFinite(+want)) return;
    const got = gotCounts[k] || 0;
    if (got !== +want) {
      out.countMismatches.push({ role: k, expected: +want, got });
      out.penalty += Math.min(25, Math.abs(got - want) * 8);
      L.push('LIKENESS count: expected ' + want + ' ' + k + ' but model has ' + got + '.');
    }
  });
  if (Array.isArray(inventory.parts)) {
    inventory.parts.forEach(p => {
      if (!p || p.count == null) return;
      const role = String(p.role || '').toLowerCase();
      if (!role || role === 'other' || role === 'top' || role === 'side' || role === 'panel' || role === 'rail' || role === 'stretcher' || role === 'arm' || role === 'seat' || role === 'back' || role === 'frame' || role === 'cushion') return;
      const key = /leg|foot|post/.test(role) ? 'legs' : /drawer/.test(role) ? 'drawers' : /door/.test(role) ? 'doors' : /shelf/.test(role) ? 'shelves' : /slat|spindle/.test(role) ? 'slats' : null;
      if (!key || wantCounts[key] != null) return;
      const got = gotCounts[key] || 0;
      if (got !== +p.count) {
        out.countMismatches.push({ role: key, expected: +p.count, got });
        out.penalty += Math.min(25, Math.abs(got - p.count) * 8);
        L.push('LIKENESS count: inventory lists ' + p.count + '× ' + role + ' but model has ' + got + '.');
      }
    });
  }
  /* Structure: continuity + section (category-agnostic) */
  const wantSt = inventory.structure || {};
  const gotSt = V.inferStructure(M);
  out.inferredStructure = gotSt;
  const wantCont = String(wantSt.memberContinuity || '').toLowerCase();
  const gotCont = String(gotSt.memberContinuity || '').toLowerCase();
  if (wantCont && wantCont !== 'unknown' && gotCont && gotCont !== 'unknown' && wantCont !== gotCont) {
    if (!(wantCont === 'mixed' || gotCont === 'mixed')) {
      out.structureIssues.push({ kind: 'continuity', want: wantCont, got: gotCont });
      out.penalty += 28;
      L.push('LIKENESS structure: inventory memberContinuity is "' + wantCont + '" but model reads as "' + gotCont + '". Rebuild primary members to match (continuous = one-piece frames; separate = discrete sticks).');
    }
  }
  const wantSec = String(wantSt.dominantSection || '').toLowerCase();
  if (wantSec && wantSec !== 'unknown' && wantSec !== 'mixed') {
    const gotDom = gotSt.dominantSection || 'unknown';
    const roundWant = wantSec === 'round' || wantSec === 'oval';
    const squareishWant = wantSec === 'square' || wantSec === 'rect' || wantSec === 'slab' || wantSec === 'tapered';
    if (gotSt.mixedSection) {
      out.structureIssues.push({ kind: 'section', want: wantSec, got: 'mixed' });
      out.penalty += 22;
      L.push('LIKENESS structure: inventory dominantSection is "' + wantSec + '" but the model mixes round and square/rect members. Match cross-sections to the inventory (do not invent dowel legs on a square-stock frame or vice versa).');
    } else if (roundWant && gotDom !== 'unknown' && gotDom !== 'round') {
      out.structureIssues.push({ kind: 'section', want: wantSec, got: gotDom });
      out.penalty += 18;
      L.push('LIKENESS structure: inventory dominantSection is "' + wantSec + '" but model is mostly "' + gotDom + '".');
    } else if (squareishWant && gotDom === 'round') {
      out.structureIssues.push({ kind: 'section', want: wantSec, got: gotDom });
      out.penalty += 18;
      L.push('LIKENESS structure: inventory dominantSection is "' + wantSec + '" but model is mostly "' + gotDom + '".');
    }
  }
  /* Stance / rake: inventory asked for lean but SPEC is plumb sticks */
  const wantStance = String(wantSt.legStance || '').toLowerCase();
  const wantBack = String(wantSt.backRake || '').toLowerCase();
  const wantsLean = /raked|splayed|canted/.test(wantStance) || /aft|forward/.test(wantBack)
    || (Array.isArray(inventory.parts) && inventory.parts.some(p => p && /aft|forward|outboard|inboard/.test(String(p.lean || ''))));
  if (wantsLean && o.spec) {
    const gotStance = V.analyzeStance(o.spec);
    out.inferredStance = gotStance;
    if (gotStance.stance === 'vertical' || (gotStance.leanSweeps < 1 && gotStance.verticalLegs >= 2)) {
      out.structureIssues.push({ kind: 'stance', want: wantStance || wantBack || 'raked', got: gotStance.stance || 'vertical' });
      out.penalty += 32;
      L.push('LIKENESS stance: inventory wants leaning members (legStance/backRake) but the model is plumb vertical sticks. Rebuild legs/posts as mesh sweeps whose path moves in Y (aft rake = +Y as Z rises) or X (splay) — do not use vertical solid boxes or axis:+z cylinders.');
    }
  }
  if (o.iou != null && isFinite(o.iou)) {
    out.iou = o.iou;
    /* Silhouette is the primary photo-likeness signal (north star). Aspect/counts remain secondary. */
    if (o.iou < 0.55) {
      out.penalty += Math.round((0.55 - o.iou) * 80);
      L.push('LIKENESS silhouette IoU ' + o.iou.toFixed(2) + ' is low — overall outline does not match the reference. Adjust proportions and major parts first.');
    } else if (o.iou < 0.7) {
      out.penalty += Math.round((0.7 - o.iou) * 25);
      L.push('LIKENESS silhouette IoU ' + o.iou.toFixed(2) + ' is fair — refine outline (legs, back, seat mass) toward the photo.');
    }
  }
  const met = o.metrics;
  if (met && M && M.size && (met.wMm > 0 || met.dMm > 0 || met.hMm > 0)) {
    const targets = [met.wMm, met.dMm, met.hMm];
    const labels = ['W', 'D', 'H'];
    let sumRel = 0, n = 0;
    const bits = [];
    for (let i = 0; i < 3; i++) {
      if (!(targets[i] > 0)) continue;
      const rel = Math.abs(M.size[i] - targets[i]) / targets[i];
      sumRel += rel; n++;
      if (rel > 0.02) bits.push(labels[i] + ' target ' + Math.round(targets[i]) + ' mm but model ' + Math.round(M.size[i]) + ' mm');
    }
    out.metricErr = n ? sumRel / n : 0;
    if (bits.length && out.metricErr > 0.02) {
      const pen = Math.min(45, Math.round(out.metricErr * 120));
      out.penalty += pen;
      L.push('METRIC size: ' + bits.join('; ') + '. Set params so overall AABB matches USER METRICS within ~2%.');
    }
  }
  if (o.unlabeledContacts && o.unlabeledContacts.length) {
    /* Penalty drives likeness retry; evaluate already lists the pairs in the critic text. */
    out.penalty += Math.min(40, o.unlabeledContacts.length * 12);
  }
  if (!L.length && inventory.object) L.push('LIKENESS: aspect/counts/structure look consistent with inventory ("' + inventory.object + '").');
  out.text = L.join('\n');
  return out;
};

/* ---------- the critic ---------- */
V.evaluate = function (spec, o) {
  o = o || {};
  const schema = CAD.validateSpec ? CAD.validateSpec(spec) : { ok: true, errors: [] };
  const M = CAD.buildSpec(spec, o.overrides);
  const r = { M, errors: M.errors.slice(), warnings: M.warnings.slice(), nonmanifold: [], interference: [], underfilled: [], fillChecked: 0, schemaErrors: schema.errors.slice() };
  if (schema.errors.length) {
    schema.errors.forEach(e => { if (r.errors.indexOf(e) < 0) r.errors.push(e); });
  }
  if (!M.errors.length) {
    r.nonmanifold = CAD.manifoldReport(M).filter(x => x.bad).map(x => x.id);
    const allHit = CAD.interference(M);
    r.interference = allHit.filter(x => !x.coarse || x.severe);
    r.coarseInterference = allHit.filter(x => x.coarse && !x.severe);
    const fl = CAD.jointFill(M); r.fillChecked = fl.length; r.underfilled = fl.filter(x => x.ratio < .999).map(x => ({ part: x.part, tag: x.tag, ratio: x.ratio, by: x.by }));
    r.unlabeledContacts = typeof CAD.unlabeledContacts === 'function' ? CAD.unlabeledContacts(M) : [];
    r.size = M.size.map(Math.round); r.parts = M.defs.size; r.pieces = M.insts.length;
  }
  r.ok = !r.errors.length && !r.nonmanifold.length && !r.interference.length && !r.underfilled.length;
  r.score = r.errors.length * 1000 + r.nonmanifold.length * 100 + r.interference.length * 50 + r.underfilled.length * 20 + r.warnings.length + (r.coarseInterference ? r.coarseInterference.length * 2 : 0);
  const L = []; if (r.errors.length) {
    L.push('ERRORS (fix first):');
    r.errors.slice(0, 20).forEach(e => {
      L.push(' - ' + e);
      if (/sweep fold/i.test(e)) L.push('   hint: increase path curvature radius or shrink section; fold guard rejects rho < 1.05× half-extent.');
      if (/bend radius below/i.test(e)) L.push('   hint: panel bend.radius must be ≥ 20×t (or reduce t).');
      if (/edgeR too large|triangle budget/i.test(e)) L.push('   hint: reduce edgeR / planR / tol, or simplify the path.');
    });
  }
  if (r.warnings.length) { L.push('WARNINGS:'); r.warnings.slice(0, 10).forEach(e => L.push(' - ' + e)); }
  if (r.nonmanifold.length) L.push('NON-WATERTIGHT parts (degenerate or self-overlapping geometry): ' + r.nonmanifold.join(', '));
  if (r.interference.length) {
    L.push('INTERFERENCE: these part pairs physically overlap (volume mm³). Move/resize one, or make the overlap a proper joint (a "cut" void in one part exactly filled by an "add" tenon/tongue in the other). Coarse entries are severe AABB overlaps involving a mesh part:');
    r.interference.slice(0, 15).forEach(x => L.push(' - ' + x.a + ' × ' + x.b + ': ' + Math.round(x.vol) + (x.coarse ? ' (coarse AABB, severe)' : '')));
  }
  if (r.coarseInterference && r.coarseInterference.length) {
    L.push('COARSE MESH OVERLAP (review; often intentional assembly contact such as a stretcher through a ring):');
    r.coarseInterference.slice(0, 10).forEach(x => L.push(' - ' + x.a + ' × ' + x.b + ': ~' + Math.round(x.vol) + ' mm³ AABB'));
  }
  if (r.underfilled.length) { L.push('UNFILLED JOINTS: these "fill":true cuts are not completely occupied by a mating part (ratio filled). Add/resize the mating tenon/tongue, or drop "fill" if the void is deliberate:'); r.underfilled.slice(0, 15).forEach(x => L.push(' - ' + x.part + ' / ' + x.tag + ': ' + Math.round(x.ratio * 100) + '%')); }
  if (r.unlabeledContacts && r.unlabeledContacts.length) {
    L.push('UNLABELED CONTACTS: these exact parts nearly touch without tagged/labeled joinery — add fill:true cuts and mating tenons (tag+label), or merge continuous members into one part:');
    r.unlabeledContacts.slice(0, 15).forEach(x => L.push(' - ' + x.a + ' ↔ ' + x.b));
  }
  if (r.size) L.push('Overall size: ' + r.size.join(' × ') + ' mm; ' + r.parts + ' part types, ' + r.pieces + ' pieces.');
  if ((o.inventory || o.metrics || (r.unlabeledContacts && r.unlabeledContacts.length)) && !M.errors.length) {
    r.likeness = V.likeness(M, o.inventory || {}, { iou: o.iou, metrics: o.metrics, unlabeledContacts: r.unlabeledContacts, spec: spec });
    r.score += r.likeness.penalty;
    if (r.likeness.text) L.push(r.likeness.text);
  }
  if (r.ok) L.push('All geometry checks passed.');
  r.text = L.join('\n'); return r;
};

/* ---------- providers: async ({text, images:[{mediaType,base64}], model, apiKey, signal}) → string ---------- */
const blocks = (text, images) => images.map(i => ({ type: 'image', source: { type: 'base64', media_type: i.mediaType, data: i.base64 } })).concat([{ type: 'text', text }]);
V.readAnthropicSSE = async function (res) {
  if (!res.body || typeof res.body.getReader !== 'function') {
    const j = await res.json().catch(() => ({}));
    return (j.content || []).filter(c => c.type === 'text').map(c => c.text).join('');
  }
  const reader = res.body.getReader(), dec = new TextDecoder();
  let buf = '', text = '', errMsg = null;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split('\n'); buf = lines.pop() || '';
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (!line.startsWith('data:')) continue;
      const raw = line.slice(5).trim();
      if (!raw || raw === '[DONE]') continue;
      let j; try { j = JSON.parse(raw); } catch (e) { continue; }
      if (j.type === 'content_block_delta' && j.delta && j.delta.type === 'text_delta' && j.delta.text) text += j.delta.text;
      if (j.type === 'error') errMsg = (j.error && j.error.message) || 'stream error';
    }
  }
  if (errMsg) throw new Error(errMsg);
  return text;
};
/** Max output tokens we ask Anthropic for (proxy also caps). Sonnet 4.5/5.5 support large outputs — do not starve staged chair SPECs. */
V.MAX_OUTPUT_TOKENS = 64000;
V.tokenBudget = function (task) {
  if (task === 'inventory') return 4000;
  if (task === 'revise') return 24000;
  if (task === 'carcass') return 32000;
  if (task === 'interiors') return 48000;
  if (task === 'refine') return 32000;
  if (task === 'design') return 32000;
  return 24000;
};
/** Prompt fragment: keep JSON completable within the token budget. */
V.COMPACT_JSON_RULES =
  'OUTPUT COMPACTNESS (required): Return ONE complete JSON object that fits in the reply. Keep "reasoning" to 2–4 short sentences. Prefer short part ids (leg_fl, rail_f). Omit verbose notes/steps arrays unless essential. Prefer param expressions over duplicating large number lists. Do not paste the inventory or SPEC_DOC back into the JSON. Never leave the JSON unfinished.';

/**
 * Unified photo-chair score (same rubric for lab + app).
 * rating: Match | Close | Close+ | Wrong
 * topology_ok: part set / construction is basically right
 * iou: silhouette overlap in [0,1] (optional until a render exists)
 */
V.scorePhotoChair = function (o) {
  o = o || {};
  const topology_ok = !!o.topology_ok;
  const iou = (o.iou != null && isFinite(o.iou)) ? +o.iou : null;
  let rating = 'Wrong';
  if (topology_ok && iou != null) {
    if (iou >= 0.7) rating = 'Match';
    else if (iou >= 0.55) rating = 'Close+';
    else if (iou >= 0.4) rating = 'Close';
    else rating = 'Wrong';
  } else if (topology_ok && iou == null) {
    rating = o.ratingHint || 'Close'; /* eyeball until IoU is measured */
  } else if (!topology_ok) {
    rating = 'Wrong';
  }
  return {
    rating,
    topology_ok,
    iou,
    missing_block: o.missing_block || null,
    notes: o.notes || '',
    method: 'silhouette-iou-v1'
  };
};

/**
 * Phase 7 (practical): coordinate-descent on numeric params to reduce aspect likeness error.
 * Uses inventory aspect only (no render). Returns best overrides + trail.
 */
V.fitParams = function (spec, inventory, o) {
  o = o || {};
  const maxIters = o.maxIters || 40;
  const M0 = CAD.buildSpec(spec);
  if (!M0.paramDefs.length || !inventory || !inventory.aspect) return { overrides: {}, penalty: 0, iters: 0 };
  const keys = M0.paramDefs.map(p => p.key);
  const cur = {}; M0.paramDefs.forEach(p => { cur[p.key] = p.value; });
  let best = Object.assign({}, cur);
  let bestPen = (V.likeness(M0, inventory).penalty) || 0;
  const trail = [{ overrides: Object.assign({}, best), penalty: bestPen }];
  for (let it = 0; it < maxIters; it++) {
    let improved = false;
    for (let ki = 0; ki < keys.length; ki++) {
      const def = M0.paramDefs[ki];
      const step = def.step || 1;
      for (const dir of [-1, 1]) {
        const trial = Object.assign({}, best);
        trial[def.key] = Math.max(def.min, Math.min(def.max, best[def.key] + dir * step));
        if (trial[def.key] === best[def.key]) continue;
        const M = CAD.buildSpec(spec, trial);
        if (M.errors.length) continue;
        const pen = V.likeness(M, inventory).penalty;
        if (pen + 1e-6 < bestPen) { bestPen = pen; best = trial; improved = true; trail.push({ overrides: Object.assign({}, best), penalty: bestPen }); }
      }
    }
    if (!improved) break;
  }
  return { overrides: best, penalty: bestPen, iters: trail.length - 1, trail };
};
V.providers = {
  anthropic: async o => {
    const maxTok = Math.min(+o.max_tokens || V.tokenBudget(o.task), V.MAX_OUTPUT_TOKENS);
    const stream = o.stream !== false;
    const headers = { 'content-type': 'application/json', 'x-api-key': o.apiKey, 'anthropic-version': '2023-06-01', 'anthropic-dangerous-direct-browser-access': 'true' };
    if (o.runId) headers['x-run-id'] = String(o.runId);
    const r = await fetch((o.baseUrl || 'https://api.anthropic.com') + '/v1/messages', { method: 'POST', signal: o.signal, headers,
      body: JSON.stringify({ model: o.model || 'claude-sonnet-5-5', max_tokens: maxTok, stream, messages: [{ role: 'user', content: blocks(o.text, o.images) }] }) });
    if (!r.ok) { const j = await r.json().catch(() => ({})); throw new Error('Anthropic API ' + r.status + ': ' + ((j.error && j.error.message) || r.statusText)); }
    const ct = (r.headers.get('content-type') || '');
    if (stream && /event-stream/i.test(ct)) return V.readAnthropicSSE(r);
    const j = await r.json().catch(() => ({})); return (j.content || []).filter(c => c.type === 'text').map(c => c.text).join('');
  },
  proxy: async o => {
    const maxTok = Math.min(+o.max_tokens || V.tokenBudget(o.task), V.MAX_OUTPUT_TOKENS);
    const stream = o.stream !== false;
    const headers = { 'content-type': 'application/json' };
    if (o.runId) headers['x-run-id'] = String(o.runId);
    if (o.task) headers['x-task'] = String(o.task);
    if (o.quality) headers['x-quality'] = String(o.quality);
    if (o.domain) headers['x-domain'] = String(o.domain);
    const body = { model: o.model || 'claude-sonnet-5-5', max_tokens: maxTok, stream, messages: [{ role: 'user', content: blocks(o.text, o.images) }] };
    if (o.runId) body.runId = String(o.runId);
    body.metadata = {
      runId: o.runId || null,
      task: o.task || null,
      quality: o.quality || null,
      domain: o.domain || 'furniture'
    };
    const r = await fetch(o.proxyUrl || '/api/messages', { method: 'POST', signal: o.signal, headers, body: JSON.stringify(body) });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      const msg = (j.error && (j.error.message || j.error)) || r.statusText;
      if (r.status === 504 || r.status === 524) throw new Error('Proxy timed out (504). Vercel caps long model calls (~5 min on Hobby). Your API key on the server is fine — try Haiku, max rounds 1, turn off visual critic, or upgrade the Vercel plan for longer runs. ' + msg);
      throw new Error('Proxy ' + r.status + ': ' + msg);
    }
    const ct = (r.headers.get('content-type') || '');
    if (stream && /event-stream|text\/plain/i.test(ct)) return V.readAnthropicSSE(r);
    const j = await r.json().catch(() => ({}));
    return (j.content || []).filter(c => c.type === 'text').map(c => c.text).join('');
  },
  artifact: async o => { const c = root.claude; if (!c || !c.use) throw new Error('not running inside Claude'); const sample = await c.use('sample'); if (!sample) throw new Error('Claude sampling is not available here');
    const blobs = o.images.map(i => { const bin = atob(i.base64), u = new Uint8Array(bin.length); for (let k = 0; k < bin.length; k++) u[k] = bin.charCodeAt(k); return new Blob([u], { type: i.mediaType }); });
    const res = await sample(o.text, { images: blobs, modelTier: 'complex', signal: o.signal, cache: false }); return res.text; },
  mock: async o => { const p = o.mock; p.calls = p.calls || []; p.calls.push({ text: o.text, images: o.images.length, task: o.task }); const r = p.responses[Math.min(p.calls.length - 1, p.responses.length - 1)]; return typeof r === 'function' ? r(o) : r; },
};

V.summarizeInventory = function (inv) {
  if (!inv || typeof inv !== 'object') return '';
  const bits = [];
  if (inv.object) bits.push(inv.object);
  if (inv.aspect) bits.push('aspect ' + [inv.aspect.w, inv.aspect.d, inv.aspect.h].map(x => (+x || 0).toFixed(2)).join(':'));
  const c = inv.counts || {};
  ['legs', 'drawers', 'doors', 'shelves', 'slats'].forEach(k => { if (c[k]) bits.push(c[k] + ' ' + k); });
  const st = inv.structure || {};
  if (st.memberContinuity && st.memberContinuity !== 'unknown') bits.push(st.memberContinuity + ' members');
  if (st.dominantSection && st.dominantSection !== 'unknown') bits.push(st.dominantSection + ' section');
  if (st.legStance && st.legStance !== 'unknown') bits.push(st.legStance + ' stance');
  if (st.backRake && st.backRake !== 'unknown' && st.backRake !== 'none') bits.push('back rake ' + st.backRake);
  return bits.join(' · ');
};

/* ---------- the loop ---------- */
V.run = async function (o) {
  const log = o.onLog || (() => {}), max = o.maxRounds || 3, call = V.providers[o.provider.kind]; if (!call) throw new Error('unknown provider ' + o.provider.kind);
  if (o.task === 'revise' && !o.prevSpec) throw new Error('no current design to revise');
  const refs = o.image ? [typeof o.image === 'string' ? V.dataUrlToImage(o.image) : o.image] : [];
  const inputMode = o.inputMode === 'drawing' ? 'drawing' : 'photo';
  const metrics = o.metrics || V.parseDims(o.hints, o.dimFields);
  const hintText = V.composeHints(o.hints, metrics);
  let pastExampleText = o.pastExampleText || (o.pastExamples && CAD.store && CAD.store.formatExamplesForPrompt
    ? CAD.store.formatExamplesForPrompt(o.pastExamples) : '') || '';
  const callModel = (extra) => call(Object.assign({}, o.provider, {
    signal: o.signal, runId: o.runId, quality: o.quality, domain: o.domain || 'furniture'
  }, extra));
  const promptExtras = () => ({ hints: hintText, metrics, inputMode, inventory, pastExampleText: pastExampleText || undefined });
  const critOpts = () => ({ inventory, metrics: (metrics.wMm || metrics.dMm || metrics.hMm) ? metrics : null });
  let best = null, prev = o.task === 'revise' ? o.prevSpec : null, report = null, mode = 'fix', visualDone = false, likenessRetryDone = false, lastOk = null;
  let inventory = o.inventory || null, roundCounter = 0, lastIou = null;

  if (metrics.wMm || metrics.dMm || metrics.hMm) log('Metrics: ' + V.formatMetrics(metrics));
  if (inputMode === 'drawing') log('Input mode: drawing + dimensions');
  if (pastExampleText) log('Using ' + (o.pastExamples ? o.pastExamples.length : 1) + ' past success example(s) as few-shot guidance');
  const wantSilhouette = o.silhouette !== false && typeof o.silhouetteIoU === 'function' && typeof o.render === 'function' && refs.length > 0;
  if (o.visual) log('Photo match (visual critic): on');
  else log('Photo match (visual critic): off — enable in Quality or check the box for LLM visual critique');
  if (wantSilhouette) log('Silhouette score: on (outline IoU vs reference after a successful build)');
  else if (refs.length && inputMode === 'photo') log('Silhouette score: off (need render + silhouetteIoU)');

  const noteCritic = (rep) => {
    const likeNote = rep.likeness && rep.likeness.penalty ? ', likeness −' + rep.likeness.penalty : '';
    log('Critic: ' + (rep.ok ? 'all geometry checks passed' : rep.errors.length + ' errors, ' + rep.interference.length + ' interferences, ' + rep.underfilled.length + ' unfilled joints') + (rep.size ? ' · ' + rep.size.join('×') + ' mm' : '') + likeNote);
  };
  const adopt = (spec, rep) => {
    roundCounter++;
    if (spec.reasoning) { log('Thought process:'); String(spec.reasoning).split(/\n+/).forEach(line => { if (line.trim()) log(line.trim()); }); }
    noteCritic(rep);
    if (o.onSpec) o.onSpec(spec, rep, roundCounter);
    if (!best || rep.score < best.rep.score) best = { spec, rep, round: roundCounter };
    if (rep.ok) lastOk = { spec, rep, round: roundCounter };
  };

  if (o.task !== 'revise' && refs.length && !inventory) {
    log(inputMode === 'drawing' ? 'Inventory pass: reading the drawing…' : 'Inventory pass: reading the picture…');
    try {
      const rawInv = await callModel({ text: V.buildInventoryPrompt({ hints: hintText, metrics, inputMode, pastExampleText }), images: refs.slice(), task: 'inventory', max_tokens: V.tokenBudget('inventory') });
      inventory = V.extractJSON(rawInv);
      if (metrics.wMm || metrics.dMm || metrics.hMm) {
        inventory.overallGuessMm = inventory.overallGuessMm || {};
        if (metrics.wMm) inventory.overallGuessMm.w = Math.round(metrics.wMm);
        if (metrics.dMm) inventory.overallGuessMm.d = Math.round(metrics.dMm);
        if (metrics.hMm) inventory.overallGuessMm.h = Math.round(metrics.hMm);
        if (!inventory.aspect && metrics.wMm && metrics.dMm && metrics.hMm) {
          inventory.aspect = V.normalizeAspect(metrics.wMm, metrics.dMm, metrics.hMm);
        }
      }
      const sum = V.summarizeInventory(inventory);
      log(sum ? 'Inventory: ' + sum : 'Inventory captured');
      if (o.onInventory) o.onInventory(inventory);
      /* After inventory, inject the best seating few-shot (Lakin if continuous, else dining-chair). */
      if (CAD.store && CAD.store.looksLikeSeating && CAD.store.looksLikeSeating(inventory.object || '')) {
        let shot = o.chairFewShot;
        try {
          const kind = CAD.store.pickChairFewShotKind ? CAD.store.pickChairFewShotKind(inventory, hintText) : 'dining';
          const ex = (typeof window !== 'undefined' && window.EXAMPLES) || {};
          const src = (kind === 'lakin' && ex['lakin-chair']) || ex['dining-chair'] || ex['lakin-chair'];
          if (src && CAD.store.chairFewShotFromExample) {
            shot = CAD.store.chairFewShotFromExample(src, (kind === 'lakin' && ex['lakin-chair']) ? 'lakin' : 'dining');
          }
          if (shot) {
            const chairText = CAD.store.formatExamplesForPrompt([shot]);
            if (chairText) {
              pastExampleText = chairText + (pastExampleText ? '\n\n' + pastExampleText : '');
              log('Few-shot: ' + (kind === 'lakin' ? 'lakin continuous side-frame' : 'dining-chair') + ' patterns (sweep / panel / pillow)');
            }
          }
        } catch (e) { /* optional */ }
      }
    } catch (e) {
      log('Inventory pass skipped: ' + e.message);
      inventory = null;
    }
  }

  const wantStages = o.task !== 'revise' && (o.staged === true || (o.staged !== false && V.needsStages(inventory)));
  if (wantStages) {
    log('Staged design: carcass → interiors → refine');
    for (let si = 0; si < V.STAGES.length; si++) {
      const stage = V.STAGES[si];
      let stageReport = null, stagePrev = prev;
      for (let attempt = 1; attempt <= 2; attempt++) {
        log('Stage ' + stage.label + ' (' + (si + 1) + '/' + V.STAGES.length + ')' + (attempt > 1 ? ' · fix' : '') + '…');
        const text = V.buildPrompt(Object.assign({ stage, prevSpec: stagePrev, report: stageReport }, promptExtras(), { inventory }));
        let raw; try { raw = await callModel({ text, images: refs.slice(), task: stage.id, max_tokens: V.tokenBudget(stage.id) }); } catch (e) { log('Model call failed: ' + e.message); throw e; }
        let spec; try { spec = V.extractJSON(raw); } catch (e) {
          log('Could not read JSON: ' + e.message);
          const trunc = /truncat/i.test(e.message);
          stageReport = {
            text: 'Your last reply could not be parsed: ' + e.message + '. Return one complete, valid JSON object.' +
              (trunc
                ? ' CRITICAL: prior reply was truncated — shorten reasoning to 2 sentences, use short ids, omit notes/steps, keep only essential parts for this stage, and finish the closing braces.'
                : '')
          };
          continue;
        }
        if (stagePrev) spec = V.mergeSpecs(stagePrev, spec);
        const rep = V.evaluate(spec, critOpts());
        adopt(spec, rep);
        stagePrev = spec; prev = spec;
        if (rep.ok) break;
        stageReport = rep;
      }
    }
  }

  for (let round = 1; round <= max; round++) {
    if (wantStages && round === 1 && prev && !report) {
      const seed = V.evaluate(prev, critOpts());
      if (seed.ok && !(o.visual && !visualDone) && !(seed.likeness && seed.likeness.penalty >= 20)) {
        if (!best) adopt(prev, seed);
        break;
      }
      if (!seed.ok || (seed.likeness && seed.likeness.penalty >= 20)) { report = seed; mode = 'fix'; }
    }
    const first = o.task === 'revise' ? 'asking the model to apply your changes…' : (wantStages ? 'final critic pass…' : (inputMode === 'drawing' ? 'asking the model to design from the drawing…' : 'asking the model to design from the picture…'));
    log('Round ' + round + '/' + max + ': ' + (round === 1 && !wantStages ? first : mode === 'visual' ? 'visual critique against the reference…' : wantStages && round === 1 ? first : 'sending critic findings back to the model…'));
    const images = refs.slice(); if (mode === 'visual' && o.render) { const png = await o.render(prev); if (png) images.push(typeof png === 'string' ? V.dataUrlToImage(png) : png); }
    const text = V.buildPrompt(Object.assign({ round: wantStages ? round + 1 : round, prevSpec: prev, report, mode, task: o.task, focusParts: o.focusParts, focusJoint: o.focusJoint }, promptExtras(), { inventory }));
    let raw; try { raw = await callModel({ text, images, task: o.task === 'revise' ? 'revise' : 'design', max_tokens: V.tokenBudget(o.task === 'revise' ? 'revise' : 'design') }); } catch (e) { log('Model call failed: ' + e.message); throw e; }
    let spec; try { spec = V.extractJSON(raw); } catch (e) {
      log('Could not read JSON: ' + e.message);
      const trunc = /truncat/i.test(e.message);
      report = {
        text: 'Your last reply could not be parsed: ' + e.message + '. Return one complete, valid JSON object with a short "reasoning" field.' +
          (trunc ? ' CRITICAL: prior reply was truncated — emit compact JSON and finish every brace.' : '')
      };
      mode = 'fix'; continue;
    }
    if (prev && wantStages) spec = V.mergeSpecs(prev, spec);
    let iou = null;
    if (mode === 'visual' && typeof o.silhouetteIoU === 'function' && images.length >= 2) {
      try { iou = await o.silhouetteIoU(images[0], images[1]); lastIou = iou; if (iou != null) log('Silhouette IoU: ' + iou.toFixed(2)); } catch (e) { log('Silhouette score skipped: ' + e.message); }
    }
    let rep = V.evaluate(spec, Object.assign(critOpts(), { iou }));
    /* North star: after geometry passes, always score silhouette vs the photo when we can render — even if LLM visual critic is off. */
    if (rep.ok && wantSilhouette && lastIou == null) {
      try {
        log('Silhouette score: rendering model for outline comparison…');
        const png = await o.render(spec);
        if (png) {
          const modelImg = typeof png === 'string' ? V.dataUrlToImage(png) : png;
          iou = await o.silhouetteIoU(refs[0], modelImg);
          lastIou = iou;
          if (iou != null) log('Silhouette IoU: ' + iou.toFixed(2));
          rep = V.evaluate(spec, Object.assign(critOpts(), { iou }));
        }
      } catch (e) { log('Silhouette score skipped: ' + e.message); }
    }
    adopt(spec, rep);
    if (rep.ok && !likenessRetryDone && rep.likeness && rep.likeness.penalty >= 20 && round < max) {
      likenessRetryDone = true; mode = 'fix'; prev = spec; report = rep; continue;
    }
    if (rep.ok && o.visual && !visualDone && round < max && o.render) {
      visualDone = true; mode = 'visual'; prev = spec; report = rep;
      log('Photo match: LLM visual critique against the reference…');
      continue;
    }
    if (rep.ok && o.visual && !visualDone && !(round < max && o.render)) {
      log('Photo match: could not run LLM visual — ' + (!o.render ? 'no renderer available' : 'no rounds left; raise Quality to Careful'));
    }
    if (rep.ok) break; prev = spec; report = rep; mode = 'fix';
  }
  if (!best) throw new Error('The model never returned a usable spec. See the log.');
  const final = lastOk || best;
  /* If we exited early (e.g. staged seed OK), still measure silhouette once. */
  if (wantSilhouette && lastIou == null && final.spec) {
    try {
      log('Silhouette score: rendering final model…');
      const png = await o.render(final.spec);
      if (png) {
        const modelImg = typeof png === 'string' ? V.dataUrlToImage(png) : png;
        lastIou = await o.silhouetteIoU(refs[0], modelImg);
        if (lastIou != null) {
          log('Silhouette IoU: ' + lastIou.toFixed(2));
          final.rep = V.evaluate(final.spec, Object.assign(critOpts(), { iou: lastIou }));
        }
      }
    } catch (e) { log('Silhouette score skipped: ' + e.message); }
  }
  final.inventory = inventory;
  final.metrics = metrics;
  final.staged = !!wantStages;
  final.visualCritic = {
    requested: !!o.visual,
    ran: !!visualDone,
    iou: lastIou,
    silhouette: wantSilhouette,
    skippedReason: o.visual ? (visualDone ? null : (!o.render ? 'no-renderer' : 'not-enough-rounds-or-geometry-failed')) : 'off'
  };
  final.photoScore = V.scorePhotoChair({
    topology_ok: !!(final.rep && final.rep.ok),
    iou: lastIou,
    notes: final.rep && final.rep.ok ? 'geometry checks passed' : 'geometry still failing'
  });
  if (lastIou != null) log('Silhouette score: ' + lastIou.toFixed(2) + ' → ' + final.photoScore.rating);
  else if (wantSilhouette) log('Silhouette score: no IoU measured');
  if (final.visualCritic.requested && final.visualCritic.ran) log('LLM visual critic: finished');
  else if (!final.visualCritic.requested) log('LLM visual critic: off');
  log(final.rep.ok ? 'Done: design passes every check (round ' + final.round + ').' : 'Stopped after ' + max + ' rounds: best design still has issues. You can fix it in the Spec tab.');
  return final;
};
})(typeof globalThis !== 'undefined' ? globalThis : window);
