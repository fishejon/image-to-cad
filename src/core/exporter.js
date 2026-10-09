/* exporter.js — print-ready STL: orientation, scale, auto-split with alignment keys, plate nesting, ZIP.
   Pure functions (no DOM) so they run in Node tests. `mult` is a length multiplier (1/5 for a 1:5 model). */
(function (root) {
'use strict';
const CAD = root.CAD, T = root.THREE, V = (x, y, z) => new T.Vector3(x, y, z);
const E = CAD.exporter = {};
E.safe = n => n.replace(/[^A-Za-z0-9._-]+/g, '_').replace(/^_+|_+$/g, '');
E.orientMat = function (size) { // longest axis → X, middle → Y, shortest → Z (proper rotation)
  const idx = [0, 1, 2].sort((a, b) => size[b] - size[a]), m = new T.Matrix4(), r = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]; idx.forEach((ax, i) => { r[i][ax] = 1; });
  m.set(...r[0], 0, ...r[1], 0, ...r[2], 0, 0, 0, 0, 1); if (m.determinant() < 0) { r[2] = r[2].map(v => -v); m.set(...r[0], 0, ...r[1], 0, ...r[2], 0, 0, 0, 0, 1); } return m;
};
E.xfPos = function (pos, m, s) { const e = m.elements, o = new Float32Array(pos.length); for (let i = 0; i < pos.length; i += 3) { const x = pos[i], y = pos[i + 1], z = pos[i + 2]; o[i] = (e[0] * x + e[4] * y + e[8] * z + e[12]) * s; o[i + 1] = (e[1] * x + e[5] * y + e[9] * z + e[13]) * s; o[i + 2] = (e[2] * x + e[6] * y + e[10] * z + e[14]) * s; } return o; };
E.posBox = a => { const b = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]; for (let i = 0; i < a.length; i += 3) for (let k = 0; k < 3; k++) { b[k] = Math.min(b[k], a[i + k]); b[k + 3] = Math.max(b[k + 3], a[i + k]); } return b; };
E.groundPos = a => { const b = E.posBox(a), o = new Float32Array(a.length); for (let i = 0; i < a.length; i += 3) { o[i] = a[i] - b[0]; o[i + 1] = a[i + 1] - b[1]; o[i + 2] = a[i + 2] - b[2]; } return o; };
/* → [{name, pos (Float32Array, print frame, grounded), size:[x,y,z], part, split, over}] */
E.printPieces = function (d, mult, bed, split) {
  const sz = d.size, om = E.orientMat(sz), idx = [0, 1, 2].sort((a, b) => sz[b] - sz[a]), box = d.box, out = [];
  if (!d.solid.splittable || !split) { const m = d.solid.mesh(); const pos = E.groundPos(E.xfPos(m.pos, om, mult)), b = E.posBox(pos), size = [b[3], b[4], b[5]];
    const lim = [Math.max(bed[0], bed[1]), Math.min(bed[0], bed[1]), bed[2]], xy = [Math.max(size[0], size[1]), Math.min(size[0], size[1])]; return [{ name: d.id, pos, size, part: d.id, split: false, over: xy[0] > lim[0] + .01 || xy[1] > lim[1] + .01 || size[2] > lim[2] + .01 }]; }
  const lim = [Math.max(bed[0], bed[1]) - 6, Math.min(bed[0], bed[1]) - 6, bed[2] - 2];
  const n = idx.map((ax, r) => Math.max(1, Math.ceil(sz[ax] * mult / lim[r] - 1e-9)));
  const cuts = idx.map((ax, r) => Array.from({ length: n[r] - 1 }, (_, i) => box[ax] + sz[ax] * (i + 1) / n[r]));
  const kd = 5 / mult, clr = .2 / mult, ranges = idx.map((ax, r) => Array.from({ length: n[r] }, (_, i) => [i ? cuts[r][i - 1] : box[ax] - 1, i < n[r] - 1 ? cuts[r][i] : box[ax + 3] + 1])), total = n[0] * n[1] * n[2];
  for (let i0 = 0; i0 < n[0]; i0++) for (let i1 = 0; i1 < n[1]; i1++) for (let i2 = 0; i2 < n[2]; i2++) {
    const I = [i0, i1, i2]; let clip = null; const ka = [], kc = [];
    if (total > 1) {
      clip = [0, 0, 0, 0, 0, 0]; idx.forEach((ax, r) => { clip[ax] = ranges[r][I[r]][0]; clip[ax + 3] = ranges[r][I[r]][1]; });
      idx.forEach((ax, r) => {
        const o1 = idx.filter((_, q) => q !== r);
        const keyBox = (a0, a1, cl) => { const b = [0, 0, 0, 0, 0, 0]; b[ax] = a0; b[ax + 3] = a1; o1.forEach(oa => { const ro = idx.indexOf(oa), lo = Math.max(ranges[ro][I[ro]][0], box[oa]), hi = Math.min(ranges[ro][I[ro]][1], box[oa + 3]), mid = (lo + hi) / 2, ext = hi - lo, span = Math.min(Math.max(ext * .4, 4 / mult), 30 / mult, ext * .7); b[oa] = mid - span / 2 - cl; b[oa + 3] = mid + span / 2 + cl; }); return b; };
        if (I[r] < n[r] - 1) { const c = cuts[r][I[r]]; ka.push(keyBox(c - 1 / mult, c + kd, 0)); }
        if (I[r] > 0) { const c = cuts[r][I[r] - 1]; kc.push(keyBox(c - 1 / mult, c + kd + clr, clr)); }
      });
    }
    const m = d.solid.mesh({ clip, kadds: ka, kcuts: kc }); if (!m.pos.length) continue;
    const pos = E.groundPos(E.xfPos(m.pos, om, mult)), b = E.posBox(pos); out.push({ name: total > 1 ? d.id + '_p' + (i0 + 1) + (i1 + 1) + (i2 + 1) : d.id, pos, size: [b[3], b[4], b[5]], part: d.id, split: total > 1, over: false });
  }
  return out;
};
E.stlFiles = function (M, defs, o) { // o: {mult, bed, split, qty:true}
  const files = [], tag = o.mult === 1 ? '1-1' : '1-' + Math.round(1 / o.mult);
  defs.forEach(d => E.printPieces(d, o.mult, o.bed, o.split).forEach(p => files.push({ name: E.safe(p.name) + (o.qty !== false ? '_x' + d.qty : '') + '_' + tag + '.stl', data: CAD.stlBinary([p.pos]), tris: p.pos.length / 9, pos: p.pos, over: p.over }))); return files;
};
E.assemblyFile = function (M, mult, name) { const tr = []; M.insts.forEach(i => { const d = M.defs.get(i.def), m = d.mesh || (d.mesh = d.solid.mesh()); tr.push(E.xfPos(m.pos, i.m, mult)); }); return { name: E.safe(name) + '.stl', data: CAD.stlBinary(tr), tris: tr.reduce((s, a) => s + a.length / 9, 0) }; };
E.nest = function (M, mult, bed, split, gap) {
  gap = gap || 4; const items = []; M.defs.forEach(d => { const ps = E.printPieces(d, mult, bed, split); for (let q = 0; q < d.qty; q++) ps.forEach(p => items.push({ p, q, d })); });
  items.sort((a, b) => Math.max(b.p.size[0], b.p.size[1]) - Math.max(a.p.size[0], a.p.size[1])); const plates = [], over = [], B = [bed[0], bed[1]];
  const tryPlace = (pl, w, h) => { for (const row of pl.rows) if (row.x + w <= B[0] && h <= row.h) { const o = { x: row.x, y: row.y }; row.x += w + gap; return o; } const last = pl.rows[pl.rows.length - 1], ny = last ? last.y + last.h + gap : 0; if (ny + h <= B[1] && w <= B[0]) { pl.rows.push({ x: w + gap, y: ny, h }); return { x: 0, y: ny }; } return null; };
  items.forEach(it => { const [w0, h0, z0] = it.p.size; if (z0 > bed[2] || (Math.max(w0, h0) > Math.max(B[0], B[1]) || Math.min(w0, h0) > Math.min(B[0], B[1]))) { over.push(it); return; }
    for (const pl of plates) for (const rot of [0, 1]) { const w = rot ? h0 : w0, h = rot ? w0 : h0, o = tryPlace(pl, w, h); if (o) { pl.items.push({ it, o, rot }); return; } }
    const pl = { rows: [], items: [] }; plates.push(pl); for (const rot of [0, 1]) { const w = rot ? h0 : w0, h = rot ? w0 : h0, o = tryPlace(pl, w, h); if (o) { pl.items.push({ it, o, rot }); return; } } over.push(it); });
  return { plates, over };
};
E.plateFiles = function (M, mult, bed, split) {
  const { plates, over } = E.nest(M, mult, bed, split), files = [], tag = mult === 1 ? '1-1' : '1-' + Math.round(1 / mult); let man = 'Print plates, scale ' + tag.replace('-', ':') + ', bed ' + bed.join('×') + ' mm, 4 mm gaps\n\n';
  plates.forEach((pl, i) => { const nm = 'plate_' + String(i + 1).padStart(2, '0') + '_' + tag, parts = []; man += nm + '.stl\n';
    pl.items.forEach(({ it, o, rot }) => { const a = it.p.pos, out = new Float32Array(a.length); for (let k = 0; k < a.length; k += 3) { let x = a[k], y = a[k + 1]; if (rot) { const nx = y, ny = it.p.size[0] - x; x = nx; y = ny; } out[k] = x + o.x; out[k + 1] = y + o.y; out[k + 2] = a[k + 2]; } parts.push(out); man += '  ' + it.d.name + (it.p.split ? ' [' + it.p.name + ']' : '') + '\n'; });
    files.push({ name: nm + '.stl', data: CAD.stlBinary(parts), tris: parts.reduce((s, a) => s + a.length / 9, 0) }); });
  if (over.length) man += '\nDid NOT fit: ' + [...new Set(over.map(o => o.p.name))].join(', ') + '\n'; files.push({ name: 'MANIFEST.txt', data: man }); return { files, plates, over };
};
E.cutCSV = function (M) {
  const esc = s => '"' + String(s).replace(/"/g, '""') + '"', g = id => (CAD.GROUPS.find(x => x.id === id) || { name: id }).name;
  const plan = CAD.lumberPlan(M);
  let c = 'BUY LIST\nQty,Stock,Length,Material,Blanks on these boards\n';
  plan.summary.forEach(s => { c += [s.qty, esc(s.stock), esc(s.buy), esc(s.mat), s.pieces].join(',') + '\n'; });
  c += '\nCUT LIST PER BOARD\nBoard,Stock,Buy,Material,Part,Finished T×W×L,Cut length\n';
  plan.boards.forEach(b => b.cuts.forEach(cut => {
    c += [b.id, esc(b.stock), esc(b.buy), esc(b.mat), esc(cut.name), esc(cut.finished), esc(cut.len)].join(',') + '\n';
  }));
  c += '\nPARTS (finished sizes)\nID,Part,Group,Qty,Thickness,Width,Length,Material,Spec\n';
  CAD.cutList(M).sort((a, b) => a.grp.localeCompare(b.grp)).forEach(r => {
    c += [r.id, esc(r.name), esc(g(r.grp)), r.qty, esc(CAD.fmtInch(r.T)), esc(CAD.fmtInch(r.W)), esc(CAD.fmtInch(r.L)), esc(r.mat), esc(CAD.inchifyText(r.spec || ''))].join(',') + '\n';
  });
  return c;
};
})(typeof globalThis !== 'undefined' ? globalThis : window);
