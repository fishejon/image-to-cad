/* curves.js — Catmull paths, section rings, sweep / pillow / panel mesh builders.
   Units mm, Z-up. Consumed by spec mesh prims (sweep, pillow, panel). */
(function (root) {
'use strict';
const CAD = root.CAD = root.CAD || {};
const T = root.THREE;
const TRI_BUDGET = 60000;
const DEFAULT_TOL = 0.15;

function v3(a) { return new T.Vector3(a[0], a[1], a[2]); }
function assertFinite(n, label) {
  if (typeof n !== 'number' || !isFinite(n)) throw new Error((label || 'value') + ' must be a finite number');
  return n;
}

/* ---------- Catmull-Rom (centripetal) ---------- */
function catmullRom(pts, alpha) {
  alpha = alpha == null ? 0.5 : alpha;
  const P = pts.map(p => v3(p));
  if (P.length < 2) throw new Error('path needs at least 2 points');
  // reflected phantoms
  const p0 = P[0].clone().multiplyScalar(2).sub(P[1]);
  const pn = P[P.length - 1].clone().multiplyScalar(2).sub(P[P.length - 2]);
  const C = [p0].concat(P).concat([pn]);
  function tj(ti, a, b) { return Math.pow(a.distanceTo(b), alpha) + ti; }
  const segs = [];
  for (let i = 1; i < C.length - 2; i++) {
    const p1 = C[i], p2 = C[i + 1], p0s = C[i - 1], p3 = C[i + 2];
    const t0 = 0, t1 = tj(t0, p0s, p1), t2 = tj(t1, p1, p2), t3 = tj(t2, p2, p3);
    segs.push({ p0: p0s, p1, p2, p3, t0, t1, t2, t3 });
  }
  return {
    nSegs: segs.length,
    eval(si, u) { // segment index, u in [0,1] within segment
      const s = segs[si];
      const t = s.t1 + (s.t2 - s.t1) * Math.max(0, Math.min(1, u));
      const A1 = s.p0.clone().lerp(s.p1, (t - s.t0) / (s.t1 - s.t0 || 1e-12));
      const A2 = s.p1.clone().lerp(s.p2, (t - s.t1) / (s.t2 - s.t1 || 1e-12));
      const A3 = s.p2.clone().lerp(s.p3, (t - s.t2) / (s.t3 - s.t2 || 1e-12));
      const B1 = A1.clone().lerp(A2, (t - s.t0) / (s.t2 - s.t0 || 1e-12));
      const B2 = A2.clone().lerp(A3, (t - s.t1) / (s.t3 - s.t1 || 1e-12));
      return B1.clone().lerp(B2, (t - s.t1) / (s.t2 - s.t1 || 1e-12));
    }
  };
}

function polylinePath(pts) {
  const P = pts.map(p => v3(p));
  return {
    nSegs: Math.max(1, P.length - 1),
    eval(si, u) {
      const i = Math.min(si, P.length - 2);
      return P[i].clone().lerp(P[i + 1], Math.max(0, Math.min(1, u)));
    }
  };
}

function arcLengthTable(path, samplesPerSeg) {
  samplesPerSeg = samplesPerSeg || 32;
  const samples = [];
  let dist = 0, prev = null;
  for (let si = 0; si < path.nSegs; si++) {
    for (let k = 0; k <= samplesPerSeg; k++) {
      if (si > 0 && k === 0) continue;
      const u = k / samplesPerSeg;
      const p = path.eval(si, u);
      if (prev) dist += p.distanceTo(prev);
      samples.push({ s: dist, si, u, p: p.clone() });
      prev = p;
    }
  }
  const total = dist || 1e-9;
  return {
    total,
    at(t) {
      t = Math.max(0, Math.min(1, t));
      const target = t * total;
      let lo = 0, hi = samples.length - 1;
      while (lo < hi) { const mid = (lo + hi) >> 1; if (samples[mid].s < target) lo = mid + 1; else hi = mid; }
      const b = samples[lo], a = samples[Math.max(0, lo - 1)];
      const denom = (b.s - a.s) || 1e-12;
      const f = (target - a.s) / denom;
      const p = a.p.clone().lerp(b.p, f);
      // tangent from nearby samples
      const i0 = Math.max(0, lo - 1), i1 = Math.min(samples.length - 1, lo + 1);
      const tang = samples[i1].p.clone().sub(samples[i0].p);
      if (tang.lengthSq() < 1e-18) tang.set(0, 0, 1); else tang.normalize();
      return { p, T: tang, s: target };
    }
  };
}

function pickStations(table, tol, forceTs, maxN) {
  tol = tol || DEFAULT_TOL;
  maxN = maxN || 400;
  forceTs = (forceTs || []).slice().sort((a, b) => a - b);
  const out = [0];
  let t = 0;
  const minStep = Math.min(0.002, 1 / 200), maxStep = 0.25;
  while (t < 1 - 1e-9) {
    const a = table.at(t), b = table.at(Math.min(1, t + 0.01));
    const chord = a.p.distanceTo(b.p) || 1e-6;
    // crude kappa from angle change
    const c = table.at(Math.min(1, t + 0.02));
    const d1 = b.T.angleTo(a.T), d2 = c.T.angleTo(b.T);
    const kappa = Math.max(d1, d2) / (chord || 1e-3);
    let ds = Math.sqrt(Math.max(1e-8, 8 * tol / Math.max(kappa, 1e-6)));
    ds = Math.max(minStep * table.total, Math.min(maxStep * table.total, ds));
    let nt = Math.min(1, t + ds / table.total);
    for (let i = 0; i < forceTs.length; i++) {
      if (forceTs[i] > t + 1e-9 && forceTs[i] < nt) { nt = forceTs[i]; break; }
    }
    if (nt <= t) nt = Math.min(1, t + minStep);
    out.push(nt);
    t = nt;
    if (out.length >= maxN) { if (out[out.length - 1] < 1) out.push(1); break; }
  }
  if (out[out.length - 1] < 1 - 1e-12) out.push(1);
  return out;
}

function upFrame(tan, up) {
  const Tg = tan.clone().normalize();
  const U = up.clone().normalize();
  let s = new T.Vector3().crossVectors(U, Tg);
  if (s.lengthSq() < 1e-10) {
    const alt = Math.abs(Tg.z) > 0.9 ? new T.Vector3(1, 0, 0) : new T.Vector3(0, 0, 1);
    s = new T.Vector3().crossVectors(alt, Tg);
  }
  s.normalize();
  const n = new T.Vector3().crossVectors(Tg, s).normalize();
  return { T: Tg, s, n };
}

function rmfFrames(stations) {
  // stations: [{p,T},...]
  const frames = [];
  let prev = null;
  for (let i = 0; i < stations.length; i++) {
    const Tg = stations[i].T.clone().normalize();
    if (!prev) {
      const up = Math.abs(Tg.z) > 0.9 ? new T.Vector3(1, 0, 0) : new T.Vector3(0, 0, 1);
      prev = upFrame(Tg, up);
      frames.push(prev);
      continue;
    }
    // keep previous s, re-orthogonalize (simplified RMF)
    let s = prev.s.clone().sub(Tg.clone().multiplyScalar(prev.s.dot(Tg)));
    if (s.lengthSq() < 1e-10) s = prev.n.clone().sub(Tg.clone().multiplyScalar(prev.n.dot(Tg)));
    s.normalize();
    const n = new T.Vector3().crossVectors(Tg, s).normalize();
    prev = { T: Tg, s, n };
    frames.push(prev);
  }
  return frames;
}

/* ---------- sections ---------- */
function sectionRing(sec, tol) {
  tol = tol || DEFAULT_TOL;
  const type = (sec && sec.type) || 'rrect';
  if (type === 'ellipse') {
    const w = assertFinite(sec.w, 'section.w'), h = assertFinite(sec.h, 'section.h');
    const n = Math.max(12, Math.min(64, Math.ceil(Math.PI * Math.max(w, h) / Math.max(tol * 8, 0.5))));
    const ring = [];
    for (let i = 0; i < n; i++) {
      const a = i / n * Math.PI * 2;
      ring.push({ x: (w / 2) * Math.cos(a), y: (h / 2) * Math.sin(a) });
    }
    return ring;
  }
  if (type === 'poly') {
    const pts = sec.pts || [];
    if (pts.length < 3) throw new Error('section.poly needs >= 3 pts');
    return pts.map(p => ({ x: p[0], y: p[1] }));
  }
  // rrect
  const w = assertFinite(sec.w != null ? sec.w : sec.width, 'section.w');
  const h = assertFinite(sec.h != null ? sec.h : sec.height, 'section.h');
  let r = sec.r != null ? sec.r : Math.min(w, h) * 0.15;
  r = Math.max(0, Math.min(r, Math.min(w, h) / 2 - 1e-6));
  if (r < 1e-6) {
    return [
      { x: -w / 2, y: -h / 2 }, { x: w / 2, y: -h / 2 },
      { x: w / 2, y: h / 2 }, { x: -w / 2, y: h / 2 }
    ];
  }
  const kf = Math.max(2, Math.min(8, Math.ceil((Math.PI / 2) / (2 * Math.acos(Math.max(-1, Math.min(1, 1 - tol / Math.max(r, 1e-6))))))));
  const hx = w / 2 - r, hy = h / 2 - r;
  const ring = [];
  const corners = [
    [hx, -hy, -Math.PI / 2, 0],
    [hx, hy, 0, Math.PI / 2],
    [-hx, hy, Math.PI / 2, Math.PI],
    [-hx, -hy, Math.PI, 3 * Math.PI / 2]
  ];
  corners.forEach(([cx, cy, a0, a1]) => {
    for (let k = 0; k <= kf; k++) {
      if (k === 0 && ring.length) continue;
      const a = a0 + (a1 - a0) * (k / kf);
      ring.push({ x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) });
    }
  });
  return ring;
}

function perimeter(ring) {
  let L = 0;
  for (let i = 0; i < ring.length; i++) {
    const a = ring[i], b = ring[(i + 1) % ring.length];
    L += Math.hypot(b.x - a.x, b.y - a.y);
  }
  return L || 1;
}

function stitchRings(rings, closed) {
  const pos = [], uv = [];
  const n = rings[0].length;
  const push = (a, b, c, ua, ub, uc) => {
    pos.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z);
    if (ua) uv.push(ua[0], ua[1], ub[0], ub[1], uc[0], uc[1]);
  };
  const S = 1 / 260;
  for (let i = 0; i < rings.length - 1; i++) {
    const A = rings[i], B = rings[i + 1];
    const u0 = A._u || 0, u1 = B._u || 0;
    for (let k = 0; k < n; k++) {
      const k2 = (k + 1) % n;
      const a = A[k], b = A[k2], c = B[k2], d = B[k];
      const va = k / n * A._perim * S, vb = k2 / n * A._perim * S;
      push(a, b, c, [u0 * S, va], [u0 * S, vb], [u1 * S, vb]);
      push(a, c, d, [u0 * S, va], [u1 * S, vb], [u1 * S, va]);
    }
  }
  if (closed && rings.length > 2) {
    const A = rings[rings.length - 1], B = rings[0];
    for (let k = 0; k < n; k++) {
      const k2 = (k + 1) % n;
      push(A[k], A[k2], B[k2]); push(A[k], B[k2], B[k]);
    }
  }
  return { pos, uv };
}

