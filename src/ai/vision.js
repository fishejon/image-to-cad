/* vision.js — picture → design spec, with the Gauntlet loop built in:
   builder (the model writes a spec) ⇄ critic (exact geometry checks, optional visual comparison) until the critic is satisfied. */
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
# DESIGN SPEC (JSON) — numeric geometry is millimetres (the engine's unit). Z is up, X is the long side, the FRONT faces -Y, origin is the centre of the footprint on the floor. User-facing text (name, description, spec, notes, labels, param labels) MUST use inches to the nearest 1/16, written as fractions under 1" (3/4\" not 0.75\") and mixed numbers above (12 3/16\"). Convert: 1 inch = 25.4 mm.
Top-level keys: name, description, assumptions[], params{}, materials{}, groups[], steps[], kinematics{}, parts[] (required).
Every NUMBER may be an arithmetic expression string using params, part "vars", and the repeat variable. Operators + - * / % ^ ( ) comparisons < > <= >= == != ; functions min max abs round floor ceil sqrt pow mod sin cos tan atan2 clamp if(c,a,b). Angles are in degrees.
params: { "W": {"value":900,"min":600,"max":1400,"step":50,"label":"Width"}, "t": {"expr":"18"}, "Wi": {"expr":"W-2*t"} }  (objects with "value" become UI sliders; "expr" are derived values; params are evaluated in order, so define a name before using it).
materials: { "oak": {"base":"oak"}, "paint": {"color":"#d9d9d4","metal":0,"rough":0.5,"rho":700} }. Built-in ids: wood(walnut) oak pine ply marble steel aluminium brass plastic glass rubber fabric concrete paint.
groups: [{"id":"carcass","name":"Carcass","color":"#6aa6ff"}]. steps: ["Glue the sides", {"title":"...","notes":["..."],"tools":["..."],"tip":"...","check":"..."}] — index = the "step" number of the parts placed in that step.
kinematics: { "drawer": {"label":"Drawer","axis":[0,-1,0],"range":[0,300],"unit":"mm"} }  or rotation: {"unit":"deg","axis":[0,0,1],"pivot":[x,y,z],"range":[0,110]}. Instances with "kin":"drawer" move with it.
parts[]: each part is ONE physical piece type: { "id","name","group","material","kind":"solid"|"mesh","grain":"x"|"y"|"z","spec":"size text","notes":[...],"tools":[...], "vars":{...}, "instances":[...] }.
  kind "solid" (default; rectilinear parts, EXACT boolean geometry): "ops":[ {"add":[x0,y0,z0,x1,y1,z1]}, {"cut":[x0,y0,z0,x1,y1,z1],"tag":"mortise","label":"Mortise 24 × 8 × 40","fill":true} ]. Boxes are axis-aligned in the part's LOCAL frame. All "add" boxes are united, then all "cut" boxes removed. "fill":true means a mating part MUST completely occupy that void (mortise, dado, groove, rabbet). "tag"+"label" document a joint so the build guide can show it. Leave "fill" off for deliberate voids (finger pulls, door tracks).
  kind "mesh" (round / turned / non-rectilinear parts): "prims":[ {"type":"box","min":[..],"max":[..]}, {"type":"cylinder","base":[x,y,z],"axis":"+z","length":L,"r":R,"seg":32}, {"type":"cone","base","axis","length","r0","r1"}, {"type":"tube","base","axis","length","ro","ri"}, {"type":"sphere","r":R,"center":[..]}, {"type":"revolve","at":[x,y,z],"axis":"+z","profile":[[radius,height],...],"seg":48}, {"type":"extrude","plane":"xy"|"xz"|"yz","profile":[[u,v],...],"range":[w0,w1],"holes":[{"c":[u,v],"r":R}]} ]. One material per part.
  instances: [{"pos":[x,y,z],"rot":[rx,ry,rz],"step":0,"explode":[dx,dy,dz],"kin":"name","repeat":{"var":"i","count":4}}]. Placement = translate(pos) · Rz · Ry · Rx. Solid parts should be rotated only by multiples of 90°. "repeat" also works on ops and prims. Omit "explode" to get an automatic exploded view.
