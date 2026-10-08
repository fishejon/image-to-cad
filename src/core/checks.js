/* checks.js — exact design review for the sideboard */
(function (root) {
'use strict';
const CAD = root.CAD, T = root.THREE;
CAD.instBoxes = (M, i) => { if (!i._wb || i._wbm !== i.m.elements.join()) { i._wb = CAD.xfBoxes(M.defs.get(i.def).boxes, i.m); i._wbm = i.m.elements.join(); i._ab = i._wb.reduce((a, b) => [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.min(a[2], b[2]), Math.max(a[3], b[3]), Math.max(a[4], b[4]), Math.max(a[5], b[5])], [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]); } return i._wb; };
CAD.instAABB = (M, i) => { CAD.instBoxes(M, i); return i._ab; };
const ov = (a, b) => a[0] < b[3] - 1e-6 && b[0] < a[3] - 1e-6 && a[1] < b[4] - 1e-6 && b[1] < a[4] - 1e-6 && a[2] < b[5] - 1e-6 && b[2] < a[5] - 1e-6;
CAD.interference = function (M, tol) {
  tol = tol === undefined ? 1 : tol; const I = M.insts.filter(i => M.defs.get(i.def).solid.exact !== false), res = [];
  I.forEach(i => CAD.instBoxes(M, i));
  for (let a = 0; a < I.length; a++) for (let b = a + 1; b < I.length; b++) {
    if (!ov(I[a]._ab, I[b]._ab)) continue; let v = 0;
    for (const A of I[a]._wb) { if (!ov(A, I[b]._ab)) continue; for (const B of I[b]._wb) v += CAD.boxInter(A, B); }
    if (v > tol) res.push({ a: I[a].def + '#' + I[a].qtyIdx, b: I[b].def + '#' + I[b].qtyIdx, vol: v });
  }
  return res;
};
/* every cut feature flagged fill:true must be completely filled by mating parts */
CAD.jointFill = function (M) {
  const I = M.insts.filter(i => M.defs.get(i.def).solid.exact !== false), rows = []; I.forEach(i => CAD.instBoxes(M, i));
  I.forEach(i => { const d = M.defs.get(i.def);
    (d.solid.feat || []).forEach(f => { if (f.kind !== 'cut' || !f.fill) return; const fb = CAD.xfBoxes([f.box], i.m)[0], fv = CAD.boxVol(fb); let filled = 0, by = new Set();
      I.forEach(j => { if (j === i || !ov(fb, j._ab)) return; for (const B of j._wb) { const q = CAD.boxInter(fb, B); if (q > 0) { filled += q; by.add(j.def); } } });
      rows.push({ part: i.def + '#' + i.qtyIdx, tag: f.tag, vol: fv, filled, ratio: filled / fv, by: [...by].join('+') }); }); });
  return rows;
};
CAD.manifoldPos = function (pos) {
  const key = i => Math.round(pos[i] * 100) + ',' + Math.round(pos[i + 1] * 100) + ',' + Math.round(pos[i + 2] * 100), e = new Map();
  for (let t = 0; t < pos.length; t += 9) { const k = [key(t), key(t + 3), key(t + 6)]; for (let a = 0; a < 3; a++) { const f = k[a] + '>' + k[(a + 1) % 3]; e.set(f, (e.get(f) || 0) + 1); } }
  let bad = 0; e.forEach((c, k) => { const [u, v] = k.split('>'); if (c !== (e.get(v + '>' + u) || 0)) bad++; }); return bad;
};
CAD.manifoldReport = M => { const r = []; M.defs.forEach(d => { const m = d.mesh || (d.mesh = d.solid.mesh()); r.push({ id: d.id, bad: CAD.manifoldPos(m.pos), tris: m.pos.length / 9 }); }); return r; };
CAD.bounds = M => { const b = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]; M.insts.forEach(i => { const a = CAD.instAABB(M, i); for (let k = 0; k < 3; k++) { b[k] = Math.min(b[k], a[k]); b[k + 3] = Math.max(b[k + 3], a[k + 3]); } }); return b; };
CAD.cutList = M => { const rows = []; M.defs.forEach(d => { if (!d.qty) return; const s = d.size.slice().sort((a, b) => b - a); rows.push({ id: d.id, name: d.name, grp: d.grp, qty: d.qty, T: s[2], W: s[1], L: s[0], mat: CAD.MATS[d.solid.mat].name, vol: d.vol, mass: d.mass, spec: d.spec || '' }); }); return rows; };
})(typeof globalThis !== 'undefined' ? globalThis : window);