function capFan(ring, center, outward) {
  const pos = [];
  const n = ring.length;
  for (let k = 0; k < n; k++) {
    const a = ring[k], b = ring[(k + 1) % n];
    if (outward) pos.push(center.x, center.y, center.z, a.x, a.y, a.z, b.x, b.y, b.z);
    else pos.push(center.x, center.y, center.z, b.x, b.y, b.z, a.x, a.y, a.z);
  }
  return pos;
}

function taperAt(keyframes, t) {
  if (!keyframes || !keyframes.length) return { sw: 1, sh: 1 };
  const kf = keyframes.map(k => ({
    t: assertFinite(k.t != null ? k.t : k[0], 'taper.t'),
    sw: assertFinite(k.scaleW != null ? k.scaleW : (k[1] != null ? k[1] : 1), 'taper.sw'),
    sh: assertFinite(k.scaleH != null ? k.scaleH : (k[2] != null ? k[2] : k.scaleW != null ? k.scaleW : 1), 'taper.sh')
  })).sort((a, b) => a.t - b.t);
  if (t <= kf[0].t) return { sw: kf[0].sw, sh: kf[0].sh };
  if (t >= kf[kf.length - 1].t) return { sw: kf[kf.length - 1].sw, sh: kf[kf.length - 1].sh };
  for (let i = 0; i < kf.length - 1; i++) {
    if (t >= kf[i].t && t <= kf[i + 1].t) {
      const f = (t - kf[i].t) / (kf[i + 1].t - kf[i].t || 1e-12);
      return { sw: kf[i].sw + (kf[i + 1].sw - kf[i].sw) * f, sh: kf[i].sh + (kf[i + 1].sh - kf[i].sh) * f };
    }
  }
  return { sw: 1, sh: 1 };
}

