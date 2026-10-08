/* csg.js — exact axis-aligned solid modelling: union(adds) − cuts on a compressed grid. Units mm. */
(function (root) {
'use strict';
const CAD = root.CAD = root.CAD || {}, T = root.THREE;
const R = v => Math.round(v * 1000) / 1000;
class Solid {
  constructor(o) { Object.assign(this, { grain: 'x', mat: 'wood' }, o || {}); this.adds = []; this.cuts = []; this.kadds = []; this.kcuts = []; this.feat = []; }
  _b(x0, y0, z0, x1, y1, z1) { return [R(Math.min(x0, x1)), R(Math.min(y0, y1)), R(Math.min(z0, z1)), R(Math.max(x0, x1)), R(Math.max(y0, y1)), R(Math.max(z0, z1))]; }
  add(x0, y0, z0, x1, y1, z1, tag, o) { const b = this._b(x0, y0, z0, x1, y1, z1); this.adds.push(b); if (tag) this.feat.push(Object.assign({ kind: 'add', tag, box: b }, o)); return this; }
  cut(x0, y0, z0, x1, y1, z1, tag, o) { const b = this._b(x0, y0, z0, x1, y1, z1); this.cuts.push(b); if (tag) this.feat.push(Object.assign({ kind: 'cut', tag, box: b, fill: false }, o)); return this; }
  clone() { const s = new Solid({ grain: this.grain, mat: this.mat }); s.adds = this.adds.map(b => b.slice()); s.cuts = this.cuts.map(b => b.slice()); s.feat = this.feat.map(f => Object.assign({}, f, { box: f.box.slice() })); return s; }
  /* evaluate on a grid. opts.clip = box; opts.kadds / kcuts = key boxes applied after clipping */
  grid(opts) {
    opts = opts || {}; const clip = opts.clip, ka = opts.kadds || [], kc = opts.kcuts || [];
    const cs = [new Set(), new Set(), new Set()];
    [this.adds, this.cuts, ka, kc, clip ? [clip] : []].forEach(L => L.forEach(b => { for (let a = 0; a < 3; a++) { cs[a].add(b[a]); cs[a].add(b[a + 3]); } }));
    const co = cs.map(s => [...s].sort((p, q) => p - q)), n = co.map(c => c.length - 1);
    if (n[0] < 1 || n[1] < 1 || n[2] < 1) return { co, n, c: new Uint8Array(0) };
    const idx = co.map(c => { const m = new Map(); c.forEach((v, i) => m.set(v, i)); return m; });
    const c = new Uint8Array(n[0] * n[1] * n[2]), I = (i, j, k) => (k * n[1] + j) * n[0] + i;
    const fill = (b, v) => { const r = [0, 1, 2].map(a => [idx[a].get(b[a]), idx[a].get(b[a + 3])]); for (let k = r[2][0]; k < r[2][1]; k++) for (let j = r[1][0]; j < r[1][1]; j++) for (let i = r[0][0]; i < r[0][1]; i++) c[I(i, j, k)] = v; };
    this.adds.forEach(b => fill(b, 1));
    if (clip) { const r = [0, 1, 2].map(a => [idx[a].get(clip[a]), idx[a].get(clip[a + 3])]); for (let k = 0; k < n[2]; k++) for (let j = 0; j < n[1]; j++) for (let i = 0; i < n[0]; i++) if (i < r[0][0] || i >= r[0][1] || j < r[1][0] || j >= r[1][1] || k < r[2][0] || k >= r[2][1]) c[I(i, j, k)] = 0; }
    ka.forEach(b => fill(b, 1)); this.cuts.forEach(b => fill(b, 0)); kc.forEach(b => fill(b, 0));
    return { co, n, c, I };
  }
  /* run-merged solid boxes (for interference tests / volume) */
  boxes(opts) {
    const g = this.grid(opts), out = []; if (!g.c.length) return out; const { co, n, c, I } = g;
    for (let k = 0; k < n[2]; k++) for (let j = 0; j < n[1]; j++) { let i = 0; while (i < n[0]) { if (!c[I(i, j, k)]) { i++; continue; } let e = i; while (e < n[0] && c[I(e, j, k)]) e++; out.push([co[0][i], co[1][j], co[2][k], co[0][e], co[1][j + 1], co[2][k + 1]]); i = e; } }
    return out;
  }
  volume(opts) { return this.boxes(opts).reduce((s, b) => s + (b[3] - b[0]) * (b[4] - b[1]) * (b[5] - b[2]), 0); }
  /* triangle surface with UVs; outward winding. */
  mesh(opts) {
    const g = this.grid(opts), pos = [], uv = [], nor = []; if (!g.c.length) return { pos: new Float32Array(0), uv: new Float32Array(0), nor: new Float32Array(0) };
    const { co, n, c, I } = g, ga = 'xyz'.indexOf(this.grain), S = 1 / 260;
    const solid = (i, j, k) => i >= 0 && j >= 0 && k >= 0 && i < n[0] && j < n[1] && k < n[2] && c[I(i, j, k)];
    const quad = (p0, p1, p2, p3, a, sgn) => { // p0..p3 CCW seen from outside
      const N = [0, 0, 0]; N[a] = sgn; const tri = (A, B, C) => { [A, B, C].forEach(P => { pos.push(P[0], P[1], P[2]); nor.push(N[0], N[1], N[2]);
        const ax = [0, 1, 2].filter(q => q !== a); let u, v; if (ga !== a) { u = P[ga]; v = P[ax.find(q => q !== ga)]; } else { u = P[ax[0]]; v = P[ax[1]]; } uv.push(u * S, v * S); }); };
      tri(p0, p1, p2); tri(p0, p2, p3);
    };
    for (let k = 0; k < n[2]; k++) for (let j = 0; j < n[1]; j++) for (let i = 0; i < n[0]; i++) {
      if (!c[I(i, j, k)]) continue; const x0 = co[0][i], x1 = co[0][i + 1], y0 = co[1][j], y1 = co[1][j + 1], z0 = co[2][k], z1 = co[2][k + 1];
      if (!solid(i + 1, j, k)) quad([x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1], 0, 1);
      if (!solid(i - 1, j, k)) quad([x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0], 0, -1);
      if (!solid(i, j + 1, k)) quad([x0, y1, z0], [x0, y1, z1], [x1, y1, z1], [x1, y1, z0], 1, 1);
      if (!solid(i, j - 1, k)) quad([x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1], 1, -1);
      if (!solid(i, j, k + 1)) quad([x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1], 2, 1);
      if (!solid(i, j, k - 1)) quad([x0, y0, z0], [x0, y1, z0], [x1, y1, z0], [x1, y0, z0], 2, -1);
    }
    return { pos: new Float32Array(pos), uv: new Float32Array(uv), nor: new Float32Array(nor) };
  }
  bbox() { const b = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]; this.adds.forEach(a => { for (let i = 0; i < 3; i++) { b[i] = Math.min(b[i], a[i]); b[i + 3] = Math.max(b[i + 3], a[i + 3]); } }); return b; }
}
CAD.Solid = Solid;
/* transform axis-aligned boxes by a Matrix4 made of 90° rotations/translation → AABB list */
CAD.xfBoxes = function (boxes, m) {
  const e = m.elements, out = [];
  boxes.forEach(b => { const lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
    for (let c = 0; c < 8; c++) { const x = c & 1 ? b[3] : b[0], y = c & 2 ? b[4] : b[1], z = c & 4 ? b[5] : b[2];
      const X = e[0] * x + e[4] * y + e[8] * z + e[12], Y = e[1] * x + e[5] * y + e[9] * z + e[13], Z = e[2] * x + e[6] * y + e[10] * z + e[14];
      lo[0] = Math.min(lo[0], X); lo[1] = Math.min(lo[1], Y); lo[2] = Math.min(lo[2], Z); hi[0] = Math.max(hi[0], X); hi[1] = Math.max(hi[1], Y); hi[2] = Math.max(hi[2], Z); }
    out.push([R(lo[0]), R(lo[1]), R(lo[2]), R(hi[0]), R(hi[1]), R(hi[2])]); });
  return out;
};
CAD.boxVol = b => (b[3] - b[0]) * (b[4] - b[1]) * (b[5] - b[2]);
CAD.boxInter = (a, b) => { const x = Math.min(a[3], b[3]) - Math.max(a[0], b[0]), y = Math.min(a[4], b[4]) - Math.max(a[1], b[1]), z = Math.min(a[5], b[5]) - Math.max(a[2], b[2]); return x > 1e-6 && y > 1e-6 && z > 1e-6 ? x * y * z : 0; };
})(typeof globalThis !== 'undefined' ? globalThis : window);
