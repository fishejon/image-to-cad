/* geo.js — geometry kit, materials, STL + ZIP writers. Units: millimetres, Z-up. */
(function (root) {
'use strict';
const CAD = root.CAD = root.CAD || {};
const T = root.THREE;
const D2R = Math.PI / 180;

/* ---------------- materials (visual + density kg/m3) ---------------- */
CAD.MATS = {
  al:      { name: '6063-T5 aluminium',      color: 0xc4cad1, metal: .78, rough: .40, rho: 2700 },
  alBlk:   { name: 'Black anodised Al 6061', color: 0x2a2d33, metal: .55, rough: .48, rho: 2700 },
  alRaw:   { name: '6061-T6 aluminium plate',color: 0xaeb4bb, metal: .70, rough: .52, rho: 2700 },
  steel:   { name: 'Mild steel (zinc)',      color: 0x949ca6, metal: .85, rough: .42, rho: 7850 },
  steelD:  { name: 'Blackened steel',        color: 0x33383f, metal: .70, rough: .50, rho: 7850 },
  plate:   { name: 'A36 steel plate',        color: 0x7b838c, metal: .80, rough: .55, rho: 7850 },
  ss:      { name: '304 stainless',          color: 0xc9ced4, metal: .92, rough: .28, rho: 8000 },
  rail:    { name: 'Linear rail (steel)',    color: 0xb9c1cb, metal: .92, rough: .26, rho: 7850 },
  blk:     { name: 'Bearing block (steel)',  color: 0x56606c, metal: .75, rough: .38, rho: 7850 },
  seal:    { name: 'End seal (PA)',          color: 0x1b1d20, metal: .05, rough: .80, rho: 1150 },
  screw:   { name: 'Ground ballscrew',       color: 0xd9dee4, metal: .96, rough: .22, rho: 7850 },
  motor:   { name: 'Motor laminations',      color: 0x1f2227, metal: .35, rough: .60, rho: 5200 },
  motorCap:{ name: 'Motor end caps',         color: 0xb4b9bf, metal: .85, rough: .35, rho: 2700 },
  copper:  { name: 'Copper (C101)',          color: 0xb9743a, metal: .92, rough: .30, rho: 8900 },
  brass:   { name: 'Brass',                  color: 0xc9a43a, metal: .90, rough: .30, rho: 8500 },
  peek:    { name: 'PEEK',                   color: 0xcdac66, metal: 0,   rough: .55, rho: 1320 },
  rubber:  { name: 'Rubber / PVC',           color: 0x17181a, metal: 0,   rough: .90, rho: 1200 },
  printed: { name: 'PETG-CF (printed)',      color: 0xf0661f, metal: .05, rough: .62, rho: 1300 },
  printedB:{ name: 'ASA (printed)',          color: 0x26282b, metal: .05, rough: .60, rho: 1070 },
  acrylic: { name: 'Polycarbonate',          color: 0x9fd2e8, metal: 0,   rough: .12, rho: 1200, alpha: .35 },
  pcb:     { name: 'PCB',                    color: 0x1b6e3d, metal: .1,  rough: .5,  rho: 1850 },
  paintRed:{ name: 'Painted steel (red)',    color: 0xa5231f, metal: .10, rough: .5, rho: 7850 },
  paintGry:{ name: 'Painted steel (grey)',   color: 0xcfd5da, metal: .25, rough: .50, rho: 7850 },
  paintBlu:{ name: 'Painted steel (blue)',   color: 0x2d5ea6, metal: .30, rough: .45, rho: 7850 },
  bottle:  { name: 'Gas cylinder (steel)',   color: 0x2b6f55, metal: .35, rough: .45, rho: 7850 },
  wire:    { name: 'Cu-coated wire',         color: 0xb26a2c, metal: .85, rough: .40, rho: 7850 },
  white:   { name: 'ABS white',              color: 0xe8eaec, metal: 0,   rough: .55, rho: 1050 },
  ledR:    { name: 'Indicator red',          color: 0xff3b30, metal: 0,   rough: .3,  rho: 1100, emis: 0x661510 },
  ledA:    { name: 'Indicator amber',        color: 0xffb020, metal: 0,   rough: .3,  rho: 1100, emis: 0x664400 },
  ledG:    { name: 'Indicator green',        color: 0x2ecc71, metal: 0,   rough: .3,  rho: 1100, emis: 0x0b4a24 },
  glass:   { name: 'Glass / lens',           color: 0x25384a, metal: .2,  rough: .08, rho: 2500 },
};

/* ---------------- low-level helpers ---------------- */
function strip(g) {
  const n = g.index ? g.toNonIndexed() : g;
  const out = new T.BufferGeometry();
  out.setAttribute('position', new T.BufferAttribute(new Float32Array(n.attributes.position.array), 3));
  return out;
}
function volume(g) {
  const p = g.attributes.position.array; let v = 0;
  for (let i = 0; i < p.length; i += 9) {
    v += p[i] * (p[i + 4] * p[i + 8] - p[i + 5] * p[i + 7])
       - p[i + 1] * (p[i + 3] * p[i + 8] - p[i + 5] * p[i + 6])
       + p[i + 2] * (p[i + 3] * p[i + 7] - p[i + 4] * p[i + 6]);
  }
  return v / 6;
}
function flipWinding(g) {
  const p = g.attributes.position.array;
  for (let i = 0; i < p.length; i += 9) for (let k = 0; k < 3; k++) { const t = p[i + 3 + k]; p[i + 3 + k] = p[i + 6 + k]; p[i + 6 + k] = t; }
}
function orient(g) { if (volume(g) < 0) flipWinding(g); return g; }
function dropDegenerate(g) {
  const p = g.attributes.position.array, out = [];
  for (let i = 0; i < p.length; i += 9) {
    const ux = p[i + 3] - p[i], uy = p[i + 4] - p[i + 1], uz = p[i + 5] - p[i + 2];
    const vx = p[i + 6] - p[i], vy = p[i + 7] - p[i + 1], vz = p[i + 8] - p[i + 2];
    const cx = uy * vz - uz * vy, cy = uz * vx - ux * vz, cz = ux * vy - uy * vx;
    if (cx * cx + cy * cy + cz * cz > 1e-10) for (let k = 0; k < 9; k++) out.push(p[i + k]);
  }
  const r = new T.BufferGeometry();
  r.setAttribute('position', new T.BufferAttribute(new Float32Array(out), 3));
  return r;
}
function creaseNormals(g, angleDeg) {
  const pos = g.attributes.position.array, nT = pos.length / 9;
  const fn = new Float32Array(nT * 3), keys = new Array(nT * 3), map = new Map();
  const q = v => Math.round(v * 500);
  for (let t = 0; t < nT; t++) {
    const o = t * 9;
    const ux = pos[o + 3] - pos[o], uy = pos[o + 4] - pos[o + 1], uz = pos[o + 5] - pos[o + 2];
    const vx = pos[o + 6] - pos[o], vy = pos[o + 7] - pos[o + 1], vz = pos[o + 8] - pos[o + 2];
    let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    const l = Math.hypot(nx, ny, nz) || 1; nx /= l; ny /= l; nz /= l;
    fn[t * 3] = nx; fn[t * 3 + 1] = ny; fn[t * 3 + 2] = nz;
    for (let k = 0; k < 3; k++) {
      const kk = q(pos[o + 3 * k]) + ',' + q(pos[o + 3 * k + 1]) + ',' + q(pos[o + 3 * k + 2]);
      keys[t * 3 + k] = kk; let a = map.get(kk); if (!a) { a = []; map.set(kk, a); } a.push(t);
    }
  }
  const cosT = Math.cos(angleDeg * D2R), out = new Float32Array(pos.length);
  for (let t = 0; t < nT; t++) {
    const nx = fn[t * 3], ny = fn[t * 3 + 1], nz = fn[t * 3 + 2];
    for (let k = 0; k < 3; k++) {
      const list = map.get(keys[t * 3 + k]); let sx = 0, sy = 0, sz = 0;
      for (let j = 0; j < list.length; j++) {
        const u = list[j], d = fn[u * 3] * nx + fn[u * 3 + 1] * ny + fn[u * 3 + 2] * nz;
        if (d >= cosT) { sx += fn[u * 3]; sy += fn[u * 3 + 1]; sz += fn[u * 3 + 2]; }
      }
      const l = Math.hypot(sx, sy, sz) || 1;
      out[t * 9 + k * 3] = sx / l; out[t * 9 + k * 3 + 1] = sy / l; out[t * 9 + k * 3 + 2] = sz / l;
    }
  }
  g.setAttribute('normal', new T.BufferAttribute(out, 3));
  return g;
}
function mergeGeoms(list) {
  let n = 0; list.forEach(g => n += g.attributes.position.array.length);
  const a = new Float32Array(n); let o = 0;
  list.forEach(g => { a.set(g.attributes.position.array, o); o += g.attributes.position.array.length; });
  const r = new T.BufferGeometry(); r.setAttribute('position', new T.BufferAttribute(a, 3)); return r;
}
function bbox(g) { g.computeBoundingBox(); return g.boundingBox.clone(); }

/* axis → rotation taking local +Z onto the axis */
function axisMat(ax) {
  const m = new T.Matrix4();
  switch (ax) {
    case '+x': m.makeRotationY(Math.PI / 2); break;
    case '-x': m.makeRotationY(-Math.PI / 2); break;
    case '+y': m.makeRotationX(-Math.PI / 2); break;
    case '-y': m.makeRotationX(Math.PI / 2); break;
    case '-z': m.makeRotationX(Math.PI); break;
    default: m.identity();
  }
  return m;
}
function transl(p) { return new T.Matrix4().makeTranslation(p[0], p[1], p[2]); }

function mkShape(pts, holes) {
  const s = new T.Shape(); pts.forEach((p, i) => i ? s.lineTo(p[0], p[1]) : s.moveTo(p[0], p[1]));
  (holes || []).forEach(h => {
    const path = new T.Path();
    if (h.r) { path.absarc(h.c[0], h.c[1], h.r, 0, Math.PI * 2, true); }
    else { h.poly.forEach((p, i) => i ? path.lineTo(p[0], p[1]) : path.moveTo(p[0], p[1])); }
    s.holes.push(path);
  });
  return s;
}
function rrectPts(x0, y0, x1, y1, r, seg) {
  seg = seg || 6; const pts = [];
  if (!r) return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
  const c = [[x1 - r, y0 + r, -90], [x1 - r, y1 - r, 0], [x0 + r, y1 - r, 90], [x0 + r, y0 + r, 180]];
  c.forEach(([cx, cy, a0]) => { for (let i = 0; i <= seg; i++) { const a = (a0 + 90 * i / seg) * D2R; pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); } });
  return pts;
}
function chamferPts(w, h, c) { const x = w / 2, y = h / 2; return [[-x + c, -y], [x - c, -y], [x, -y + c], [x, y - c], [x - c, y], [-x + c, y], [-x, y - c], [-x, -y + c]]; }
CAD.rrectPts = rrectPts; CAD.chamferPts = chamferPts;

/* T-slot extrusion profile (nx × ny modules of 40 mm, 10 mm slot) */
function tslotProfile(nx, ny) {
  const hx = 20 * nx, hy = 20 * ny;
  const notch = [[-5, 0], [-5, 3], [-11, 3], [-11, 6.5], [-5.5, 11.5], [5.5, 11.5], [11, 6.5], [11, 3], [5, 3], [5, 0]];
  const sides = [
    { S: [hx, hy], D: [-1, 0], I: [0, -1], n: nx },
    { S: [-hx, hy], D: [0, -1], I: [1, 0], n: ny },
    { S: [-hx, -hy], D: [1, 0], I: [0, 1], n: nx },
    { S: [hx, -hy], D: [0, 1], I: [-1, 0], n: ny },
  ];
  const pts = [];
  sides.forEach(s => {
    pts.push([s.S[0], s.S[1]]);
    for (let k = 0; k < s.n; k++) {
      const tc = 20 + 40 * k;
      notch.forEach(([tau, d]) => { const t = tc + tau; pts.push([s.S[0] + s.D[0] * t + s.I[0] * d, s.S[1] + s.D[1] * t + s.I[1] * d]); });
    }
  });
  const holes = [];
  for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) holes.push({ c: [-hx + 20 + 40 * i, -hy + 20 + 40 * j], r: 4.2 });
  return { pts, holes };
}
CAD.tslotProfile = tslotProfile;