function geomFrom(pos, uv) {
  if (pos.length / 9 > TRI_BUDGET) throw new Error('triangle budget exceeded (' + (pos.length / 9) + ' > ' + TRI_BUDGET + ')');
  for (let i = 0; i < pos.length; i++) if (!isFinite(pos[i])) throw new Error('NaN in mesh');
  const g = new T.BufferGeometry();
  g.setAttribute('position', new T.BufferAttribute(new Float32Array(pos), 3));
  if (uv && uv.length) g.setAttribute('uv', new T.BufferAttribute(new Float32Array(uv), 2));
  return g;
}

/* ---------- sweep ---------- */
CAD.buildSweepPrim = function (opts) {
  opts = opts || {};
  const pathPts = opts.path;
  if (!Array.isArray(pathPts) || pathPts.length < 2) throw new Error('sweep.path needs >= 2 points');
  for (let i = 0; i < pathPts.length; i++) {
    if (!Array.isArray(pathPts[i]) || pathPts[i].length < 3) throw new Error('path[' + i + '] must be [x,y,z]');
    pathPts[i].forEach((v, j) => assertFinite(v, 'path[' + i + '][' + j + ']'));
  }
  const tol = opts.tol != null ? opts.tol : DEFAULT_TOL;
  const curveKind = opts.curve || 'catmull';
  const path = curveKind === 'polyline' ? polylinePath(pathPts) : catmullRom(pathPts, 0.5);
  const table = arcLengthTable(path, 24);
  const force = (opts.taper || []).map(k => (k.t != null ? k.t : k[0]));
  const ts = pickStations(table, tol, force, 400);
  const unit = sectionRing(opts.section || { type: 'rrect', w: 20, h: 20, r: 2 }, tol);
  const perim0 = perimeter(unit);
  const upArr = opts.up || [0, 0, 1];
  const up = v3(upArr);
  const frameMode = opts.frame || 'up';
  const twist = ((opts.twist || 0) * Math.PI) / 180;
  const caps = opts.caps !== 'none';

  const samples = ts.map(t => Object.assign({ t }, table.at(t)));
  // fold guard
  for (let i = 1; i < samples.length - 1; i++) {
    const a = samples[i - 1], b = samples[i], c = samples[i + 1];
    const d1 = b.p.clone().sub(a.p), d2 = c.p.clone().sub(b.p);
    const ang = d1.angleTo(d2);
    const ds = (d1.length() + d2.length()) / 2 || 1e-6;
    const kappa = ang / ds;
    const rho = 1 / Math.max(kappa, 1e-9);
    const tp = taperAt(opts.taper, b.t);
    const half = Math.max(
      Math.abs((opts.section.w || opts.section.width || 20) * tp.sw / 2),
      Math.abs((opts.section.h || opts.section.height || 20) * tp.sh / 2)
    );
    if (rho < 1.05 * half) throw new Error('sweep fold at t=' + b.t.toFixed(3) + ' (rho ' + rho.toFixed(2) + ' < ' + (1.05 * half).toFixed(2) + ')');
  }

  let frames;
  if (frameMode === 'rmf') frames = rmfFrames(samples);
  else frames = samples.map(s => upFrame(s.T, up));

  const rings = [];
  for (let i = 0; i < samples.length; i++) {
    const { p, t } = samples[i];
    let s = frames[i].s.clone(), n = frames[i].n.clone();
    const ang = twist * t;
    if (ang) {
      const cs = Math.cos(ang), sn = Math.sin(ang);
      const s2 = s.clone().multiplyScalar(cs).add(n.clone().multiplyScalar(sn));
      const n2 = n.clone().multiplyScalar(cs).sub(s.clone().multiplyScalar(sn));
      s = s2; n = n2;
    }
    const tp = taperAt(opts.taper, t);
    const ring = unit.map(q => {
      return p.clone().addScaledVector(s, q.x * tp.sw).addScaledVector(n, q.y * tp.sh);
    });
    ring._u = samples[i].s;
    ring._perim = perim0 * Math.max(tp.sw, tp.sh);
    rings.push(ring);
  }

  const st = stitchRings(rings, !!opts.closed);
  let pos = st.pos, uv = st.uv;
  if (caps && !opts.closed) {
    pos = pos.concat(capFan(rings[0], samples[0].p, false));
    pos = pos.concat(capFan(rings[rings.length - 1], samples[samples.length - 1].p, true));
  }
  return geomFrom(pos, uv);
};