Modelling rules: (1) Parts must NOT overlap each other except where a tenon/tongue fills a "fill":true void exactly. (2) Joint voids and the tenon that fills them must have identical dimensions. (3) Model the object as separate real-world parts joined the way the real object is built (mortise & tenon, dados, rabbets, box joints, bolted flanges...). (4) Use params for the main dimensions so the user can resize. (5) Prefer "solid" parts; use "mesh" only for round/turned/sloped shapes. (6) Put the object on the floor (min z = 0). (7) Give each part a short real-world "spec" and, when there is a joint to cut, "notes" saying how.
`;
V.EXAMPLE_JSON = JSON.stringify(V.EXAMPLE);

V.buildPrompt = function (o) {
  o = o || {}; const parts = [];
  if (o.task === 'revise' && o.prevSpec && (o.round === 1 || !o.report)) {
    parts.push('You are revising an existing CAD design spec. Apply the user\'s requested changes and return the COMPLETE updated spec as ONE JSON object (no commentary, no markdown fences). Keep everything that is not mentioned. Preserve joinery: if you move or resize a part, update its mating mortises/tenons so they still fill.');
    parts.push(V.SPEC_DOC); parts.push('CURRENT SPEC:\n' + JSON.stringify(o.prevSpec));
    parts.push('REQUESTED CHANGES: ' + (o.hints || '(none)'));
  } else if (o.round === 1 || !o.prevSpec) {
    parts.push('You are an expert CAD engineer and furniture/product designer. Study the attached picture and write a design spec for a 3D model of the object in it, as ONE JSON object that follows the DESIGN SPEC below. Reproduce the real proportions, parts, joinery and details you can see (drawers, doors, slats, legs, stretchers, round parts...). Where something is hidden, choose the most plausible construction and list it in "assumptions". Return ONLY the JSON object: no commentary, no markdown fences.');
    parts.push(V.SPEC_DOC); parts.push('Minimal valid example:\n' + V.EXAMPLE_JSON);
    if (o.hints) parts.push('USER HINTS (they override anything you guess from the picture): ' + o.hints);
    if (o.report) parts.push('YOUR PREVIOUS REPLY WAS REJECTED:\n' + o.report.text);
  } else {
    parts.push('You are the BUILDER in a builder/critic loop. Below are your previous spec and the CRITIC report from an exact geometry checker' + (o.mode === 'visual' ? ' plus a render of your model next to the reference picture' : '') + '. Fix every issue and return the COMPLETE corrected spec as ONE JSON object (no commentary, no fences). Keep everything that was already correct.');
    parts.push(V.SPEC_DOC); if (o.hints) parts.push('USER HINTS: ' + o.hints);
    parts.push('PREVIOUS SPEC:\n' + JSON.stringify(o.prevSpec)); parts.push('CRITIC REPORT:\n' + (o.report ? o.report.text : ''));
    if (o.mode === 'visual') parts.push('VISUAL CRITIQUE: image 1 is the reference picture, image 2 is the render of your spec. Compare proportions (width : depth : height), number and size of parts (legs, drawers, shelves, slats), leg/foot shape and any visible details. If they differ materially, correct the spec. If it already matches, return the spec unchanged.');
  }
  return parts.join('\n\n');
};
V.extractJSON = function (text) {
  if (typeof text !== 'string') throw new Error('empty model response'); let s = text.replace(/```(?:json)?/gi, '').trim(); const a = s.indexOf('{'); if (a < 0) throw new Error('no JSON object found in the model response');
  let depth = 0, inStr = false, esc = false, end = -1; for (let i = a; i < s.length; i++) { const c = s[i]; if (inStr) { if (esc) esc = false; else if (c === '\\') esc = true; else if (c === '"') inStr = false; } else if (c === '"') inStr = true; else if (c === '{') depth++; else if (c === '}') { depth--; if (!depth) { end = i; break; } } }
  if (end < 0) throw new Error('JSON object is truncated (the model ran out of space). Ask for a smaller design.'); return JSON.parse(s.slice(a, end + 1));
};
V.dataUrlToImage = function (u) { const m = /^data:([^;]+);base64,(.*)$/.exec(u); if (!m) throw new Error('bad data URL'); return { mediaType: m[1], base64: m[2] }; };