/* ---------------- Builder: collects {geometry, material-key} items in a part-local frame ---------------- */
class Builder {
  constructor() { this.items = []; }
  _push(g, m, mat) {
    g = strip(g); g = dropDegenerate(g); orient(g);
    if (mat) g.applyMatrix4(mat);
    this.items.push({ g, m }); return this;
  }
  bb(p0, p1, m) {
    const s = [Math.abs(p1[0] - p0[0]), Math.abs(p1[1] - p0[1]), Math.abs(p1[2] - p0[2])];
    const c = [(p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2];
    return this._push(new T.BoxGeometry(s[0], s[1], s[2]), m, transl(c));
  }
  box(c, s, m) { return this._push(new T.BoxGeometry(s[0], s[1], s[2]), m, transl(c)); }
  cyl(p, ax, len, r, m, seg) { return this.cone(p, ax, len, r, r, m, seg); }
  cone(p, ax, len, r0, r1, m, seg) {
    const g = new T.CylinderGeometry(r1, r0, len, seg || 32, 1, false); g.rotateX(Math.PI / 2); g.translate(0, 0, len / 2);
    return this._push(g, m, transl(p).multiply(axisMat(ax)));
  }
  /* revolve closed profile [[r,z],...] around the axis through p */
  rev(p, ax, prof, m, seg) {
    const pts = prof.map(q => new T.Vector2(q[0], q[1]));
    if (pts[0].distanceTo(pts[pts.length - 1]) > 1e-9) pts.push(pts[0].clone());
    const g = new T.LatheGeometry(pts, seg || 32); g.rotateX(Math.PI / 2);
    return this._push(g, m, transl(p).multiply(axisMat(ax)));
  }
  tube(p, ax, len, ro, ri, m, seg) { return this.rev(p, ax, [[ri, 0], [ro, 0], [ro, len], [ri, len]], m, seg); }
  /* extrude 2-D profile: plane 'xy'|'xz'|'yz'; range [w0,w1] along plane normal; profile coords (u,v) */
  ext(plane, pts, w0, w1, m, holes, seg) {
    const depth = w1 - w0;
    const g = new T.ExtrudeGeometry(mkShape(pts, holes), { depth, bevelEnabled: false, curveSegments: seg || 20, steps: 1 });
    let M = new T.Matrix4();
    if (plane === 'xy') M = transl([0, 0, w0]);
    else if (plane === 'xz') { M.set(1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1); M = transl([0, w1, 0]).multiply(M); }
    else { M.set(0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1); M = transl([w0, 0, 0]).multiply(M); }
    return this._push(g, m, M);
  }
  /* rectangular plate in local XY, thickness +Z [z0, z0+t], centred in XY */
  plate(w, h, t, holes, m, o) {
    o = o || {}; const z0 = o.z0 || 0, cx = o.cx || 0, cy = o.cy || 0;
    return this.ext('xy', rrectPts(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, o.r || 0, 5), z0, z0 + t, m, holes, o.seg);
  }
  /* hollow shell box (outer w,d,h centred XY, z from 0), wall t, open toward +Z, then rotated so opening faces `open` */
  shell(c, size, t, open, m) {
    const [w, d, h] = size, x = w / 2, y = d / 2, ix = x - t, iy = y - t, tris = [];
    const Q = (a, b, cc, dd, n) => { tris.push([a, b, cc, n], [a, cc, dd, n]); };
    // outer
    Q([-x, -y, 0], [x, -y, 0], [x, y, 0], [-x, y, 0], [0, 0, -1]);
    Q([-x, -y, 0], [x, -y, 0], [x, -y, h], [-x, -y, h], [0, -1, 0]);
    Q([x, -y, 0], [x, y, 0], [x, y, h], [x, -y, h], [1, 0, 0]);
    Q([x, y, 0], [-x, y, 0], [-x, y, h], [x, y, h], [0, 1, 0]);
    Q([-x, y, 0], [-x, -y, 0], [-x, -y, h], [-x, y, h], [-1, 0, 0]);
    // top ring
    Q([-x, -y, h], [x, -y, h], [ix, -iy, h], [-ix, -iy, h], [0, 0, 1]);
    Q([x, -y, h], [x, y, h], [ix, iy, h], [ix, -iy, h], [0, 0, 1]);
    Q([x, y, h], [-x, y, h], [-ix, iy, h], [ix, iy, h], [0, 0, 1]);
    Q([-x, y, h], [-x, -y, h], [-ix, -iy, h], [-ix, iy, h], [0, 0, 1]);
    // inner (normals point into cavity)
    Q([-ix, -iy, t], [ix, -iy, t], [ix, iy, t], [-ix, iy, t], [0, 0, 1]);
    Q([-ix, -iy, t], [ix, -iy, t], [ix, -iy, h], [-ix, -iy, h], [0, 1, 0]);
    Q([ix, -iy, t], [ix, iy, t], [ix, iy, h], [ix, -iy, h], [-1, 0, 0]);
    Q([ix, iy, t], [-ix, iy, t], [-ix, iy, h], [ix, iy, h], [0, -1, 0]);
    Q([-ix, iy, t], [-ix, -iy, t], [-ix, -iy, h], [-ix, iy, h], [1, 0, 0]);
    const arr = [];
    tris.forEach(([a, b, cc, n]) => {
      const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2], vx = cc[0] - a[0], vy = cc[1] - a[1], vz = cc[2] - a[2];
      const cx = uy * vz - uz * vy, cy = uz * vx - ux * vz, cz = ux * vy - uy * vx;
      if (cx * n[0] + cy * n[1] + cz * n[2] >= 0) arr.push(...a, ...b, ...cc); else arr.push(...a, ...cc, ...b);
    });
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(new Float32Array(arr), 3));
    return this._push(g, m, transl(c).multiply(axisMat(open)));
  }
  /* round/capsule tube swept along polyline of [x,y,z] with end caps */
  sweep(pts, r, m, radial) {
    radial = radial || 14; const n = pts.length, P = pts.map(p => new T.Vector3(p[0], p[1], p[2]));
    const tang = P.map((p, i) => (P[Math.min(n - 1, i + 1)].clone().sub(P[Math.max(0, i - 1)])).normalize());
    let nrm = new T.Vector3(0, 0, 1); if (Math.abs(tang[0].z) > .9) nrm.set(1, 0, 0);
    nrm = nrm.sub(tang[0].clone().multiplyScalar(nrm.dot(tang[0]))).normalize();
    const rings = [];
    for (let i = 0; i < n; i++) {
      if (i) { const prev = tang[i - 1], cur = tang[i], axis = new T.Vector3().crossVectors(prev, cur); const s = axis.length();
        if (s > 1e-6) { nrm.applyAxisAngle(axis.normalize(), Math.asin(Math.min(1, s))); } }
      nrm.sub(tang[i].clone().multiplyScalar(nrm.dot(tang[i]))).normalize();
      const bn = new T.Vector3().crossVectors(tang[i], nrm), ring = [];
      for (let k = 0; k < radial; k++) { const a = k / radial * Math.PI * 2; ring.push(P[i].clone().addScaledVector(nrm, Math.cos(a) * r).addScaledVector(bn, Math.sin(a) * r)); }
      rings.push(ring);
    }
    const arr = [], push = (a, b, c) => arr.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z);
    for (let i = 0; i < n - 1; i++) for (let k = 0; k < radial; k++) {
      const k2 = (k + 1) % radial, a = rings[i][k], b = rings[i][k2], c = rings[i + 1][k2], d = rings[i + 1][k];
      push(a, b, c); push(a, c, d);
    }
    for (let k = 0; k < radial; k++) { const k2 = (k + 1) % radial; push(P[0], rings[0][k2], rings[0][k]); push(P[n - 1], rings[n - 1][k], rings[n - 1][k2]); }
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(new Float32Array(arr), 3));
    return this._push(g, m, null);
  }
  /* socket-head cap screw along +Z, head bearing face at z=0, shank to -len */
  screw(d, len, hd, hh, m) {
    const r = d / 2, h = hd / 2, rs = Math.max(r * .55, 1);
    return this.rev([0, 0, 0], '+z', [[0, -len], [r - .4, -len], [r, -len + .6], [r, 0], [h, 0], [h, hh - .4], [h - .4, hh], [rs, hh], [rs, hh - hh * .55], [0, hh - hh * .55]], m, 20);
  }
  /* merge several builders' items */
  absorb(b) { this.items.push(...b.items); return this; }
}
CAD.Builder = Builder;

