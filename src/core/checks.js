/* checks.js — design review: exact solid interference + coarse mesh AABB, joint fill, manifold. */
(function (root) {
'use strict';
const CAD = root.CAD, T = root.THREE;
CAD.instBoxes = (M, i) => { if (!i._wb || i._wbm !== i.m.elements.join()) { i._wb = CAD.xfBoxes(M.defs.get(i.def).boxes, i.m); i._wbm = i.m.elements.join(); i._ab = i._wb.reduce((a, b) => [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.min(a[2], b[2]), Math.max(a[3], b[3]), Math.max(a[4], b[4]), Math.max(a[5], b[5])], [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]); } return i._wb; };
CAD.instAABB = (M, i) => { CAD.instBoxes(M, i); return i._ab; };
const ov = (a, b) => a[0] < b[3] - 1e-6 && b[0] < a[3] - 1e-6 && a[1] < b[4] - 1e-6 && b[1] < a[4] - 1e-6 && a[2] < b[5] - 1e-6 && b[2] < a[5] - 1e-6;

/** Uniform-grid candidate pairs for AABB overlap. Returns [[i,j], ...] with i < j into the given array. */
CAD.spatialPairs = function (items, getAABB, cellSize) {
  const n = items.length;
  if (n < 2) return [];
  if (n <= 24) {
    const pairs = [];
    for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++) pairs.push([a, b]);
    return pairs;
  }
  let cs = cellSize;
  if (!(cs > 0)) {
    let sum = 0;
    for (let i = 0; i < n; i++) {
      const a = getAABB(items[i]);
      sum += Math.max(a[3] - a[0], a[4] - a[1], a[5] - a[2], 1);
    }
    cs = Math.max(20, sum / n);
  }
  const cells = new Map();
  const key = (ix, iy, iz) => ix + ',' + iy + ',' + iz;
  for (let i = 0; i < n; i++) {
    const a = getAABB(items[i]);
    const x0 = Math.floor(a[0] / cs), y0 = Math.floor(a[1] / cs), z0 = Math.floor(a[2] / cs);
    const x1 = Math.floor(a[3] / cs), y1 = Math.floor(a[4] / cs), z1 = Math.floor(a[5] / cs);
    for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) for (let z = z0; z <= z1; z++) {
      const k = key(x, y, z);
      let L = cells.get(k); if (!L) { L = []; cells.set(k, L); }
      L.push(i);
    }
  }
  const seen = new Set(), pairs = [];
  cells.forEach(L => {
    for (let a = 0; a < L.length; a++) for (let b = a + 1; b < L.length; b++) {
      const i = L[a], j = L[b], lo = Math.min(i, j), hi = Math.max(i, j), pk = lo + ':' + hi;
      if (seen.has(pk)) continue;
      seen.add(pk);
      pairs.push([lo, hi]);
    }
  });
  return pairs;
};

/**
 * Interference report. Exact solids use boolean box volumes; any pair involving a mesh
 * (exact===false) uses AABB overlap volume and is flagged { coarse: true }.
 */
CAD.interference = function (M, tol) {
  tol = tol === undefined ? 1 : tol;
  const I = M.insts.slice();
  if (I.length < 2) return [];
  I.forEach(i => CAD.instBoxes(M, i));
  const exactOf = i => M.defs.get(i.def).solid.exact !== false;
  const pairs = CAD.spatialPairs(I, i => i._ab);
  const res = [];
  for (let p = 0; p < pairs.length; p++) {
    const ia = I[pairs[p][0]], ib = I[pairs[p][1]];
    if (!ov(ia._ab, ib._ab)) continue;
    const ea = exactOf(ia), eb = exactOf(ib);
    if (ea && eb) {
      let v = 0;
      for (const A of ia._wb) {
        if (!ov(A, ib._ab)) continue;
        for (const B of ib._wb) v += CAD.boxInter(A, B);
      }
      if (v > tol) res.push({ a: ia.def + '#' + ia.qtyIdx, b: ib.def + '#' + ib.qtyIdx, vol: v, coarse: false });
    } else {
      const A = ia._ab, B = ib._ab;
      const v = CAD.boxInter(A, B);
      const va = CAD.boxVol(A), vb = CAD.boxVol(B);
      const minV = Math.min(va, vb);
      /* Skip trivial AABB kisses; piercing joints (dowel through ring) stay below severe. */
      const thresh = Math.max(tol * 50, 0.02 * minV);
      if (v <= thresh) continue;
      const frac = v / Math.max(1, minV);
      const fracLarge = v / Math.max(1, Math.max(va, vb));
      /* Nested assembly (bulb inside shade) has high frac of the small AABB but low of the large — warn only.
         Two bodies occupying the same space overlap a large fraction of BOTH AABBs. */
      const severe = frac >= 0.4 && fracLarge >= 0.22;
      res.push({ a: ia.def + '#' + ia.qtyIdx, b: ib.def + '#' + ib.qtyIdx, vol: v, coarse: true, severe, frac });
    }
  }
  return res;
};

/**
 * Exact-solid pairs that nearly touch (AABB padded by `gap` mm) but neither part has
 * documented joinery (labeled feat or fill:true cut). Soft assembly without tags.
 */
CAD.unlabeledContacts = function (M, gap) {
  gap = gap === undefined ? 2 : gap;
  const I = M.insts.filter(i => {
    const d = M.defs.get(i.def);
    return d && d.solid && d.solid.exact !== false;
  });
  if (I.length < 2) return [];
  I.forEach(i => CAD.instBoxes(M, i));
  const hasJoinery = d => {
    const feats = d.solid.feat || [];
    return feats.some(f => (f.label && String(f.label).trim()) || (f.kind === 'cut' && f.fill) || (f.kind === 'add' && f.tag));
  };
  const pad = (a, g) => [a[0] - g, a[1] - g, a[2] - g, a[3] + g, a[4] + g, a[5] + g];
  const pairs = CAD.spatialPairs(I, i => pad(i._ab, gap), Math.max(20, gap * 4));
  const res = [], seen = new Set();
  for (let p = 0; p < pairs.length; p++) {
    const ia = I[pairs[p][0]], ib = I[pairs[p][1]];
    if (ia.def === ib.def) continue;
    const da = M.defs.get(ia.def), db = M.defs.get(ib.def);
    if (!ov(pad(ia._ab, gap), ib._ab) && !ov(ia._ab, pad(ib._ab, gap))) continue;
    if (hasJoinery(da) || hasJoinery(db)) continue;
    /* Prefer pairs that actually share a face/volume, not distant padded false positives */
    const v = CAD.boxInter(pad(ia._ab, gap), pad(ib._ab, gap));
    if (!(v > 0)) continue;
    const key = [ia.def, ib.def].sort().join('|');
    if (seen.has(key)) continue;
    seen.add(key);
    res.push({ a: ia.def, b: ib.def, vol: v });
  }
  return res;
};

/* every cut feature flagged fill:true must be completely filled by mating parts (exact solids only) */
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