/* ---------- the critic ---------- */
V.evaluate = function (spec, o) {
  o = o || {}; const M = CAD.buildSpec(spec, o.overrides), r = { M, errors: M.errors.slice(), warnings: M.warnings.slice(), nonmanifold: [], interference: [], underfilled: [], fillChecked: 0 };
  if (!M.errors.length) {
    r.nonmanifold = CAD.manifoldReport(M).filter(x => x.bad).map(x => x.id); r.interference = CAD.interference(M);
    const fl = CAD.jointFill(M); r.fillChecked = fl.length; r.underfilled = fl.filter(x => x.ratio < .999).map(x => ({ part: x.part, tag: x.tag, ratio: x.ratio, by: x.by }));
    r.size = M.size.map(Math.round); r.parts = M.defs.size; r.pieces = M.insts.length;
  }
  r.ok = !r.errors.length && !r.nonmanifold.length && !r.interference.length && !r.underfilled.length;
  r.score = r.errors.length * 1000 + r.nonmanifold.length * 100 + r.interference.length * 50 + r.underfilled.length * 20 + r.warnings.length;
  const L = []; if (r.errors.length) { L.push('ERRORS (fix first):'); r.errors.slice(0, 20).forEach(e => L.push(' - ' + e)); }
  if (r.warnings.length) { L.push('WARNINGS:'); r.warnings.slice(0, 10).forEach(e => L.push(' - ' + e)); }
  if (r.nonmanifold.length) L.push('NON-WATERTIGHT parts (degenerate or self-overlapping geometry): ' + r.nonmanifold.join(', '));
  if (r.interference.length) { L.push('INTERFERENCE: these part pairs physically overlap (volume mm³). Move/resize one, or make the overlap a proper joint (a "cut" void in one part exactly filled by an "add" tenon/tongue in the other):'); r.interference.slice(0, 15).forEach(x => L.push(' - ' + x.a + ' × ' + x.b + ': ' + Math.round(x.vol))); }
  if (r.underfilled.length) { L.push('UNFILLED JOINTS: these "fill":true cuts are not completely occupied by a mating part (ratio filled). Add/resize the mating tenon/tongue, or drop "fill" if the void is deliberate:'); r.underfilled.slice(0, 15).forEach(x => L.push(' - ' + x.part + ' / ' + x.tag + ': ' + Math.round(x.ratio * 100) + '%')); }
  if (r.size) L.push('Overall size: ' + r.size.join(' × ') + ' mm; ' + r.parts + ' part types, ' + r.pieces + ' pieces.'); if (r.ok) L.push('All geometry checks passed.');
  r.text = L.join('\n'); return r;
};