/* ---------- pillow (sphere topology → rounded-box SDF + displace) ---------- */
CAD.buildPillowPrim = function (opts) {
  opts = opts || {};
  const size = opts.size;
  if (!Array.isArray(size) || size.length < 3) throw new Error('pillow.size [X,Y,Z] required');
  const X = assertFinite(size[0], 'size.x'), Y = assertFinite(size[1], 'size.y'), Z = assertFinite(size[2], 'size.z');
  const tol = opts.tol != null ? opts.tol : DEFAULT_TOL;
  let edgeR = opts.edgeR != null ? opts.edgeR : Math.min(X, Y, Z) * 0.15;
  let planR = opts.planR != null ? opts.planR : Math.min(X, Y) * 0.2;
  edgeR = Math.max(0.5, edgeR);
  if (edgeR > 0.499 * Math.min(X, Y, Z)) throw new Error('pillow.edgeR too large');
  if (planR < edgeR) planR = edgeR;
  const bulgeTop = (opts.bulge && opts.bulge.top) || 0;
  const bulgeBot = (opts.bulge && opts.bulge.bottom) || 0;
  const bend = opts.bend || 0;
  const kTaper = (opts.taper && opts.taper.k != null) ? opts.taper.k : (opts.taperK || 0);
  if (kTaper < 0 || kTaper > 0.6) throw new Error('pillow.taper.k must be in [0,0.6]');

  const hx = X / 2, hy = Y / 2, hz = Z / 2;
  const rc = Math.max(0, planR - edgeR);
  const coreHx = hx - edgeR, coreHy = hy - edgeR, coreHz = hz - edgeR;

  function closestCore(p) {
    let qx = Math.max(-coreHx + rc, Math.min(coreHx - rc, p.x));
    let qy = Math.max(-coreHy + rc, Math.min(coreHy - rc, p.y));
    const dx = p.x - qx, dy = p.y - qy;
    const L = Math.hypot(dx, dy);
    if (L > 1e-12) { qx += dx / L * Math.min(L, rc); qy += dy / L * Math.min(L, rc); }
    const cz = Math.max(-coreHz, Math.min(coreHz, p.z));
    return new T.Vector3(qx, qy, cz);
  }

  function projectDir(dir) {
    // Ray from origin along dir; land on Minkowski surface of rounded-rect core ⊕ ball(edgeR)
    let lo = 0, hi = Math.hypot(hx, hy, hz) + edgeR + 1;
    for (let it = 0; it < 40; it++) {
      const mid = (lo + hi) / 2;
      const p = dir.clone().multiplyScalar(mid);
      const c = closestCore(p);
      const d = p.distanceTo(c);
      if (d > edgeR) hi = mid; else lo = mid;
    }
    const p = dir.clone().multiplyScalar(hi);
    const c = closestCore(p);
    let n = p.clone().sub(c);
    if (n.lengthSq() < 1e-16) {
      // Face centre: use dominant axis of dir
      const ax = Math.abs(dir.x), ay = Math.abs(dir.y), az = Math.abs(dir.z);
      if (az >= ax && az >= ay) n.set(0, 0, Math.sign(dir.z) || 1);
      else if (ax >= ay) n.set(Math.sign(dir.x) || 1, 0, 0);
      else n.set(0, Math.sign(dir.y) || 1, 0);
    } else n.normalize();
    return c.add(n.multiplyScalar(edgeR));
  }

  function displace(p) {
    const fx = Math.max(0, 1 - Math.pow(2 * p.x / X, 2));
    const fy = Math.max(0, 1 - Math.pow(2 * p.y / Y, 2));
    if (p.z >= 0) p.z += bulgeTop * fx * fy;
    else p.z -= bulgeBot * fx * fy;
    p.z += bend * Math.pow(2 * p.x / X, 2);
    const ty = p.y / Y + 0.5;
    p.x *= 1 - kTaper * ty;
    return p;
  }

  const segs = Math.max(12, Math.min(36, Math.ceil(Math.PI * Math.max(X, Y, Z) / Math.max(tol * 40, 4))));
  const rings = segs, slices = segs * 2;
  const grid = [];
  for (let i = 0; i <= rings; i++) {
    const v = i / rings;
    const phi = v * Math.PI;
    grid[i] = [];
    for (let j = 0; j <= slices; j++) {
      const u = j / slices;
      const th = u * Math.PI * 2;
      const dir = new T.Vector3(Math.sin(phi) * Math.cos(th), Math.sin(phi) * Math.sin(th), Math.cos(phi));
      if (dir.lengthSq() < 1e-18) dir.set(0, 0, 1);
      else dir.normalize();
      grid[i][j] = displace(projectDir(dir));
    }
  }

  const pos = [];
  const push = (a, b, c) => pos.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z);
  for (let i = 0; i < rings; i++) {
    for (let j = 0; j < slices; j++) {
      const a = grid[i][j], b = grid[i][j + 1], c = grid[i + 1][j + 1], d = grid[i + 1][j];
      if (i === 0) push(a, c, d); // degenerate at pole — dropDegenerate cleans
      else if (i === rings - 1) push(a, b, c);
      else { push(a, b, c); push(a, c, d); }
    }
  }
  return geomFrom(pos, null);
};