/* ---------------- finalize: merge per material, smooth, bbox, volume ---------------- */
CAD.finalizeItems = function (items, defMat) {
  const byMat = new Map();
  items.forEach(it => { const k = it.m || defMat; if (!byMat.has(k)) byMat.set(k, []); byMat.get(k).push(it.g); });
  const parts = []; let vol = 0; let tris = 0; const box = new T.Box3();
  byMat.forEach((list, k) => {
    const g = mergeGeoms(list); creaseNormals(g, 38);
    g.computeBoundingBox(); box.union(g.boundingBox);
    const v = volume(g); vol += v; tris += g.attributes.position.count / 3;
    parts.push({ m: k, g, vol: v });
  });
  return { parts, vol, tris, box };
};
CAD.volume = volume; CAD.mergeGeoms = mergeGeoms; CAD.creaseNormals = creaseNormals; CAD.axisMat = axisMat;

/* ---------------- STL writer (binary) ---------------- */
CAD.stlBinary = function (triArrays) {
  // triArrays: array of Float32Array (9 floats per triangle, already in output coordinates)
  let n = 0; triArrays.forEach(a => n += a.length / 9);
  const buf = new ArrayBuffer(84 + n * 50), dv = new DataView(buf);
  const head = 'Metal printer CAD export — mm, Z-up';
  for (let i = 0; i < head.length && i < 80; i++) dv.setUint8(i, head.charCodeAt(i) & 0x7f);
  dv.setUint32(80, n, true); let o = 84;
  triArrays.forEach(a => {
    for (let i = 0; i < a.length; i += 9) {
      const ux = a[i + 3] - a[i], uy = a[i + 4] - a[i + 1], uz = a[i + 5] - a[i + 2];
      const vx = a[i + 6] - a[i], vy = a[i + 7] - a[i + 1], vz = a[i + 8] - a[i + 2];
      let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx; const l = Math.hypot(nx, ny, nz) || 1;
      dv.setFloat32(o, nx / l, true); dv.setFloat32(o + 4, ny / l, true); dv.setFloat32(o + 8, nz / l, true);
      for (let k = 0; k < 9; k++) dv.setFloat32(o + 12 + k * 4, a[i + k], true);
      dv.setUint16(o + 48, 0, true); o += 50;
    }
  });
  return new Uint8Array(buf);
};
CAD.stlParse = function (u8) {
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength), n = dv.getUint32(80, true), out = new Float32Array(n * 9);
  for (let t = 0; t < n; t++) for (let k = 0; k < 9; k++) out[t * 9 + k] = dv.getFloat32(84 + t * 50 + 12 + k * 4, true);
  return out;
};

