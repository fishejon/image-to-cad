/* spec.js — JSON design spec → parametric model. See docs/SPEC.md.
   Exposes CAD.buildSpec(spec, overrides) → SpecModel { defs, insts, P, paramDefs, kinematics, groups, steps, errors, warnings }. */
(function (root) {
'use strict';
const CAD = root.CAD, T = root.THREE, Solid = CAD.Solid, D2R = Math.PI / 180;
Solid.prototype.exact = true; Solid.prototype.splittable = true;

/* ---------- safe arithmetic expressions (no eval) ---------- */
const FUN = { min: Math.min, max: Math.max, abs: Math.abs, round: Math.round, floor: Math.floor, ceil: Math.ceil, sqrt: Math.sqrt, pow: Math.pow, mod: (a, b) => a % b,
  sin: a => Math.sin(a * D2R), cos: a => Math.cos(a * D2R), tan: a => Math.tan(a * D2R), atan2: (a, b) => Math.atan2(a, b) / D2R, clamp: (x, a, b) => Math.min(b, Math.max(a, x)), if: (c, a, b) => (c ? a : b) };
function tokenize(s) {
  const t = [], re = /\s*(?:(\d+\.?\d*(?:e[+-]?\d+)?|\.\d+)|([A-Za-z_][A-Za-z0-9_]*)|(<=|>=|==|!=|[-+*/%^(),<>]))/y; let last = 0;
  while (last < s.length) { re.lastIndex = last; const m = re.exec(s); if (!m) { if (/^\s*$/.test(s.slice(last))) break; throw new Error('bad character at ' + last + ' in "' + s + '"'); } last = re.lastIndex; if (m[1] !== undefined) t.push({ n: parseFloat(m[1]) }); else if (m[2] !== undefined) t.push({ id: m[2] }); else t.push({ op: m[3] }); }
  return t;
}
function parse(src) {
  const toks = tokenize(src); let p = 0; const isOp = o => toks[p] && toks[p].op === o, next = () => toks[p++];
  function cmp() { let a = add(); while (toks[p] && ['<', '>', '<=', '>=', '==', '!='].includes(toks[p].op)) { const o = next().op, b = add(), l = a; a = s => { const x = l(s), y = b(s); return (o === '<' ? x < y : o === '>' ? x > y : o === '<=' ? x <= y : o === '>=' ? x >= y : o === '==' ? x === y : x !== y) ? 1 : 0; }; } return a; }
  function add() { let a = mul(); while (isOp('+') || isOp('-')) { const o = next().op, b = mul(), l = a; a = o === '+' ? s => l(s) + b(s) : s => l(s) - b(s); } return a; }
  function mul() { let a = un(); while (isOp('*') || isOp('/') || isOp('%')) { const o = next().op, b = un(), l = a; a = o === '*' ? s => l(s) * b(s) : o === '/' ? s => l(s) / b(s) : s => l(s) % b(s); } return a; }
  function un() { if (isOp('-')) { next(); const a = un(); return s => -a(s); } if (isOp('+')) { next(); return un(); } return pw(); }
  function pw() { const a = atom(); if (isOp('^')) { next(); const b = un(); return s => Math.pow(a(s), b(s)); } return a; }
  function atom() {
    const t = next(); if (!t) throw new Error('unexpected end of "' + src + '"'); if (t.n !== undefined) return () => t.n;
    if (t.id) { if (isOp('(')) { next(); const args = []; if (!isOp(')')) { do { args.push(cmp()); } while (isOp(',') && next()); } if (!isOp(')')) throw new Error('missing ) in "' + src + '"'); next(); const f = FUN[t.id]; if (!f) throw new Error('unknown function ' + t.id); return s => f(...args.map(a => a(s))); }
      const id = t.id; return s => { if (!(id in s)) throw new Error('unknown variable "' + id + '"'); return s[id]; }; }
    if (t.op === '(') { const e = cmp(); if (!isOp(')')) throw new Error('missing ) in "' + src + '"'); next(); return e; } throw new Error('unexpected "' + t.op + '" in "' + src + '"');
  }
  const f = cmp(); if (p < toks.length) throw new Error('unexpected token in "' + src + '"'); return f;
}
const cache = new Map();
function ev(v, scope) {
  if (typeof v === 'number') { if (!isFinite(v)) throw new Error('number is not finite'); return v; }
  if (typeof v === 'string') { let f = cache.get(v); if (!f) { f = parse(v); cache.set(v, f); } const r = f(scope); if (!isFinite(r)) throw new Error('"' + v + '" evaluates to ' + r); return r; }
  if (Array.isArray(v)) return v.map(x => ev(x, scope));
  if (v === undefined || v === null || typeof v === 'boolean') return v;
  throw new Error('expected a number, expression or array, got ' + typeof v);
}
CAD.expr = { parse, ev };

/* ---------- defaults ---------- */
const hex = c => typeof c === 'string' ? parseInt(c.replace('#', ''), 16) : c;
CAD.DEFAULT_MATS = {
  wood: { name: 'Walnut', color: 0xb88457, metal: 0, rough: .62, rho: 650, tex: 'wood', tint: 0xffffff },
  walnut: { name: 'Walnut', color: 0xb88457, metal: 0, rough: .62, rho: 650, tex: 'wood', tint: 0xffffff },
  oak: { name: 'White oak', color: 0xd9b27a, metal: 0, rough: .6, rho: 720, tex: 'wood', tint: 0xf2d9b0 },
  redoak: { name: 'Red oak', color: 0xc9956a, metal: 0, rough: .6, rho: 700, tex: 'wood', tint: 0xe8b890 },
  maple: { name: 'Hard maple', color: 0xe8d4b0, metal: 0, rough: .55, rho: 700, tex: 'wood', tint: 0xfff4dc },
  cherry: { name: 'Cherry', color: 0xb06a45, metal: 0, rough: .58, rho: 580, tex: 'wood', tint: 0xd99060 },
  ash: { name: 'Ash', color: 0xd8c29a, metal: 0, rough: .6, rho: 670, tex: 'wood', tint: 0xf0e0c0 },
  mahogany: { name: 'Mahogany', color: 0x8a4a32, metal: 0, rough: .55, rho: 590, tex: 'wood', tint: 0xb86848 },
  teak: { name: 'Teak', color: 0xb8975a, metal: 0, rough: .5, rho: 650, tex: 'wood', tint: 0xd4b878 },
  birch: { name: 'Birch', color: 0xe0c9a0, metal: 0, rough: .58, rho: 670, tex: 'wood', tint: 0xf8e8c8 },
  cedar: { name: 'Cedar', color: 0xc4a070, metal: 0, rough: .65, rho: 380, tex: 'wood', tint: 0xe8c898 },
  pine: { name: 'Pine', color: 0xe6c690, metal: 0, rough: .6, rho: 520, tex: 'wood', tint: 0xfff0d0 },
  ply: { name: 'Plywood', color: 0xd9b88c, metal: 0, rough: .65, rho: 680, tex: 'wood', tint: 0xf0d8b8 },
  marble: { name: 'Marble', color: 0xe7e3dc, metal: 0, rough: .35, rho: 2700, tex: 'marble' }, steel: { name: 'Steel', color: 0x9aa3ad, metal: .85, rough: .4, rho: 7850 },
  aluminium: { name: 'Aluminium', color: 0xc4cad1, metal: .8, rough: .4, rho: 2700 }, brass: { name: 'Brass', color: 0xc9a43a, metal: .9, rough: .3, rho: 8500 },
  plastic: { name: 'Plastic', color: 0xe8eaec, metal: 0, rough: .5, rho: 1050 }, glass: { name: 'Glass', color: 0x9fd2e8, metal: 0, rough: .08, rho: 2500, alpha: .35 },
  rubber: { name: 'Rubber', color: 0x1b1d20, metal: 0, rough: .9, rho: 1200 }, fabric: { name: 'Fabric', color: 0x8d8f9a, metal: 0, rough: .95, rho: 300 },
  concrete: { name: 'Concrete', color: 0xb9b8b4, metal: 0, rough: .95, rho: 2400 }, paint: { name: 'Painted', color: 0xf2f2ee, metal: 0, rough: .5, rho: 700 },
};
CAD.WOOD_KEYS = ['wood', 'walnut', 'oak', 'redoak', 'maple', 'cherry', 'ash', 'mahogany', 'teak', 'birch', 'cedar', 'pine', 'ply'];
const PALETTE = [0x6aa6ff, 0x7bd88f, 0xffb454, 0xc792ea, 0xf5d547, 0xe0a458, 0x5ad4e6, 0xff7a90, 0x9aa5b1];

/* ---------- mesh-kind parts (cylinders, revolves, extrusions: exact only for display/export, not for joint checks) ---------- */
class MeshSolid {
  constructor(geoms, mat, grain) { this.mat = mat; this.grain = grain || 'x'; this.feat = []; this.exact = false; this.splittable = false; this.adds = []; this.g = CAD.mergeGeoms(geoms); CAD.creaseNormals(this.g, 38); }
  mesh() {
    const pos = this.g.attributes.position.array, nor = this.g.attributes.normal.array, uv = new Float32Array(pos.length / 3 * 2), S = 1 / 260;
    for (let t = 0; t < pos.length; t += 9) { const ux = pos[t + 3] - pos[t], uy = pos[t + 4] - pos[t + 1], uz = pos[t + 5] - pos[t + 2], vx = pos[t + 6] - pos[t], vy = pos[t + 7] - pos[t + 1], vz = pos[t + 8] - pos[t + 2];
      const n = [Math.abs(uy * vz - uz * vy), Math.abs(uz * vx - ux * vz), Math.abs(ux * vy - uy * vx)], a = n.indexOf(Math.max(...n)), ax = [0, 1, 2].filter(q => q !== a);
      for (let k = 0; k < 3; k++) { const i = (t / 3 + k); uv[i * 2] = pos[t + k * 3 + ax[0]] * S; uv[i * 2 + 1] = pos[t + k * 3 + ax[1]] * S; } }
    return { pos, nor, uv };
  }
  volume() { return Math.abs(CAD.volume(this.g)); }
  bbox() { this.g.computeBoundingBox(); const b = this.g.boundingBox; return [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z]; }
  boxes() { return [this.bbox()]; }
}
CAD.MeshSolid = MeshSolid;

function buildPrim(B, pr, sc, mat) {
  const e = k => ev(pr[k], sc), ax = pr.axis || '+z', seg = pr.seg || 32;
  switch (pr.type) {
    case 'box': B.bb(e('min'), e('max'), mat); break;
    case 'cylinder': B.cyl(e('base'), ax, e('length'), e('r'), mat, seg); break;
    case 'cone': B.cone(e('base'), ax, e('length'), e('r0'), e('r1'), mat, seg); break;
    case 'tube': B.tube(e('base'), ax, e('length'), e('ro'), e('ri'), mat, seg); break;
    case 'revolve': B.rev(e('at') || [0, 0, 0], ax, e('profile'), mat, seg); break;
    case 'sphere': { const R = e('r'), c = e('center') || [0, 0, 0], pts = []; for (let i = 0; i <= 16; i++) { const a = (-90 + 180 * i / 16) * D2R; pts.push([Math.max(0, R * Math.cos(a)), R * Math.sin(a)]); } B.rev(c, '+z', pts, mat, seg); break; }
    case 'extrude': { const [w0, w1] = e('range'); B.ext(pr.plane || 'xy', e('profile'), w0, w1, mat, (pr.holes || []).map(h => h.poly ? { poly: ev(h.poly, sc) } : { c: ev(h.c, sc), r: ev(h.r, sc) }), seg); break; }
    default: throw new Error('unknown prim type "' + pr.type + '" (box, cylinder, cone, tube, revolve, sphere, extrude)');
  }
}
/* placement: T(pos) · Rz · Ry · Rx, angles in degrees */
const MK = (pos, rot) => { const m = new T.Matrix4().makeTranslation(pos[0], pos[1], pos[2]); if (rot && (rot[0] || rot[1] || rot[2])) m.multiply(new T.Matrix4().makeRotationFromEuler(new T.Euler(rot[0] * D2R, rot[1] * D2R, rot[2] * D2R, 'ZYX'))); return m; };
CAD.specMatrix = MK;
const expand = (item, scope, fn) => { if (item.repeat) { const r = item.repeat, n = ev(r.count, scope); if (n > 600) throw new Error('repeat count ' + n + ' is too large (max 600)'); for (let k = 0; k < n; k++) fn(Object.assign({}, scope, { [r.var || 'i']: k })); } else fn(scope); };

class SpecModel {
  constructor(spec, overrides) { this.spec = spec; this.errors = []; this.warnings = []; this.defs = new Map(); this.insts = []; this.paramDefs = []; this.kinematics = {}; this.P = {}; this.groups = []; this.steps = []; this.materials = CAD.DEFAULT_MATS; this.meta = { name: 'Untitled', description: '', assumptions: [], units: 'mm' };
    try { this.build(overrides || {}); } catch (e) { this.errors.push(e.message); } }
  at(path, fn) { try { return fn(); } catch (e) { this.errors.push(path + ': ' + e.message); return undefined; } }
  build(ov) {
    const sp = this.spec, scope = {}; if (!sp || typeof sp !== 'object') throw new Error('spec must be a JSON object'); if (!Array.isArray(sp.parts) || !sp.parts.length) throw new Error('spec.parts must be a non-empty array');
    Object.entries(sp.params || {}).forEach(([k, v]) => this.at('params.' + k, () => {
      if (typeof v === 'number') { scope[k] = ov[k] !== undefined ? ov[k] : v; this.paramDefs.push({ key: k, label: k, value: scope[k], min: Math.round(v * .5), max: Math.round(v * 1.5), step: v >= 100 ? 10 : 1 }); }
      else if (typeof v === 'string') scope[k] = ev(v, scope);
      else if (v && 'expr' in v) scope[k] = ev(v.expr, scope);
      else { const val = ov[k] !== undefined ? ov[k] : ev(v.value, scope); scope[k] = val; this.paramDefs.push({ key: k, label: v.label || k, unit: v.unit, value: val, min: v.min !== undefined ? v.min : Math.round(val * .5), max: v.max !== undefined ? v.max : Math.round(val * 1.5), step: v.step || (val >= 100 ? 10 : 1) }); }
    }));
    this.P = scope;
    this.materials = Object.assign({}, CAD.DEFAULT_MATS);
    Object.entries(sp.materials || {}).forEach(([k, m]) => { const b = CAD.DEFAULT_MATS[m.base || k] || { metal: 0, rough: .6, rho: 800, color: 0xcccccc }; this.materials[k] = Object.assign({}, b, m, { color: hex(m.color !== undefined ? m.color : b.color), name: m.name || k, tint: m.tint !== undefined ? hex(m.tint) : b.tint }); });
    CAD.MATS = this.materials;
    const gids = []; (sp.groups || []).forEach(g => gids.push(g.id)); sp.parts.forEach(p => { const g = (p && p.group) || 'main'; if (!gids.includes(g)) gids.push(g); });
    this.groups = gids.map((id, i) => { const g = (sp.groups || []).find(x => x.id === id) || {}; return { id, name: g.name || id.replace(/[_-]/g, ' ').replace(/^./, c => c.toUpperCase()), color: hex(g.color !== undefined ? g.color : PALETTE[i % PALETTE.length]) }; });
    const seen = new Set();
    sp.parts.forEach((p, pi) => this.at('parts[' + pi + ']' + (p && p.id ? ' (' + p.id + ')' : ''), () => {
      if (!p.id || typeof p.id !== 'string') throw new Error('missing string "id"'); if (seen.has(p.id)) throw new Error('duplicate id'); seen.add(p.id);
      const kind = p.kind || (p.prims ? 'mesh' : 'solid'); let mat = p.material || 'wood'; if (!this.materials[mat]) { this.warnings.push(p.id + ': unknown material "' + mat + '", using wood'); mat = 'wood'; }
      const base = Object.assign({}, scope); Object.entries(p.vars || {}).forEach(([k, v]) => { base[k] = ev(v, base); });
      let solid;
      if (kind === 'solid') {
        solid = new Solid({ grain: p.grain || 'x', mat }); if (!Array.isArray(p.ops) || !p.ops.length) throw new Error('solid part needs a non-empty "ops" array');
        p.ops.forEach((op, oi) => this.at('parts[' + pi + '].ops[' + oi + ']', () => expand(op, base, sc => {
          const isAdd = 'add' in op, isCut = 'cut' in op; if (isAdd === isCut) throw new Error('each op needs exactly one of "add" or "cut"'); const b = ev(isAdd ? op.add : op.cut, sc);
          if (!Array.isArray(b) || b.length !== 6) throw new Error('box must be [x0,y0,z0,x1,y1,z1]'); const o = op.label ? { label: op.label } : {};
          if (isAdd) solid.add(...b, op.tag, o); else solid.cut(...b, op.tag, Object.assign({ fill: !!op.fill }, o)); })));
        if (!solid.adds.length) throw new Error('part has no "add" boxes');
      } else if (kind === 'mesh') {
        const B = new CAD.Builder(); if (!Array.isArray(p.prims) || !p.prims.length) throw new Error('mesh part needs a non-empty "prims" array');
        p.prims.forEach((pr, qi) => this.at('parts[' + pi + '].prims[' + qi + ']', () => expand(pr, base, sc => buildPrim(B, pr, sc, 'm'))));
        if (!B.items.length) throw new Error('no geometry produced'); solid = new MeshSolid(B.items.map(i => i.g), mat, p.grain);
      } else throw new Error('unknown kind "' + kind + '" (solid | mesh)');
      this.defs.set(p.id, { id: p.id, name: p.name || p.id, grp: p.group || 'main', solid, spec: p.spec || '', note: (p.notes || []).join(' '), notes: p.notes || [], tools: p.tools || [], _scope: base });
    }));
    sp.parts.forEach((p, pi) => { const d = p && this.defs.get(p.id); if (!d) return; this.at('parts[' + pi + '].instances', () => {
      (p.instances || [p.place || {}]).forEach(it => expand(it, d._scope, sc => { const pos = ev(it.pos || [0, 0, 0], sc), rot = ev(it.rot || [0, 0, 0], sc), inst = { def: p.id, m: MK(pos, rot), step: it.step !== undefined ? ev(it.step, sc) : 0, kin: it.kin, tag: it.tag };
        if (it.explode) inst.ex = ev(it.explode, sc); this.insts.push(inst); })); }); });
    Object.entries(sp.kinematics || {}).forEach(([k, v]) => this.at('kinematics.' + k, () => { this.kinematics[k] = { label: v.label || k, axis: ev(v.axis, scope), range: ev(v.range, scope), unit: v.unit || 'mm', pivot: v.pivot ? ev(v.pivot, scope) : null }; }));
    this.finalize();
    const maxStep = Math.max(0, ...this.insts.map(i => i.step)), st = sp.steps || [];
    this.steps = Array.from({ length: maxStep + 1 }, (_, i) => { const s = st[i]; return typeof s === 'string' ? { title: s } : Object.assign({ title: 'Assembly step ' + (i + 1) }, s || {}); });
    CAD.GROUPS = this.groups; CAD.STEPS = this.steps.map(s => s.title);
    this.meta = { name: sp.name || 'Untitled object', description: sp.description || '', assumptions: sp.assumptions || [], units: sp.units || 'mm' };
    this.sanity();
  }
  finalize() {
    const cnt = {}; this.insts.forEach(i => { cnt[i.def] = (cnt[i.def] || 0) + 1; i.qtyIdx = cnt[i.def]; });
    this.defs.forEach(d => { d.qty = cnt[d.id] || 0; d.vol = d.solid.volume(); d.box = d.solid.bbox(); d.boxes = d.solid.boxes(); d.mass = d.vol * 1e-9 * (this.materials[d.solid.mat].rho || 800); d.size = [d.box[3] - d.box[0], d.box[4] - d.box[1], d.box[5] - d.box[2]]; });
    this.defs.forEach((d, id) => { if (!d.qty) this.warnings.push(id + ': part is never placed (no instances)'); });
    if (!this.insts.length) return;
    const bb = CAD.bounds(this), c = [(bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2], diag = Math.hypot(bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]);
    this.insts.forEach(i => { if (i.ex) return; const a = CAD.instAABB(this, i), p = [(a[0] + a[3]) / 2 - c[0], (a[1] + a[4]) / 2 - c[1], ((a[2] + a[5]) / 2 - c[2]) * 1.4 + 30], l = Math.hypot(...p) || 1, k = diag * (.12 + .03 * i.step) / l; i.ex = [p[0] * k, p[1] * k, p[2] * k]; });
  }
  sanity() {
    if (!this.insts.length) { this.errors.push('no parts were placed'); return; }
    const bb = CAD.bounds(this); if (bb[2] < -2) this.warnings.push('model extends ' + Math.round(-bb[2]) + ' mm below the floor (z<0)');
    const big = Math.max(bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]); if (big > 20000) this.warnings.push('object is ' + Math.round(big) + ' mm long: check units (mm expected)'); if (big < 20) this.warnings.push('object is tiny (' + Math.round(big) + ' mm): check units (mm expected)');
    this.bounds = bb; this.size = [bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]];
  }
}
CAD.buildSpec = (spec, ov) => new SpecModel(spec, ov);
CAD.SpecModel = SpecModel;