/* Steiner volume for axis-aligned box of outer size X×Y×Z with uniform fillet r (=edgeR=planR). */
CAD.pillowSteinerVolume = function (X, Y, Z, r) {
  const a = X - 2 * r, b = Y - 2 * r, c = Z - 2 * r;
  if (a <= 0 || b <= 0 || c <= 0) throw new Error('Steiner: r too large');
  return a * b * c + 2 * (a * b + b * c + c * a) * r + Math.PI * (a + b + c) * r * r + (4 / 3) * Math.PI * r * r * r;
};

/* ---------- panel (developable bend, square edge walls) ---------- */
CAD.buildPanelPrim = function (opts) {
  opts = opts || {};
  const size = opts.size;
  if (!Array.isArray(size) || size.length < 2) throw new Error('panel.size [W,H] required');
  const W = assertFinite(size[0], 'W'), H = assertFinite(size[1], 'H');
  const t = assertFinite(opts.t != null ? opts.t : opts.thickness, 't');
  const tol = opts.tol != null ? opts.tol : DEFAULT_TOL;
  const outline = opts.outline || { shape: 'rect' };
  const shape = outline.shape || 'rect';
  let fmin = outline.fmin != null ? outline.fmin : 0.55;
  let nExp = outline.n != null ? outline.n : 2.5;
  if (fmin <= 0 || fmin > 1) throw new Error('panel outline.fmin must be in (0,1]');
  const arch = opts.arch || 0;
  const bend = opts.bend || {};
  let R;
  if (bend.radius != null) R = assertFinite(bend.radius, 'bend.radius');
  else if (bend.sagitta != null) {
    const sag = assertFinite(bend.sagitta, 'bend.sagitta');
    if (sag >= W / 2) throw new Error('sagitta must be < W/2');
    R = (sag * sag + (W / 2) * (W / 2)) / (2 * sag);
  } else R = Math.max(20 * t, W);
  if (R < 20 * t) throw new Error('bend radius below minimum (20*t)');
  const dir = bend.direction === -1 || bend.direction === 'neg' ? -1 : 1;

  function fOutline(a) {
    if (shape === 'superellipse') {
      return fmin + (1 - fmin) * Math.pow(Math.max(0, 1 - Math.pow(Math.abs(a), nExp)), 1 / nExp);
    }
    return 1;
  }

  const nu = Math.max(16, Math.min(80, Math.ceil(W / Math.max(4, tol * 20))));
  const nv = Math.max(8, Math.min(40, Math.ceil(H / Math.max(4, tol * 20))));
  const as = [], bs = [];
  for (let i = 0; i <= nu; i++) {
    const u = i / nu;
    as.push(-1 + 2 * (0.5 - 0.5 * Math.cos(Math.PI * u)));
  }
  for (let j = 0; j <= nv; j++) bs.push(-1 + 2 * (j / nv));

  function midPoint(a, b) {
    const s = a * (W / 2);
    const v = b * fOutline(a) * (H / 2) + arch * (1 - a * a);
    return new T.Vector3(dir * R * Math.sin(s / R), v, R * (1 - Math.cos(s / R)));
  }
  function midNormal(a, b) {
    const eps = 1e-3;
    const pu = midPoint(Math.min(1, a + eps), b).sub(midPoint(Math.max(-1, a - eps), b));
    const pv = midPoint(a, Math.min(1, b + eps)).sub(midPoint(a, Math.max(-1, b - eps)));
    const n = new T.Vector3().crossVectors(pu, pv);
    if (n.lengthSq() < 1e-18) n.set(0, 0, 1); else n.normalize();
    return n;
  }

  const top = [], bot = [];
  for (let i = 0; i <= nu; i++) {
    top[i] = []; bot[i] = [];
    for (let j = 0; j <= nv; j++) {
      const p = midPoint(as[i], bs[j]);
      const n = midNormal(as[i], bs[j]);
      top[i][j] = p.clone().addScaledVector(n, t / 2);
      bot[i][j] = p.clone().addScaledVector(n, -t / 2);
    }
  }

  const pos = [];
  const push = (a, b, c) => pos.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z);
  for (let i = 0; i < nu; i++) for (let j = 0; j < nv; j++) {
    const a = top[i][j], b = top[i + 1][j], c = top[i + 1][j + 1], d = top[i][j + 1];
    push(a, b, c); push(a, c, d);
    const a2 = bot[i][j], b2 = bot[i + 1][j], c2 = bot[i + 1][j + 1], d2 = bot[i][j + 1];
    push(a2, c2, b2); push(a2, d2, c2);
  }
  // Single boundary loop so corner vertical edges appear once (manifold)
  const loop = [];
  for (let i = 0; i < nu; i++) loop.push([i, 0]);
  for (let j = 0; j < nv; j++) loop.push([nu, j]);
  for (let i = nu; i > 0; i--) loop.push([i, nv]);
  for (let j = nv; j > 0; j--) loop.push([0, j]);
  for (let k = 0; k < loop.length; k++) {
    const [i0, j0] = loop[k], [i1, j1] = loop[(k + 1) % loop.length];
    const a = top[i0][j0], b = top[i1][j1], c = bot[i1][j1], d = bot[i0][j0];
    // Opposite winding to top/bottom boundary edges for manifold pairing
    push(a, d, c); push(a, c, b);
  }

  const g = geomFrom(pos, null);
  g.userData = g.userData || {};
  g.userData.panelFlat = { W, H, t, R };
  return g;
};

CAD.curves = {
  catmullRom, polylinePath, arcLengthTable, pickStations, upFrame, sectionRing, TRI_BUDGET, DEFAULT_TOL
};
})(typeof globalThis !== 'undefined' ? globalThis : window);