/* ---------------- ZIP writer (store) ---------------- */
const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
function crc32(u8) { let c = 0xFFFFFFFF; for (let i = 0; i < u8.length; i++) c = CRC[(c ^ u8[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
CAD.zip = function (files) {
  const enc = new TextEncoder(), chunks = [], central = []; let off = 0;
  const d = new Date(), dt = ((d.getFullYear() - 1980) << 9 | (d.getMonth() + 1) << 5 | d.getDate()) & 0xffff, tm = (d.getHours() << 11 | d.getMinutes() << 5 | (d.getSeconds() >> 1)) & 0xffff;
  files.forEach(f => {
    const name = enc.encode(f.name), data = typeof f.data === 'string' ? enc.encode(f.data) : f.data, crc = crc32(data);
    const lh = new DataView(new ArrayBuffer(30)); lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true); lh.setUint16(8, 0, true);
    lh.setUint16(10, tm, true); lh.setUint16(12, dt, true); lh.setUint32(14, crc, true); lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true); lh.setUint16(26, name.length, true); lh.setUint16(28, 0, true);
    chunks.push(new Uint8Array(lh.buffer), name, data);
    const ch = new DataView(new ArrayBuffer(46)); ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true); ch.setUint16(10, 0, true);
    ch.setUint16(12, tm, true); ch.setUint16(14, dt, true); ch.setUint32(16, crc, true); ch.setUint32(20, data.length, true); ch.setUint32(24, data.length, true); ch.setUint16(28, name.length, true); ch.setUint32(42, off, true);
    central.push(new Uint8Array(ch.buffer), name);
    off += 30 + name.length + data.length;
  });
  let cs = 0; central.forEach(c => cs += c.length);
  const e = new DataView(new ArrayBuffer(22)); e.setUint32(0, 0x06054b50, true); e.setUint16(8, files.length, true); e.setUint16(10, files.length, true); e.setUint32(12, cs, true); e.setUint32(16, off, true);
  const all = chunks.concat(central, [new Uint8Array(e.buffer)]); let total = 0; all.forEach(c => total += c.length);
  const out = new Uint8Array(total); let p = 0; all.forEach(c => { out.set(c, p); p += c.length; }); return out;
};
CAD.unzipList = function (u8) { // minimal reader for tests
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength); let eo = u8.length - 22; while (eo > 0 && dv.getUint32(eo, true) !== 0x06054b50) eo--;
  const n = dv.getUint16(eo + 10, true); let p = dv.getUint32(eo + 16, true); const res = [];
  for (let i = 0; i < n; i++) { const nl = dv.getUint16(p + 28, true), xl = dv.getUint16(p + 30, true), cl = dv.getUint16(p + 32, true), size = dv.getUint32(p + 24, true), crc = dv.getUint32(p + 16, true), lo = dv.getUint32(p + 42, true);
    const name = new TextDecoder().decode(u8.subarray(p + 46, p + 46 + nl)); const lnl = dv.getUint16(lo + 26, true), lxl = dv.getUint16(lo + 28, true);
    const data = u8.subarray(lo + 30 + lnl + lxl, lo + 30 + lnl + lxl + size); res.push({ name, size, crcOk: crc32(data) === crc, data }); p += 46 + nl + xl + cl; }
  return res;
};
})(typeof globalThis !== 'undefined' ? globalThis : window);