/* Scale a baked (non-parametric) spec so overall size becomes targetW×D×H (mm). Pure numbers in boxes/pos/explode/pivots are scaled; expression strings are left alone. */
CAD.scaleSpec = function (spec, sx, sy, sz) {
  const s = JSON.parse(JSON.stringify(spec)), ax = [sx, sy, sz];
  const n = (v, i) => (typeof v === 'number' && isFinite(v) ? v * ax[i] : v);
  const v3 = a => Array.isArray(a) && a.length >= 3 ? [n(a[0], 0), n(a[1], 1), n(a[2], 2)].concat(a.slice(3)) : a;
  const box6 = a => Array.isArray(a) && a.length >= 6 ? [n(a[0], 0), n(a[1], 1), n(a[2], 2), n(a[3], 0), n(a[4], 1), n(a[5], 2)].concat(a.slice(6)) : a;
  const scalePrim = p => {
    if (!p || typeof p !== 'object') return;
    if (p.min) p.min = v3(p.min); if (p.max) p.max = v3(p.max); if (p.base) p.base = v3(p.base); if (p.center) p.center = v3(p.center);
    if (typeof p.length === 'number') { const axis = String(p.axis || '+z').replace('+', '').replace('-', ''); p.length *= axis === 'x' ? sx : axis === 'y' ? sy : sz; }
    ['r', 'r0', 'r1', 'ro', 'ri'].forEach(k => { if (typeof p[k] === 'number') p[k] *= Math.cbrt(sx * sy * sz); });
    if (Array.isArray(p.profile)) p.profile = p.profile.map(pt => Array.isArray(pt) ? pt.map((v, i) => typeof v === 'number' ? v * (i === 0 ? Math.sqrt(sx * sy) : sz) : v) : pt);
    if (Array.isArray(p.range) && p.range.length >= 2) { const pl = String(p.plane || 'xy'); const wi = pl.includes('x') && pl.includes('y') ? 2 : pl.includes('x') ? 1 : 0; p.range = [n(p.range[0], wi === 2 ? 2 : wi === 1 ? 1 : 0), n(p.range[1], wi === 2 ? 2 : wi === 1 ? 1 : 0)]; }
  };
  (s.parts || []).forEach(p => {
    (p.ops || []).forEach(op => { if (op.add) op.add = box6(op.add); if (op.cut) op.cut = box6(op.cut); });
    (p.prims || []).forEach(scalePrim);
    (p.instances || []).forEach(inst => { if (inst.pos) inst.pos = v3(inst.pos); if (inst.explode) inst.explode = v3(inst.explode); });
  });
  Object.values(s.kinematics || {}).forEach(k => {
    if (k.pivot) k.pivot = v3(k.pivot);
    if (Array.isArray(k.range) && k.unit !== 'deg') k.range = k.range.map((v, i) => typeof v === 'number' ? v * (k.axis ? Math.abs(k.axis[0]) * sx + Math.abs(k.axis[1]) * sy + Math.abs(k.axis[2]) * sz : sx) : v);
  });
  return s;
};
})(typeof globalThis !== 'undefined' ? globalThis : window);