/* ---------- providers: async ({text, images:[{mediaType,base64}], model, apiKey, signal}) → string ---------- */
const blocks = (text, images) => images.map(i => ({ type: 'image', source: { type: 'base64', media_type: i.mediaType, data: i.base64 } })).concat([{ type: 'text', text }]);
V.providers = {
  anthropic: async o => { const r = await fetch((o.baseUrl || 'https://api.anthropic.com') + '/v1/messages', { method: 'POST', signal: o.signal, headers: { 'content-type': 'application/json', 'x-api-key': o.apiKey, 'anthropic-version': '2023-06-01', 'anthropic-dangerous-direct-browser-access': 'true' },
      body: JSON.stringify({ model: o.model || 'claude-sonnet-4-5', max_tokens: 24000, messages: [{ role: 'user', content: blocks(o.text, o.images) }] }) });
    const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error('Anthropic API ' + r.status + ': ' + ((j.error && j.error.message) || r.statusText)); return (j.content || []).filter(c => c.type === 'text').map(c => c.text).join(''); },
  proxy: async o => { const r = await fetch(o.proxyUrl || '/api/messages', { method: 'POST', signal: o.signal, headers: { 'content-type': 'application/json' }, body: JSON.stringify({ model: o.model || 'claude-sonnet-4-5', max_tokens: 24000, messages: [{ role: 'user', content: blocks(o.text, o.images) }] }) });
    const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error('Proxy ' + r.status + ': ' + ((j.error && (j.error.message || j.error)) || r.statusText)); return (j.content || []).filter(c => c.type === 'text').map(c => c.text).join(''); },
  artifact: async o => { const c = root.claude; if (!c || !c.use) throw new Error('not running inside Claude'); const sample = await c.use('sample'); if (!sample) throw new Error('Claude sampling is not available here');
    const blobs = o.images.map(i => { const bin = atob(i.base64), u = new Uint8Array(bin.length); for (let k = 0; k < bin.length; k++) u[k] = bin.charCodeAt(k); return new Blob([u], { type: i.mediaType }); });
    const res = await sample(o.text, { images: blobs, modelTier: 'complex', signal: o.signal, cache: false }); return res.text; },
  mock: async o => { const p = o.mock; p.calls = p.calls || []; p.calls.push({ text: o.text, images: o.images.length }); const r = p.responses[Math.min(p.calls.length - 1, p.responses.length - 1)]; return typeof r === 'function' ? r(o) : r; },
};

/* ---------- the loop ---------- */
V.run = async function (o) {
  const log = o.onLog || (() => {}), max = o.maxRounds || 3, call = V.providers[o.provider.kind]; if (!call) throw new Error('unknown provider ' + o.provider.kind);
  if (o.task === 'revise' && !o.prevSpec) throw new Error('no current design to revise');
  const refs = o.image ? [typeof o.image === 'string' ? V.dataUrlToImage(o.image) : o.image] : []; let best = null, prev = o.task === 'revise' ? o.prevSpec : null, report = null, mode = 'fix', visualDone = false, lastOk = null;
  for (let round = 1; round <= max; round++) {
    const first = o.task === 'revise' ? 'asking the model to apply your changes…' : 'asking the model to design from the picture…';
    log('Round ' + round + '/' + max + ': ' + (round === 1 ? first : mode === 'visual' ? 'visual critique against the reference…' : 'sending critic findings back to the model…'));
    const images = refs.slice(); if (mode === 'visual' && o.render) { const png = await o.render(prev); if (png) images.push(typeof png === 'string' ? V.dataUrlToImage(png) : png); }
    const text = V.buildPrompt({ round, prevSpec: prev, report, hints: o.hints, mode, task: o.task });
    let raw; try { raw = await call(Object.assign({}, o.provider, { text, images, signal: o.signal })); } catch (e) { log('Model call failed: ' + e.message); throw e; }
    let spec; try { spec = V.extractJSON(raw); } catch (e) { log('Could not read JSON: ' + e.message); report = { text: 'Your last reply could not be parsed: ' + e.message + '. Return one complete, valid JSON object.' }; mode = 'fix'; continue; }
    const rep = V.evaluate(spec); log('Critic: ' + (rep.ok ? 'all geometry checks passed' : rep.errors.length + ' errors, ' + rep.interference.length + ' interferences, ' + rep.underfilled.length + ' unfilled joints') + (rep.size ? ' · ' + rep.size.join('×') + ' mm' : ''));
    if (o.onSpec) o.onSpec(spec, rep, round); if (!best || rep.score < best.rep.score) best = { spec, rep, round }; if (rep.ok) lastOk = { spec, rep, round };
    if (rep.ok && o.visual && !visualDone && round < max && o.render) { visualDone = true; mode = 'visual'; prev = spec; report = rep; continue; }
    if (rep.ok) break; prev = spec; report = rep; mode = 'fix';
  }
  if (!best) throw new Error('The model never returned a usable spec. See the log.'); const final = lastOk || best; log(final.rep.ok ? 'Done: design passes every check (round ' + final.round + ').' : 'Stopped after ' + max + ' rounds: best design still has issues. You can fix it in the Spec tab.'); return final;
};
})(typeof globalThis !== 'undefined' ? globalThis : window);
