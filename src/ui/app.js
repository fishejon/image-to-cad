/* app.js — image-to-CAD workspace (spec-driven). Everything shown comes from a JSON design spec: see docs/SPEC.md */
(function () {
'use strict';
const T = THREE, CAD = window.CAD;
const $ = (s, r) => (r || document).querySelector(s), $$ = (s, r) => [...(r || document).querySelectorAll(s)];
const V = (x, y, z) => new T.Vector3(x, y, z);
const fmt = (n, d) => (+n).toLocaleString('en-US', { maximumFractionDigits: d === undefined ? 0 : d, minimumFractionDigits: d || 0 });
const inch = v => CAD.fmtInch(v), inch3 = a => CAD.fmtInch3(a), lb = v => CAD.fmtLb(v), note = s => CAD.inchifyText(s);
const outVal = (v, unit) => (!unit || unit === 'mm' || unit === 'in' || unit === '"') ? inch(v) : (v + (unit ? ' ' + unit : ''));
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const gname = id => (CAD.GROUPS.find(g => g.id === id) || { name: id }).name;
const S = { M: null, spec: null, ov: {}, R: [], kin: {}, sel: new Set(), hiddenDef: new Set(), hiddenGrp: new Set(), iso: null, mode: 'real', exF: 0, stepCur: 0, stepping: false,
  sec: { on: false, axis: 'y', off: 0, inv: false }, edges: true, meas: { on: false, pts: [], objs: [] }, q: '', need: true, hov: null, collapsed: new Set(), mv: {},
  ex: { scale: 5, bed: [220, 220, 250], split: true }, lastErrors: [], lastWarnings: [], ai: { img: null, busy: false, log: [], abort: null }, examples: {}, nav: 'orbit', movePlane: 'xy', leftOn: true, rightOn: true,
  docs: {}, docId: null };
const WS_KEY = 'image-to-cad.workspace';
const uid = () => 'd' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
function blankSpec(name) {
  return {
    name: name || 'Untitled', units: 'mm', description: 'Empty board — use AI design or edit the Spec tab to build something.', assumptions: [],
    params: { W: { value: 400, min: 100, max: 1200, step: 10, label: 'Width' }, D: { value: 300, min: 100, max: 800, step: 10, label: 'Depth' }, T: { value: 20, min: 6, max: 50, step: 1, label: 'Thickness' } },
    groups: [{ id: 'board', name: 'Board' }], steps: ['Start here'],
    parts: [{ id: 'board', name: 'Board', group: 'board', material: 'oak', grain: 'x', spec: 'W × D × T',
      ops: [{ add: ['-W/2', '-D/2', 0, 'W/2', 'D/2', 'T'] }], instances: [{ pos: [0, 0, 0], step: 0 }] }]
  };
}
function readWS() { try { return JSON.parse(localStorage.getItem(WS_KEY)); } catch (e) { return null; } }
function writeWS() {
  try {
    const docs = {};
    Object.values(S.docs).forEach(d => { docs[d.id] = { id: d.id, name: d.name, source: d.source || null, updated: d.updated || 0, spec: d.spec, ov: d.ov || {} }; });
    localStorage.setItem(WS_KEY, JSON.stringify({ activeId: S.docId, docs }));
  } catch (e) { /* quota / private mode */ }
}
function refreshDocSel() {
  const sel = $('#docsel'); if (!sel) return;
  const docs = Object.values(S.docs).sort((a, b) => (b.updated || 0) - (a.updated || 0));
  sel.innerHTML = docs.map(d => `<option value="${esc(d.id)}">${esc(d.name || 'Untitled')}</option>`).join('');
  if (S.docId && S.docs[S.docId]) sel.value = S.docId;
}
function persistActive() {
  if (!S.docId || !S.docs[S.docId] || !S.spec) return;
  const d = S.docs[S.docId], clone = JSON.parse(JSON.stringify(S.spec));
  d.spec = clone; d.ov = Object.assign({}, S.ov); d.name = clone.name || d.name || 'Untitled'; d.updated = Date.now();
  writeWS(); refreshDocSel();
}
function addDoc(spec, opts) {
  opts = opts || {}; const id = uid(), s = JSON.parse(JSON.stringify(spec)), name = opts.name || s.name || 'Untitled';
  s.name = name; S.docs[id] = { id, name, source: opts.source || null, spec: s, ov: Object.assign({}, opts.ov || {}), updated: Date.now() };
  return id;
}
function openDoc(id, opts) {
  opts = opts || {}; const d = S.docs[id]; if (!d) return false;
  if (S.docId && S.docId !== id && S.spec) persistActive();
  const prev = S.docId; S.docId = id;
  const ok = loadSpec(JSON.parse(JSON.stringify(d.spec)), Object.assign({}, d.ov || {}), !!opts.quiet);
  if (ok) { setSpecText(); if (opts.view !== false) viewNow('iso'); writeWS(); refreshDocSel(); }
  else { S.docId = prev; refreshDocSel(); }
  return ok;
}
function nextUntitled() {
  const names = new Set(Object.values(S.docs).map(d => d.name)); let i = 1; while (names.has('Untitled ' + i)) i++; return 'Untitled ' + i;
}
function newDesign() {
  const name = nextUntitled(), id = addDoc(blankSpec(name), { name });
  openDoc(id); toast('New design — previous files are unchanged');
}
function duplicateDesign() {
  if (!S.docId || !S.spec) return; persistActive();
  const base = (S.docs[S.docId].name || 'Design').replace(/ copy( \d+)?$/, ''), names = new Set(Object.values(S.docs).map(d => d.name));
  let name = base + ' copy', i = 2; while (names.has(name)) name = base + ' copy ' + i++;
  const id = addDoc(S.spec, { name, ov: S.ov }); openDoc(id); toast('Duplicated as ' + name);
}
function renameDesign() {
  if (!S.docId || !S.docs[S.docId]) return;
  const cur = S.docs[S.docId], name = prompt('Rename design', cur.name || '');
  if (name == null) return; const n = name.trim(); if (!n) return;
  cur.name = n; if (S.spec) S.spec.name = n; persistActive(); refreshAll(); toast('Renamed');
}
function deleteDesign() {
  if (!S.docId || !S.docs[S.docId]) return;
  if (Object.keys(S.docs).length <= 1) { toast('Keep at least one design'); return; }
  const cur = S.docs[S.docId];
  if (!confirm('Delete "' + (cur.name || 'Untitled') + '"? Your other designs stay.')) return;
  delete S.docs[S.docId]; S.docId = null;
  const next = Object.values(S.docs).sort((a, b) => (b.updated || 0) - (a.updated || 0))[0];
  openDoc(next.id); toast('Deleted');
}


/* ---------------- renderer / scene ---------------- */
const cv = $('#cv'), wrap = $('#vpwrap');
const renderer = new T.WebGLRenderer({ canvas: cv, antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2)); renderer.outputEncoding = T.sRGBEncoding; renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = .88; renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap;
const scene = new T.Scene(), camera = new T.PerspectiveCamera(30, 1, 5, 40000); camera.up.set(0, 0, 1);
const controls = new T.OrbitControls(camera, cv); controls.enableDamping = true; controls.dampingFactor = .12; controls.screenSpacePanning = true; controls.enablePan = true; controls.panSpeed = 1.1; controls.mouseButtons = { LEFT: T.MOUSE.ROTATE, MIDDLE: T.MOUSE.PAN, RIGHT: T.MOUSE.PAN }; controls.touches = { ONE: T.TOUCH.ROTATE, TWO: T.TOUCH.DOLLY_PAN }; controls.addEventListener('change', () => { S.need = true; });
const root = new T.Group(); scene.add(root);
scene.add(new T.HemisphereLight(0xffffff, 0x8a8478, .55));
const sun = new T.DirectionalLight(0xfff4e6, .95); sun.position.set(-1400, -2200, 2600); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); const sc_ = sun.shadow.camera; sc_.left = -1400; sc_.right = 1400; sc_.top = 1400; sc_.bottom = -1400; sc_.near = 500; sc_.far = 7000; sun.shadow.bias = -.0004; sun.shadow.normalBias = 1.5; scene.add(sun);
const fill = new T.DirectionalLight(0xdbe6ff, .35); fill.position.set(2000, 1200, 900); scene.add(fill);
const floor = new T.Mesh(new T.PlaneGeometry(9000, 9000), new T.MeshStandardMaterial({ color: 0xc9c5be, roughness: .95, metalness: 0 })); floor.position.z = -.5; floor.receiveShadow = true; scene.add(floor);
const grid = new T.GridHelper(6000, 60, 0x77716a, 0x77716a); grid.rotation.x = Math.PI / 2; grid.position.z = 0; grid.material.transparent = true; grid.material.opacity = .13; scene.add(grid);
function makeEnv() {
  const sc = new T.Scene(), g = new T.SphereGeometry(60, 32, 16), p = g.attributes.position, col = [];
  for (let i = 0; i < p.count; i++) { const t = Math.max(-1, Math.min(1, p.getZ(i) / 60)); const c = t > 0 ? [.78 + .35 * t, .8 + .32 * t, .84 + .28 * t] : [.55 + .2 * t, .52 + .2 * t, .5 + .2 * t]; col.push(...c); }
  g.setAttribute('color', new T.Float32BufferAttribute(col, 3)); sc.add(new T.Mesh(g, new T.MeshBasicMaterial({ vertexColors: true, side: T.BackSide })));
  [[-30, -25, 30, 26, 12], [35, -10, 22, 12, 18]].forEach(([x, y, z, w, h]) => { const m = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ color: new T.Color(4, 3.8, 3.4), side: T.DoubleSide })); m.position.set(x, y, z); m.lookAt(0, 0, 0); sc.add(m); });
  const pm = new T.PMREMGenerator(renderer); scene.environment = pm.fromScene(sc, .03).texture; pm.dispose();
}
makeEnv();

/* ---------------- procedural textures ---------------- */
function rng(seed) { let s = seed; return () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296; }
function woodTexture() {
  const c = document.createElement('canvas'); c.width = 1024; c.height = 1024; const x = c.getContext('2d'), r = rng(7);
  const g = x.createLinearGradient(0, 0, 0, 1024); g.addColorStop(0, '#a47652'); g.addColorStop(.5, '#9a6e4b'); g.addColorStop(1, '#a67955'); x.fillStyle = g; x.fillRect(0, 0, 1024, 1024);
  for (let i = 0; i < 520; i++) { const y = r() * 1024, a = .05 + r() * .22, dark = r() > .45, w = .5 + r() * 2.4, amp = 1 + r() * 7, f = .004 + r() * .012, ph = r() * 6;
    x.strokeStyle = dark ? `rgba(70,40,22,${a * .8})` : `rgba(225,180,135,${a * .7})`; x.lineWidth = w; x.beginPath();
    for (let u = 0; u <= 1024; u += 16) { const yy = y + Math.sin(u * f + ph) * amp + Math.sin(u * f * 2.7 + ph * 2) * amp * .35; u ? x.lineTo(u, yy) : x.moveTo(u, yy); } x.stroke(); }
  for (let i = 0; i < 6; i++) { const y = r() * 1024, h = 30 + r() * 80; const gg = x.createLinearGradient(0, y - h, 0, y + h); gg.addColorStop(0, 'rgba(30,15,8,0)'); gg.addColorStop(.5, `rgba(60,34,18,${.05 + r() * .06})`); gg.addColorStop(1, 'rgba(30,15,8,0)'); x.fillStyle = gg; x.fillRect(0, y - h, 1024, h * 2); }
  for (let i = 0; i < 1400; i++) { x.fillStyle = `rgba(25,12,6,${.06 + r() * .14})`; x.fillRect(r() * 1024, r() * 1024, 2 + r() * 9, .8); }
  const t = new T.CanvasTexture(c); t.wrapS = t.wrapT = T.RepeatWrapping; t.encoding = T.sRGBEncoding; t.anisotropy = 8; return t;
}
function marbleTexture() {
  const c = document.createElement('canvas'); c.width = 1024; c.height = 1024; const x = c.getContext('2d'), r = rng(31);
  x.fillStyle = '#e4e1da'; x.fillRect(0, 0, 1024, 1024);
  for (let i = 0; i < 90; i++) { x.fillStyle = `rgba(190,185,175,${.02 + r() * .05})`; x.beginPath(); x.ellipse(r() * 1024, r() * 1024, 40 + r() * 160, 20 + r() * 90, r() * 3, 0, 7); x.fill(); }
  for (let v = 0; v < 34; v++) { let px = r() * 1024, py = r() * 1024, ang = r() * 6.28; const w = .8 + r() * 4, a = .22 + r() * .4; x.strokeStyle = `rgba(${95 + r() * 40},${92 + r() * 35},${88 + r() * 30},${a})`; x.lineWidth = w; x.beginPath(); x.moveTo(px, py);
    for (let k = 0; k < 90; k++) { ang += (r() - .5) * .55; px += Math.cos(ang) * 14; py += Math.sin(ang) * 14; x.lineTo(px, py); if (r() < .04) { x.stroke(); x.beginPath(); x.moveTo(px, py); x.lineWidth = w * .6; } } x.stroke(); }
  const t = new T.CanvasTexture(c); t.wrapS = t.wrapT = T.RepeatWrapping; t.encoding = T.sRGBEncoding; t.anisotropy = 8; return t;
}
const TEX = { wood: woodTexture(), marble: marbleTexture() };

/* ---------------- materials ---------------- */
const mc = {};
function getMat(kind, key, extra) {
  const k = kind + ':' + key; if (mc[k]) return mc[k]; const spec = CAD.MATS[key] || CAD.MATS.wood; let m;
  const base = () => new T.MeshStandardMaterial({ color: spec.color, roughness: spec.rough, metalness: spec.metal, map: TEX[spec.tex] || null, envMapIntensity: .4 });
  if (kind === 'real') { m = base(); if (spec.tex === 'wood') m.color.set(spec.tint !== undefined ? spec.tint : 0xffffff); else if (spec.tex === 'marble') m.color.set(0xf2efe9); }
  else if (kind === 'flat') m = new T.MeshStandardMaterial({ color: extra, roughness: .6, metalness: 0 });
  else if (kind === 'xray') m = new T.MeshStandardMaterial({ color: 0xd6a36a, transparent: true, opacity: .18, depthWrite: false, roughness: .6 });
  else if (kind === 'ghost') m = new T.MeshStandardMaterial({ color: 0xb09070, transparent: true, opacity: .07, depthWrite: false });
  else if (kind === 'sel') { m = base(); m.emissive = new T.Color(0x1f5fff); m.emissiveIntensity = .55; if (spec.tex === 'wood') m.color.set(0xffffff); }
  else if (kind === 'hov') { m = base(); m.emissive = new T.Color(0x4a7bd8); m.emissiveIntensity = .28; }
  else if (kind === 'new') { m = base(); m.emissive = new T.Color(0xff7a00); m.emissiveIntensity = .42; if (spec.tex === 'wood') m.color.set(0xffffff); }
  m.side = S.sec.on ? T.DoubleSide : T.FrontSide; mc[k] = m; return m;
}
const edgeMat = new T.LineBasicMaterial({ color: 0x24160d, transparent: true, opacity: .42 }), edgeSel = new T.LineBasicMaterial({ color: 0x7fb0ff, transparent: true, opacity: .95 });
function geomOf(d) {
  if (d.geom) return d.geom; const m = d.mesh || (d.mesh = d.solid.mesh()); const g = new T.BufferGeometry();
  g.setAttribute('position', new T.BufferAttribute(m.pos, 3)); g.setAttribute('normal', new T.BufferAttribute(m.nor, 3)); g.setAttribute('uv', new T.BufferAttribute(m.uv, 2)); g.computeBoundingBox(); g.computeBoundingSphere();
  d.geom = g; d.edgeGeom = new T.EdgesGeometry(g, 25); return g;
}
function matFor(R) {
  const key = R.def.solid.mat;
  if (S.sel.has(R)) return getMat('sel', key); if (S.hov === R) return getMat('hov', key);
  if (S.iso && !S.iso.has(R)) return getMat('ghost', 'wood');
  if (S.mode === 'xray') return getMat('xray', 'x');
  if (S.mode === 'group') return getMat('flat', CAD.GROUPS.find(g => g.id === R.def.grp).color, R.def.grp);
  return getMat('real', key);
}


/* ---------------- spec → scene ---------------- */
let prevM = null, fillRows = null; const fillFor = () => fillRows || (fillRows = CAD.jointFill(S.M));
function disposeScene() { while (root.children.length) root.remove(root.children[0]); S.R = []; S.sel.clear(); S.iso = null; S.hov = null; clearMeasure(); }
/* returns true when the scene was replaced */
const hist = { stack: [], i: -1, max: 50, lock: false, sig: '' };
function histSig() { try { return JSON.stringify({ s: S.spec, o: S.ov }); } catch (e) { return String(Date.now()); } }
function pushHist() {
  if (hist.lock || !S.spec) return;
  const sig = histSig(); if (sig === hist.sig) return;
  hist.stack = hist.stack.slice(0, hist.i + 1);
  hist.stack.push({ spec: JSON.parse(JSON.stringify(S.spec)), ov: Object.assign({}, S.ov) });
  if (hist.stack.length > hist.max) hist.stack.shift();
  hist.i = hist.stack.length - 1; hist.sig = sig;
}
function restoreHist() {
  const h = hist.stack[hist.i]; if (!h) return;
  hist.lock = true;
  loadSpec(JSON.parse(JSON.stringify(h.spec)), Object.assign({}, h.ov), true);
  setSpecText(); hist.lock = false; hist.sig = histSig();
}
function undo() { if (hist.i <= 0) return toast('Nothing to undo'); hist.i--; restoreHist(); toast('Undo'); }
function redo() { if (hist.i >= hist.stack.length - 1) return toast('Nothing to redo'); hist.i++; restoreHist(); toast('Redo'); }
function loadSpec(spec, ov, quiet) {
  const M = CAD.buildSpec(spec, ov || {});
  if (!M.insts.length) { if (prevM) { CAD.GROUPS = prevM.groups; CAD.STEPS = prevM.steps.map(s => s.title); CAD.MATS = prevM.materials; } S.lastErrors = M.errors; S.lastWarnings = M.warnings; renderSpecErrors(); if (!quiet) toast('The spec has errors: see the Spec tab'); return false; }
  S.spec = spec; S.ov = ov || {}; build(M); if (!hist.lock) pushHist(); persistActive(); return true;
}
function build(M) {
  disposeScene(); Object.keys(mc).forEach(k => delete mc[k]); prevM = S.M = M; S.lastErrors = M.errors; S.lastWarnings = M.warnings; fillRows = null; S.mv = {}; S.hiddenDef.clear(); S.hiddenGrp.clear(); root.position.set(0, 0, 0);
  S.kin = { world: root }; Object.entries(M.kinematics).forEach(([k]) => { const g = new T.Group(); root.add(g); S.kin[k] = g; S.mv[k] = 0; });
  M.insts.forEach(inst => {
    const d = M.defs.get(inst.def), g = geomOf(d), mesh = new T.Mesh(g, getMat('real', d.solid.mat)), R = { inst, def: d, mesh, obj: mesh, home: inst.m.clone(), ex: V(...(inst.ex || [0, 0, 0])), anim: 1 };
    const kc = inst.kin && M.kinematics[inst.kin]; if (kc && kc.pivot) R.home.premultiply(new T.Matrix4().makeTranslation(-kc.pivot[0], -kc.pivot[1], -kc.pivot[2]));
    mesh.matrixAutoUpdate = false; mesh.castShadow = true; mesh.receiveShadow = true; mesh.userData.R = R; const ln = new T.LineSegments(d.edgeGeom, edgeMat); ln.matrixAutoUpdate = false; ln.raycast = () => { }; R.line = ln;
    const parent = S.kin[inst.kin] || root; parent.add(mesh); parent.add(ln); inst.R = R; S.R.push(R);
  });
  S.stepCur = M.steps.length - 1; S.stepping = false; stopPlay(); applyMotion(); refreshAll(); renderSpecErrors();
}
function applyTransforms() {
  const tmp = new T.Matrix4(), ev = V(0, 0, 0);
  S.R.forEach(R => { ev.copy(R.ex).multiplyScalar(S.exF); if (R.anim < 1) { const e = 1 - Math.pow(1 - R.anim, 3), dir = R.ex.lengthSq() > 1 ? R.ex.clone().normalize() : V(0, 0, 1); ev.addScaledVector(dir, 300 * (1 - e)); }
    tmp.makeTranslation(ev.x, ev.y, ev.z).multiply(R.home); R.mesh.matrix.copy(tmp); R.line.matrix.copy(tmp); R.mesh.matrixWorldNeedsUpdate = true; R.line.matrixWorldNeedsUpdate = true; });
  root.updateMatrixWorld(true); S.need = true;
}
function applyMotion() {
  Object.entries(S.M.kinematics).forEach(([k, kc]) => { const g = S.kin[k], v = S.mv[k] || 0, ax = V(...kc.axis).normalize();
    if (kc.unit === 'deg') { g.position.set(...(kc.pivot || [0, 0, 0])); g.setRotationFromAxisAngle(ax, v * Math.PI / 180); } else g.position.copy(ax.multiplyScalar(v)); });
  applyTransforms();
}
const isVis = R => !(S.hiddenDef.has(R.def.id) || S.hiddenGrp.has(R.def.grp) || R.inst.step > S.stepCur);
function updateVisuals() {
  S.R.forEach(R => { const v = isVis(R); R.mesh.visible = v; R.line.visible = v && S.edges && S.mode !== 'xray' && !(S.iso && !S.iso.has(R)); const mat = matFor(R); if (R.mesh.material !== mat) R.mesh.material = mat; R.line.material = S.sel.has(R) ? edgeSel : edgeMat; });
  S.need = true;
}
function refreshAll() { applyTransforms(); updateVisuals(); buildTree(); renderInspect(); buildSteps(); renderMotion(); renderParam(); renderExport(); renderReview(); }


/* ---------------- section ---------------- */
const plane = new T.Plane(new T.Vector3(0, -1, 0), 0);
function applySection() {
  const s = S.sec, n = { x: [1, 0, 0], y: [0, 1, 0], z: [0, 0, 1] }[s.axis], sg = s.inv ? 1 : -1;
  plane.normal.set(n[0] * sg, n[1] * sg, n[2] * sg); plane.constant = -sg * s.off * (n[0] + n[1] + n[2]);
  renderer.clippingPlanes = s.on ? [plane] : []; Object.values(mc).forEach(m => { m.side = s.on ? T.DoubleSide : T.FrontSide; m.needsUpdate = true; }); S.need = true; renderMotionSection();
}

/* ---------------- picking / measure ---------------- */
const ray = new T.Raycaster(), mouse = new T.Vector2();
function pickAt(cx, cy) {
  const r = cv.getBoundingClientRect(); mouse.set(((cx - r.left) / r.width) * 2 - 1, -((cy - r.top) / r.height) * 2 + 1); ray.setFromCamera(mouse, camera);
  for (const h of ray.intersectObject(root, true)) { const R = h.object.userData.R; if (!R || !R.mesh.visible) continue; if (S.iso && !S.iso.has(R)) continue; if (S.sec.on && plane.distanceToPoint(h.point) < 0) continue; return h; }
  return null;
}
function snap(h) {
  const a = h.object.geometry.attributes.position, f = h.face, p = h.point.clone(); let best = null, bd = 1e9;
  [f.a, f.b, f.c].forEach(i => { const v = V(a.getX(i), a.getY(i), a.getZ(i)).applyMatrix4(h.object.matrixWorld), dd = v.distanceTo(p); if (dd < bd) { bd = dd; best = v; } });
  return bd < Math.max(camera.position.distanceTo(p) * .012, 3) ? { p: best, snapped: true } : { p, snapped: false };
}
function hitMovePlane(cx, cy) {
  const r = cv.getBoundingClientRect(); mouse.set(((cx - r.left) / r.width) * 2 - 1, -((cy - r.top) / r.height) * 2 + 1); ray.setFromCamera(mouse, camera);
  const n = { xy: [0, 0, 1], xz: [0, 1, 0], yz: [1, 0, 0] }[S.movePlane] || [0, 0, 1], pl = new T.Plane(V(...n), 0), p = V(0, 0, 0);
  pl.constant = -(n[0] * root.position.x + n[1] * root.position.y + n[2] * root.position.z);
  return ray.ray.intersectPlane(pl, p) ? p : null;
}
function applyNavMode() {
  const m = S.nav; $$('#navMode button').forEach(b => b.classList.toggle('on', b.dataset.nav === m));
  $$('#movePlane button').forEach(b => b.classList.toggle('on', b.dataset.plane === S.movePlane));
  $('#movePlane').style.display = m === 'move' ? 'inline-flex' : 'none';
  controls.enableRotate = m === 'orbit'; controls.enablePan = m !== 'move';
  controls.mouseButtons.LEFT = m === 'pan' ? T.MOUSE.PAN : T.MOUSE.ROTATE;
  cv.style.cursor = S.meas.on ? 'crosshair' : (m === 'pan' ? 'grab' : m === 'move' ? 'move' : '');
  const planeHint = { xy: 'floor (XY)', xz: 'front (XZ)', yz: 'side (YZ)' }[S.movePlane];
  const bl = $('#hudBL'); if (bl) bl.textContent = m === 'pan' ? 'Drag to slide the view · scroll to zoom' : m === 'move' ? 'Drag to slide the model on the ' + planeHint : 'Drag to orbit · Shift-click to multi-select · Shift-drag to box-select · right-drag to pan';
}
let down = null, draggingModel = null, marquee = null;
(function () { const m = document.createElement('div'); m.id = 'marquee'; wrap.appendChild(m); })();
function partsInRect(x0, y0, x1, y1) {
  const r = cv.getBoundingClientRect(), L = Math.min(x0, x1) - r.left, Rgt = Math.max(x0, x1) - r.left, T_ = Math.min(y0, y1) - r.top, B = Math.max(y0, y1) - r.top, hit = [];
  S.R.forEach(R => { if (!R.mesh.visible) return; const c = new T.Box3().setFromObject(R.mesh).getCenter(V(0, 0, 0)).project(camera); const sx = (c.x * .5 + .5) * r.width, sy = (-c.y * .5 + .5) * r.height; if (c.z <= 1 && sx >= L && sx <= Rgt && sy >= T_ && sy <= B) hit.push(R); });
  return hit;
}
cv.addEventListener('pointerdown', e => {
  cv.focus(); down = { x: e.clientX, y: e.clientY, shift: e.shiftKey, button: e.button };
  if (e.shiftKey && S.nav === 'orbit' && e.button === 0 && !S.meas.on) { controls.enabled = false; marquee = { x0: e.clientX, y0: e.clientY }; cv.setPointerCapture(e.pointerId); return; }
  if (S.nav === 'move' && e.button === 0 && !S.meas.on) {
    const p = hitMovePlane(e.clientX, e.clientY); if (p) {
      draggingModel = { p0: p.clone(), pos0: root.position.clone() }; controls.enabled = false; cv.setPointerCapture(e.pointerId);
    }
  }
}, true);
cv.addEventListener('pointermove', e => {
  if (marquee) {
    const box = $('#marquee'), r = wrap.getBoundingClientRect(), x = Math.min(marquee.x0, e.clientX) - r.left, y = Math.min(marquee.y0, e.clientY) - r.top;
    box.style.display = 'block'; box.style.left = x + 'px'; box.style.top = y + 'px'; box.style.width = Math.abs(e.clientX - marquee.x0) + 'px'; box.style.height = Math.abs(e.clientY - marquee.y0) + 'px'; return;
  }
  if (!draggingModel) return; const p = hitMovePlane(e.clientX, e.clientY); if (!p) return;
  const d = p.clone().sub(draggingModel.p0); root.position.copy(draggingModel.pos0).add(d); S.need = true;
});
cv.addEventListener('pointerup', e => {
  if (marquee) {
    const hits = partsInRect(marquee.x0, marquee.y0, e.clientX, e.clientY); $('#marquee').style.display = 'none';
    const moved = Math.hypot(e.clientX - marquee.x0, e.clientY - marquee.y0) > 6; marquee = null; controls.enabled = true; down = null;
    if (moved) { const n = new Set(S.sel); hits.forEach(R => n.add(R)); setSel([...n]); } return;
  }
  if (draggingModel) { draggingModel = null; controls.enabled = true; }
  if (!down) return; const mv = Math.hypot(e.clientX - down.x, e.clientY - down.y), add = down.shift || e.ctrlKey || e.metaKey; down = null; if (mv > 4) return; const h = pickAt(e.clientX, e.clientY);
  if (S.meas.on) { if (h) addMeasurePoint(snap(h).p); return; } if (S.nav === 'move' || S.nav === 'pan') return; if (!h) { if (!add) setSel([]); return; }
  const R = h.object.userData.R; if (add) { const n = new Set(S.sel); n.has(R) ? n.delete(R) : n.add(R); setSel([...n]); } else setSel([R]);
});
let hovT = 0;
cv.addEventListener('pointermove', e => {
  if (e.buttons || marquee || draggingModel) { hideTip(); return; } const now = performance.now(); if (now - hovT < 40) return; hovT = now;
  const h = pickAt(e.clientX, e.clientY), R = h ? h.object.userData.R : null; if (R !== S.hov) { S.hov = R; updateVisuals(); }
  const tip = $('#tip'), r = wrap.getBoundingClientRect();
  if (R && !S.meas.on) { tip.style.display = 'block'; tip.style.left = Math.min(r.width - 290, e.clientX - r.left + 14) + 'px'; tip.style.top = (e.clientY - r.top + 14) + 'px'; tip.innerHTML = `<b>${esc(R.def.name)}</b><br><span style="color:var(--dim)">${esc(gname(R.def.grp))}${R.def.qty > 1 ? ' · #' + R.inst.qtyIdx + ' of ' + R.def.qty : ''}</span>`; }
  else if (S.meas.on && h) { const s = snap(h); tip.style.display = 'block'; tip.style.left = (e.clientX - r.left + 14) + 'px'; tip.style.top = (e.clientY - r.top + 14) + 'px'; tip.textContent = (s.snapped ? 'Vertex ' : 'Surface ') + s.p.toArray().map(inch).join(', '); } else hideTip();
});
cv.addEventListener('pointerleave', () => { hideTip(); if (S.hov) { S.hov = null; updateVisuals(); } });
function hideTip() { $('#tip').style.display = 'none'; }
function setSel(list) { S.sel = new Set(list); updateVisuals(); syncTreeSel(); renderInspect(); if ($('#aiBox').classList.contains('open')) syncAIFocus(); }
function selectDef(id, add) { const l = S.R.filter(R => R.def.id === id); if (add) { const n = new Set(S.sel); l.forEach(R => n.add(R)); setSel([...n]); } else setSel(l); }
function selectedPartIds() { return [...new Set([...S.sel].map(R => R.def.id))]; }
function applyMaterial(matKey) {
  const ids = selectedPartIds(); if (!ids.length) return toast('Select one or more parts first');
  if (!S.spec.materials) S.spec.materials = {};
  const base = CAD.DEFAULT_MATS[matKey];
  if (!S.spec.materials[matKey]) S.spec.materials[matKey] = base ? Object.assign({ base: matKey }, { name: base.name }) : { base: matKey };
  (S.spec.parts || []).forEach(p => { if (ids.includes(p.id)) p.material = matKey; });
  const keep = new Set(ids); loadSpec(S.spec, S.ov, true); setSpecText(); setSel(S.R.filter(R => keep.has(R.def.id))); toast('Material set on ' + ids.length + ' part type(s): ' + ((CAD.DEFAULT_MATS[matKey] || {}).name || matKey));
}
function clearMeasure() { S.meas.objs.forEach(o => scene.remove(o)); S.meas.objs = []; S.meas.pts = []; const l = $('#mlabel'); if (l) l.style.display = 'none'; }
function addMeasurePoint(p) {
  if (S.meas.pts.length >= 2) clearMeasure(); S.meas.pts.push(p.clone());
  const m = new T.Mesh(new T.SphereGeometry(Math.max(2.5, camera.position.distanceTo(p) * .005), 12, 10), new T.MeshBasicMaterial({ color: 0xffd400, depthTest: false })); m.position.copy(p); m.renderOrder = 10; scene.add(m); S.meas.objs.push(m);
  if (S.meas.pts.length === 2) { const [a, b] = S.meas.pts, ln = new T.Line(new T.BufferGeometry().setFromPoints([a, b]), new T.LineBasicMaterial({ color: 0xffd400, depthTest: false })); ln.renderOrder = 10; scene.add(ln); S.meas.objs.push(ln);
    const d = b.clone().sub(a); S.meas.txt = `${inch(d.length())}   ΔX ${inch(d.x)}  ΔY ${inch(d.y)}  ΔZ ${inch(d.z)}`; S.meas.mid = a.clone().add(b).multiplyScalar(.5); placeMeasureLabel(); }
  S.need = true;
}
function placeMeasureLabel() {
  const l = $('#mlabel'); if (S.meas.pts.length < 2) { l.style.display = 'none'; return; } const v = S.meas.mid.clone().project(camera), r = wrap.getBoundingClientRect(); if (v.z > 1) { l.style.display = 'none'; return; }
  l.style.display = 'block'; l.textContent = S.meas.txt; l.style.left = ((v.x * .5 + .5) * r.width - l.offsetWidth / 2) + 'px'; l.style.top = ((-v.y * .5 + .5) * r.height - 30) + 'px';
}

/* ---------------- camera ---------------- */
let tween = null;
function tweenCam(pos, tgt, ms) { tween = { p0: camera.position.clone(), t0: controls.target.clone(), p1: pos, t1: tgt, t: performance.now(), d: ms || 450 }; S.need = true; }
function sceneBox() { const b = new T.Box3(); S.R.forEach(R => { if (R.mesh.visible) b.union(new T.Box3().setFromObject(R.mesh)); }); return b.isEmpty() ? new T.Box3(V(-700, -200, 0), V(700, 200, 850)) : b; }
function viewTo(name) {
  if (name === 'iso') root.position.set(0, 0, 0);
  const b = sceneBox(), c = b.getCenter(V(0, 0, 0)), r = b.getSize(V(0, 0, 0)).length() / 2, d = r / Math.tan(camera.fov * Math.PI / 360) * .98 * (camera.aspect < 1 ? 1.5 : 1);
  const dirs = { iso: [.7, -1, .52], front: [0, -1, .1], right: [1, 0, .1], top: [0, -.001, 1], back: [0, 1, .1], left: [-1, 0, .1] }, v = V(...dirs[name]).normalize(); tweenCam(c.clone().addScaledVector(v, d), c, 520);
}
function fitView() {
  if (S.sel.size) return focusSel();
  const b = sceneBox(), c = b.getCenter(V(0, 0, 0)), r = Math.max(40, b.getSize(V(0, 0, 0)).length() / 2);
  const d = r / Math.tan(camera.fov * Math.PI / 360) * 1.08 * (camera.aspect < 1 ? 1.5 : 1);
  let dir = camera.position.clone().sub(controls.target); if (dir.lengthSq() < 1e-6) return viewTo('iso');
  tweenCam(c.clone().addScaledVector(dir.normalize(), d), c, 450);
}
function focusSel() {
  if (!S.sel.size) return fitView(); const b = new T.Box3(); S.sel.forEach(R => b.union(new T.Box3().setFromObject(R.mesh)));
  const c = b.getCenter(V(0, 0, 0)), r = Math.max(50, b.getSize(V(0, 0, 0)).length() / 2), d = r / Math.tan(camera.fov * Math.PI / 360) * 1.6, dir = camera.position.clone().sub(controls.target).normalize(); tweenCam(c.clone().addScaledVector(dir, d), c, 450);
}

/* ---------------- tree ---------------- */
function buildTree() {
  const tree = $('#tree'); tree.innerHTML = ''; const q = S.q.toLowerCase();
  CAD.GROUPS.forEach(g => {
    const defs = [...S.M.defs.values()].filter(d => d.grp === g.id && d.qty > 0 && (!q || (d.name + ' ' + d.id + ' ' + (d.spec || '')).toLowerCase().includes(q))).sort((a, b) => a.name.localeCompare(b.name)); if (!defs.length) return;
    const n = defs.reduce((s, d) => s + d.qty, 0), col = S.collapsed.has(g.id) && !q, wg = document.createElement('div'); wg.className = 'g';
    const h = document.createElement('div'); h.className = 'gh';
    h.innerHTML = `<span class="eye ${S.hiddenGrp.has(g.id) ? 'off' : ''}" data-g="${g.id}">●</span><span class="dot" style="background:#${g.color.toString(16).padStart(6, '0')}"></span><span>${col ? '▸' : '▾'} ${esc(g.name)}</span><span class="cnt">${defs.length} · ${n}×</span>`;
    h.addEventListener('click', e => {
      if (e.target.classList.contains('eye')) { S.hiddenGrp.has(g.id) ? S.hiddenGrp.delete(g.id) : S.hiddenGrp.add(g.id); updateVisuals(); buildTree(); return; }
      const parts = S.R.filter(R => R.def.grp === g.id);
      if (e.shiftKey || e.metaKey || e.ctrlKey) {
        const n = new Set(S.sel); parts.forEach(R => n.add(R)); setSel([...n]);
        return;
      }
      if (e.detail === 2) { setSel(parts); return; }
      col ? S.collapsed.delete(g.id) : S.collapsed.add(g.id); buildTree();
    });
    wg.appendChild(h);
    if (!col) defs.forEach(d => { const r = document.createElement('div'); r.className = 'pr'; r.dataset.id = d.id;
      r.innerHTML = `<span class="eye ${S.hiddenDef.has(d.id) ? 'off' : ''}">●</span><span class="nm" title="${esc(d.name)}">${esc(d.name)}</span><span class="q">${d.qty}×</span>`;
      r.addEventListener('click', e => { if (e.target.classList.contains('eye')) { S.hiddenDef.has(d.id) ? S.hiddenDef.delete(d.id) : S.hiddenDef.add(d.id); updateVisuals(); e.target.classList.toggle('off'); return; } selectDef(d.id, e.ctrlKey || e.metaKey || e.shiftKey); });
      r.addEventListener('dblclick', focusSel); wg.appendChild(r); });
    tree.appendChild(wg);
  }); syncTreeSel();
}
function syncTreeSel() { const ids = new Set([...S.sel].map(R => R.def.id)); $$('.pr').forEach(r => r.classList.toggle('sel', ids.has(r.dataset.id))); }


/* ---------------- inspector ---------------- */
function renderInspect() {
  const el = $('#p-insp'), M = S.M; if (!M) return;
  if (!S.sel.size) {
    let mass = 0; const byMat = {}; M.insts.forEach(i => { const d = M.defs.get(i.def); mass += d.mass; const k = (CAD.MATS[d.solid.mat] || {}).name || d.solid.mat; byMat[k] = (byMat[k] || 0) + d.mass; });
    el.innerHTML = `<h3>${esc(M.meta.name)}</h3>${M.meta.description ? `<div class="card">${esc(M.meta.description)}</div>` : ''}<div class="kv"><span>Overall size</span><span>${inch3(M.size)}</span><span>Part types / pieces</span><span>${M.defs.size} / ${M.insts.length}</span><span>Weight (est.)</span><span>${lb(mass)}</span>${Object.entries(byMat).map(([k, v]) => `<span>${esc(k)}</span><span>${lb(v)}</span>`).join('')}</div>
      ${M.meta.assumptions.length ? `<h3>Assumptions</h3><div class="card">${M.meta.assumptions.map(a => '• ' + esc(a)).join('<br>')}</div>` : ''}${S.lastWarnings.length ? `<div class="card warn"><b>Warnings</b>${S.lastWarnings.slice(0, 6).map(esc).join('<br>')}</div>` : ''}
      <div class="card"><b>How to use</b>Click a part (Shift-click or Shift-drag to multi-select). <b>AI design</b> opens picture upload and prompt-based revise. <i>Move model</i> + Floor/Front/Side slides on any plane. Collapse panels with ‹ ›.</div>`; return; }
  const first = [...S.sel][0], d = first.def, many = new Set([...S.sel].map(R => R.def.id)).size > 1;
  const matPicker = () => {
    const cur = [...new Set([...S.sel].map(R => R.def.solid.mat))];
    const btn = (k, label) => `<button type="button" class="btn sm matbtn${cur.length === 1 && cur[0] === k ? ' on' : ''}" data-mat="${esc(k)}">${esc(label)}</button>`;
    const woods = CAD.WOOD_KEYS.map(k => btn(k, (CAD.DEFAULT_MATS[k] || { name: k }).name)).join('');
    return `<h3>Wood / material</h3><div class="matrow">${woods}${btn('marble', 'Marble')}${btn('paint', 'Painted')}${btn('steel', 'Steel')}</div>
      <div class="card">Applies to all <b>${selectedPartIds().length}</b> selected part type(s)${S.sel.size > selectedPartIds().length ? ' (' + S.sel.size + ' pieces)' : ''}. Shift-click a group or part in the tree to add more.</div>`;
  };
  if (many) { const m = {}; S.sel.forEach(R => m[R.def.id] = (m[R.def.id] || 0) + 1); el.innerHTML = `<h3>${S.sel.size} pieces selected</h3><div class="kv">${Object.entries(m).map(([id, n]) => `<span>${esc(S.M.defs.get(id).name)}</span><span>${n}×</span>`).join('')}</div>${matPicker()}${acts()}`; bindActs(); return; }
  const sz = d.size, rows = d.solid.exact ? fillFor().filter(r => r.part === d.id + '#' + first.inst.qtyIdx) : [], by = {};
  rows.forEach(r => { const k = r.tag; (by[k] = by[k] || { n: 0, by: new Set(), ok: true }).n++; r.by.split('+').filter(Boolean).forEach(x => by[k].by.add(x)); if (r.ratio < .999) by[k].ok = false; });
  const lab = {}; (d.solid.feat || []).forEach(f => { if (f.label && !lab[f.tag]) lab[f.tag] = f.label; });
  el.innerHTML = `<h3>${esc(d.name)}</h3><div class="kv"><span>Group</span><span>${esc(gname(d.grp))}</span><span>Quantity</span><span>${d.qty}${d.qty > 1 ? ' (this is #' + first.inst.qtyIdx + ')' : ''}</span><span>Size</span><span>${inch3(sz)}</span>
    <span>Material</span><span>${esc((CAD.MATS[d.solid.mat] || {}).name || d.solid.mat)}</span><span>Kind</span><span>${d.solid.exact ? 'solid (exact boolean)' : 'mesh primitives'}</span><span>Volume / mass</span><span>${fmt(d.vol / 1000, 1)} cm³ · ${lb(d.mass)}</span><span>Step</span><span>${first.inst.step + 1}. ${esc((S.M.steps[first.inst.step] || {}).title || '')}</span></div>
    ${matPicker()}
    ${d.spec || d.notes.length ? `<div class="card"><b>Spec</b>${esc(note(d.spec))}${d.notes.length ? '<br>' + d.notes.map(n => esc(note(n))).join('<br>') : ''}</div>` : ''}
    ${Object.keys(by).length ? `<h3>Joinery on this part</h3><table>${Object.entries(by).map(([tag, v]) => `<tr><td>${esc(note(lab[tag] || tag))}</td><td class="n">${v.n}×</td><td class="${v.ok ? 'pass' : 'fail'}">${v.ok ? '✓ ' + esc([...v.by].join(', ')) : '✗ not filled'}</td></tr>`).join('')}</table>` : ''}${acts()}`; bindActs();
}
const acts = () => `<h3>Actions</h3><div class="grid2"><button class="btn sm" data-a="focus">Focus</button><button class="btn sm" data-a="iso">Isolate</button><button class="btn sm" data-a="hide">Hide</button><button class="btn sm" data-a="showall">Show all</button><button class="btn sm" data-a="ai" style="grid-column:1/3">Revise selected with AI…</button><button class="btn sm" data-a="stlp" style="grid-column:1/3">STL · print-ready (${S.ex.scale === 1 ? '1:1' : '1:' + S.ex.scale})</button></div>`;
function bindActs() {
  $$('#p-insp [data-a]').forEach(b => b.onclick = () => { const a = b.dataset.a; if (a === 'focus') focusSel(); else if (a === 'iso') { S.iso = new Set(S.sel); updateVisuals(); } else if (a === 'hide') { S.sel.forEach(R => S.hiddenDef.add(R.def.id)); setSel([]); updateVisuals(); buildTree(); } else if (a === 'showall') showAll(); else if (a === 'stlp') exportSelected(); else if (a === 'ai') { openAI(); const t = $('#aiRevise'); if (t) t.focus(); } });
  $$('#p-insp .matbtn').forEach(b => b.onclick = () => applyMaterial(b.dataset.mat));
}
function showAll() { S.hiddenDef.clear(); S.hiddenGrp.clear(); S.iso = null; S.stepCur = S.M.steps.length - 1; S.stepping = false; stopPlay(); S.R.forEach(R => R.anim = 1); updateVisuals(); applyTransforms(); buildTree(); buildSteps(); }


/* ---------------- assembly steps ---------------- */
let playT = null;
function buildSteps() {
  const el = $('#steps'); el.innerHTML = '';
  CAD.STEPS.forEach((s, i) => { const t = document.createElement('i'); t.title = (i + 1) + '. ' + s; t.className = (i <= S.stepCur ? 'on ' : '') + (S.stepping && i === S.stepCur ? 'cur' : ''); t.onclick = () => { stopPlay(); gotoStep(i); }; el.appendChild(t); });
  $('#stepTxt').textContent = S.stepping ? `Step ${S.stepCur + 1}/${CAD.STEPS.length}: ${CAD.STEPS[S.stepCur]}` : 'Click a segment to step through the assembly sequence';
}
function gotoStep(i) { S.stepCur = i; S.stepping = true; S.R.forEach(R => R.anim = R.inst.step === i ? 0 : 1); updateVisuals(); buildSteps(); S.need = true; }
function startPlay() { stopPlay(); S.stepping = true; let i = -1; $('#bPlay').textContent = '■ Stop'; const tick = () => { i++; if (i >= CAD.STEPS.length) { stopPlay(); return; } gotoStep(i); playT = setTimeout(tick, 1600); }; tick(); }
function stopPlay() { if (playT) clearTimeout(playT); playT = null; $('#bPlay').textContent = '▶ Assemble'; }
$('#bPlay').onclick = () => playT ? stopPlay() : startPlay(); $('#bStepAll').onclick = showAll;


/* ---------------- panes ---------------- */
const slider = (id, label, min, max, step, val, shown) => `<div class="row"><label for="${id}">${label}</label><input type="range" id="${id}" min="${min}" max="${max}" step="${step}" value="${val}"><output id="${id}o">${shown}</output></div>`;
function renderMotion() {
  const el = $('#p-motion'), M = S.M, ks = Object.entries(M.kinematics), shown = (kc, v) => kc.unit === 'deg' ? v + '°' : inch(v);
  el.innerHTML = (ks.length ? '<h3>Moving parts</h3>' + ks.map(([k, kc], i) => slider('mk' + i, esc(kc.label), kc.range[0], kc.range[1], Math.max(.1, +((kc.range[1] - kc.range[0]) / 300).toFixed(2)), S.mv[k] || 0, shown(kc, S.mv[k] || 0))).join('') + '<div class="grid2"><button class="btn sm" id="mOpen">Open all</button><button class="btn sm" id="mClose">Close all</button></div>'
    : '<div class="card"><b>No moving parts</b>Add a <code>kinematics</code> entry to the spec (and <code>"kin"</code> on instances) to get sliders here.</div>') +
    `<h3>Section plane</h3><div class="row"><label>Axis</label><div class="seg" id="secAx">${['x', 'y', 'z'].map(a => `<button class="btn sm ${S.sec.axis === a ? 'on' : ''}" data-a="${a}">${a.toUpperCase()}</button>`).join('')}</div><button class="btn sm" id="secInv">Flip</button></div><div id="secSl"></div>`;
  ks.forEach(([k, kc], i) => { const e = $('#mk' + i); e.oninput = () => { S.mv[k] = +e.value; $('#mk' + i + 'o').textContent = shown(kc, +e.value); applyMotion(); }; });
  const setAll = open => { ks.forEach(([k, kc]) => S.mv[k] = open ? kc.range[1] : kc.range[0]); applyMotion(); renderMotion(); };
  if (ks.length) { $('#mOpen').onclick = () => setAll(true); $('#mClose').onclick = () => setAll(false); }
  $$('#secAx button').forEach(b => b.onclick = () => { S.sec.axis = b.dataset.a; S.sec.off = Math.round(sceneBox().getCenter(V(0, 0, 0))[S.sec.axis]); applySection(); renderMotion(); }); $('#secInv').onclick = () => { S.sec.inv = !S.sec.inv; applySection(); }; renderMotionSection();
}
function renderMotionSection() {
  const el = $('#secSl'); if (!el) return; const b = sceneBox(), a = S.sec.axis, lo = Math.floor(b.min[a]), hi = Math.ceil(b.max[a]);
  el.innerHTML = slider('so', 'Offset', lo, hi, 1, S.sec.off, inch(S.sec.off)) + `<div class="chk"><input type="checkbox" id="secOn" ${S.sec.on ? 'checked' : ''}><label for="secOn">Section active</label></div>`;
  $('#so').oninput = e => { S.sec.off = +e.target.value; $('#soo').textContent = inch(+e.target.value); if (S.sec.on) applySection(); }; $('#secOn').onchange = e => { S.sec.on = e.target.checked; $('#bSec').classList.toggle('on', S.sec.on); applySection(); };
}
function parseInchInput(s) {
  s = String(s || '').trim().replace(/["″']/g, '');
  if (!s) return NaN;
  const mixed = s.match(/^(\d+)\s+(\d+)\s*\/\s*(\d+)$/);
  if (mixed) return (+mixed[1] + (+mixed[2] / +mixed[3])) * CAD.MM_PER_IN;
  const frac = s.match(/^(\d+)\s*\/\s*(\d+)$/);
  if (frac) return (+frac[1] / +frac[2]) * CAD.MM_PER_IN;
  const n = parseFloat(s);
  return isFinite(n) ? n * CAD.MM_PER_IN : NaN;
}
function applyOverallSize() {
  const tw = parseInchInput($('#ovW').value), td = parseInchInput($('#ovD').value), th = parseInchInput($('#ovH').value);
  if (![tw, td, th].every(v => v > 1 && isFinite(v))) return toast('Enter overall width, depth, and height in inches');
  const [cw, cd, ch] = S.M.size; if (!(cw > 0 && cd > 0 && ch > 0)) return;
  const pd = S.M.paramDefs, by = Object.fromEntries(pd.map(p => [p.key.toLowerCase(), p]));
  const wKey = by.w || by.width, dKey = by.d || by.depth || by.depthmm, hKey = by.h || by.height;
  if (wKey && dKey && hKey) {
    const ov = {}; pd.forEach(p => { ov[p.key] = p.value; });
    ov[wKey.key] = tw; ov[dKey.key] = td; ov[hKey.key] = th;
    toast('Rebuilding to ' + inch3([tw, td, th]) + '…');
    setTimeout(() => { if (loadSpec(S.spec, ov, true)) toast('Resized: ' + inch3(S.M.size)); }, 20);
    return;
  }
  const sx = tw / cw, sy = td / cd, sz = th / ch;
  if ([sx, sy, sz].some(v => v < .05 || v > 40)) return toast('That size change is too extreme');
  toast('Scaling model to ' + inch3([tw, td, th]) + '…');
  setTimeout(() => {
    const scaled = CAD.scaleSpec(S.spec, sx, sy, sz);
    if (loadSpec(scaled, {}, true)) { setSpecText(); toast('Resized: ' + inch3(S.M.size)); }
  }, 20);
}
function renderParam() {
  const el = $('#p-param'), M = S.M, pd = M.paramDefs;
  const [cw, cd, ch] = M.size;
  const overall = `<h3>Overall size</h3><div class="card">Current: <b>${inch3(M.size)}</b>. Set target overall size in inches — the model rebuilds to fill that box.</div>
    <div class="row"><label>Width</label><input id="ovW" type="text" value="${esc(CAD.fmtInch(cw).replace(/"$/, ''))}" style="flex:1" placeholder='e.g. 55'></div>
    <div class="row"><label>Depth</label><input id="ovD" type="text" value="${esc(CAD.fmtInch(cd).replace(/"$/, ''))}" style="flex:1" placeholder='e.g. 16'></div>
    <div class="row"><label>Height</label><input id="ovH" type="text" value="${esc(CAD.fmtInch(ch).replace(/"$/, ''))}" style="flex:1" placeholder='e.g. 33 1/2'></div>
    <button class="btn pri sm" id="ovApply" style="width:100%;margin:4px 0 10px">Apply overall size</button>`;
  el.innerHTML = overall + (pd.length ? '<h3>Parameters (releasing a slider re-cuts every joint)</h3>' + pd.map((p, i) => slider('pp' + i, esc(p.label), p.min, p.max, p.step, p.value, outVal(p.value, p.unit))).join('') + '<div class="grid2"><button class="btn sm" id="pReset">Reset to spec defaults</button><button class="btn sm" id="pSpec">Edit in spec</button></div>'
    : '<div class="card"><b>No named parameters</b>This design uses fixed numbers. Overall size still works by scaling the whole model.</div>') +
    `<h3>Assembly sequence</h3><ol style="margin:0;padding-left:18px">${M.steps.map(s => `<li>${esc(s.title)}</li>`).join('')}</ol>`;
  $('#ovApply').onclick = applyOverallSize;
  pd.forEach((p, i) => { const e = $('#pp' + i); e.oninput = () => $('#pp' + i + 'o').textContent = outVal(+e.value, p.unit); e.onchange = () => { const ov = {}; pd.forEach((q, j) => ov[q.key] = +$('#pp' + j).value); toast('Re-cutting joinery…'); setTimeout(() => { loadSpec(S.spec, ov, true); toast('Rebuilt: ' + inch3(S.M.size)); }, 20); }; });
  if (pd.length) { $('#pReset').onclick = () => loadSpec(S.spec, {}, true); $('#pSpec').onclick = () => setTab('spec'); }
}

/* ---------------- delivery (downloads) ---------------- */
const safe = n => CAD.exporter.safe(n);
let dlCap; async function getDL() { if (dlCap !== undefined) return dlCap; try { dlCap = (window.claude && window.claude.use) ? await window.claude.use('downloads') : null; } catch (e) { dlCap = null; } return dlCap; }
function anchorSave(name, blob) { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000); }
async function deliver(base, files) {
  if (!files.length) { toast('Nothing to export'); return null; } const dl = await getDL(), many = files.length > 1, zipIt = () => new Blob([CAD.zip(files.map(f => ({ name: f.name, data: f.data })))], { type: 'application/zip' });
  const info = { files: files.map(f => f.name), tris: files.reduce((s, f) => s + (f.tris || 0), 0) }; window.__lastExport = info;
  const plain = !many && /\.(csv|html|txt|json)$/.test(files[0].name), stl = !many && /\.stl$/.test(files[0].name);
  try { if (dl) { if (plain) { await dl.save({ filename: files[0].name, data: new Blob([files[0].data]) }); toast(files[0].name + ' saved'); } else { await dl.save({ filename: safe(base) + '.zip', data: zipIt() }); toast((many ? files.length + ' files' : files[0].name) + ' saved inside ' + safe(base) + '.zip'); } }
    else if (plain || stl) { anchorSave(files[0].name, new Blob([files[0].data], { type: 'application/octet-stream' })); toast('Downloaded ' + files[0].name); } else { anchorSave(safe(base) + '.zip', zipIt()); toast('Downloaded ' + safe(base) + '.zip'); }
  } catch (e) { toast(e && e.code === 'declined' ? 'Save cancelled' : 'Save failed: ' + (e && e.message || e)); } return info;
}
const cutCSV = () => CAD.exporter.cutCSV(S.M);
/* ---------------- export ---------------- */
const mult = () => 1 / S.ex.scale, scTag = () => S.ex.scale === 1 ? '1-1' : '1-' + S.ex.scale, jsonOf = spec => JSON.stringify(spec, (k, v) => k.startsWith('__') ? undefined : v, 1);
const expOpts = () => ({ mult: mult(), bed: S.ex.bed, split: S.ex.split, qty: true });
function exportSelected() { const rs = [...S.sel]; if (!rs.length) return toast('Select a part first'); return deliver('selected_' + scTag(), CAD.exporter.stlFiles(S.M, [...new Set(rs.map(R => R.def))], expOpts())); }
function exportGroup(gid) { return deliver(safe(S.M.meta.name) + '_' + gid + '_' + scTag(), CAD.exporter.stlFiles(S.M, [...S.M.defs.values()].filter(d => d.grp === gid), expOpts())); }
function exportAll() { const f = CAD.exporter.stlFiles(S.M, [...S.M.defs.values()], expOpts()); f.push({ name: 'CUT_LIST.csv', data: cutCSV() }); f.push({ name: 'spec.json', data: jsonOf(S.spec) }); f.push({ name: 'README.txt', data: `${S.M.meta.name}: print-ready parts, scale 1:${S.ex.scale}, bed ${S.ex.bed.join('×')} mm.\nEach part is oriented flat (longest axis X, thinnest Z). Parts too big for the bed are split with a rectangular alignment key (0.2 mm clearance at print scale); _pXYZ = piece index. _xN = quantity needed.\nMesh parts (round / turned) are exported whole. Units mm, Z-up.\n` }); return deliver(safe(S.M.meta.name) + '_all_parts_' + scTag(), f); }
function exportAssembly() { const f = CAD.exporter.assemblyFile(S.M, mult(), safe(S.M.meta.name) + '_assembled_' + scTag()); return deliver(safe(S.M.meta.name) + '_assembled', [f]); }
function exportPlates() { const r = CAD.exporter.plateFiles(S.M, mult(), S.ex.bed, S.ex.split); return deliver(safe(S.M.meta.name) + '_print_plates_' + scTag(), r.files).then(i => { toast(r.plates.length + ' plate(s)' + (r.over.length ? ', ' + r.over.length + ' oversize' : '')); return i; }); }
function renderExport() {
  const e = S.ex, el = $('#p-export');
  el.innerHTML = `<h3>Print scale &amp; printer bed</h3><div class="row"><label>Scale</label><select id="exs2" class="btn" style="flex:1">${[1, 2, 4, 5, 8, 10, 20].map(s => `<option value="${s}" ${s === e.scale ? 'selected' : ''}>${s === 1 ? '1:1 (full size)' : '1:' + s + ' model'}</option>`).join('')}</select></div>
  <div class="row"><label>Bed X·Y·Z</label><input id="bx" type="number" value="${e.bed[0]}" style="width:60px"><input id="by" type="number" value="${e.bed[1]}" style="width:60px"><input id="bz" type="number" value="${e.bed[2]}" style="width:60px"></div>
  <div class="chk"><input type="checkbox" id="exsp" ${e.split ? 'checked' : ''}><label for="exsp">Split parts that exceed the bed (keyed, 0.2 mm clearance)</label></div><div id="exInfo"></div>
  <h3>Export</h3><div class="grid2"><button class="btn sm" id="eSel">Selected part(s)</button><button class="btn sm" id="eGrp">Group of selection</button><button class="btn sm" id="eAsm">Whole object · 1 STL</button><button class="btn sm" id="eAll">All parts · ZIP</button></div>
  <button class="btn pri sm" id="ePl" style="width:100%;margin-top:8px">Nest everything onto bed plates (STL per plate)</button>
  <div class="grid2" style="margin-top:8px"><button class="btn sm" id="eCsv">Cut list · CSV</button><button class="btn sm" id="eGuide">Build guide · HTML</button><button class="btn sm" id="eSpec" style="grid-column:1/3">Design spec · JSON</button></div>
  <div class="card"><b>Notes</b>Binary STL, millimetres at the chosen scale, Z-up. Parts lie flat (longest axis on X). Exact (solid) parts split on straight planes with keys; round mesh parts are exported whole and flagged if they exceed the bed. Inside Claude the viewer only saves certain file types, so STLs arrive in a .zip.</div>`;
  const upd = () => { e.scale = +$('#exs2').value; e.bed = [+$('#bx').value || 220, +$('#by').value || 220, +$('#bz').value || 250]; e.split = $('#exsp').checked; info(); renderInspect(); };
  ['exs2', 'bx', 'by', 'bz', 'exsp'].forEach(id => $('#' + id).onchange = upd);
  $('#eSel').onclick = exportSelected; $('#eGrp').onclick = () => { const f = [...S.sel][0]; f ? exportGroup(f.def.grp) : toast('Select a part to pick its group'); }; $('#eAsm').onclick = exportAssembly; $('#eAll').onclick = exportAll; $('#ePl').onclick = exportPlates;
  $('#eCsv').onclick = () => deliver('cut_list', [{ name: safe(S.M.meta.name) + '_cut_list.csv', data: cutCSV() }]); $('#eGuide').onclick = () => window.__guide && window.__guide.save(); $('#eSpec').onclick = () => deliver('spec', [{ name: safe(S.M.meta.name) + '.spec.json', data: jsonOf(S.spec) }]); info();
}
function info() { try { let np = 0, ns = 0, mesh = 0; S.M.defs.forEach(d => { const ps = CAD.exporter.printPieces(d, mult(), S.ex.bed, S.ex.split); np += ps.length * d.qty; if (ps.length > 1) ns++; if (ps.some(p => p.over)) mesh++; }); const { plates, over } = CAD.exporter.nest(S.M, mult(), S.ex.bed, S.ex.split); $('#exInfo').innerHTML = `<div class="card">${np} printed pieces · ${ns} part types split · ${plates.length} plate(s)${over.length ? ' · <span class="fail">' + over.length + ' oversize (round parts or too tall)</span>' : ''}</div>`; } catch (e) { $('#exInfo').textContent = ''; } }

/* ---------------- cut list modal ---------------- */
function showCut() {
  const plan = CAD.lumberPlan(S.M), rows = CAD.cutList(S.M).sort((a, b) => CAD.GROUPS.findIndex(g => g.id === a.grp) - CAD.GROUPS.findIndex(g => g.id === b.grp));
  let tw = 0; rows.forEach(r => tw += r.mass * r.qty);
  const boardFrom = {};
  plan.boards.forEach(b => b.cuts.forEach(c => { (boardFrom[c.id] = boardFrom[c.id] || new Set()).add(b.label); }));
  $('#mtitle').textContent = 'Lumber & cut list'; $('#mextra').textContent = plan.boards.length + ' boards · ' + rows.length + ' part types · ' + lb(tw);
  const buyHtml = `<p class="card" style="margin-top:8px">Parts are nested onto the fewest boards of each stock size (8′ / 10′ / 12′, ⅛″ kerf). Each board below has its own cut list — buy these, then cut the listed blanks from them.</p>
    <h3>Shopping list</h3>
    <table><tr><th>Buy</th><th>Material</th><th class="n">Blanks</th></tr>${plan.summary.map(s => `<tr><td><b>${esc(s.buyLine)}</b></td><td>${esc(s.mat)}</td><td class="n">${s.pieces}</td></tr>`).join('')}</table>
    <h3>Cut list per board</h3>
    ${plan.boards.map(b => `<div class="card" style="margin:10px 0"><b>Board ${b.id}: ${esc(b.label)}</b> · ${esc(b.mat)}${b.note ? ' · ' + esc(b.note) : ''}
      <table style="margin-top:6px"><tr><th>Part blank</th><th>Finished T×W×L</th><th class="n">Cut length</th></tr>
      ${b.cuts.map(c => `<tr><td>${esc(c.name)}</td><td>${esc(c.finished)}</td><td class="n">${esc(c.len)}</td></tr>`).join('')}
      </table></div>`).join('')}`;
  let last = '', i = 0;
  const partsHtml = `<p class="card" style="margin-top:8px">Finished part sizes (nearest 1/16″). The <b>From board</b> column links each part type to the shopping-list boards above.</p>
    <table><tr><th class="n">#</th><th>Part</th><th class="n">Qty</th><th class="n">T</th><th class="n">W</th><th class="n">L</th><th>From board</th><th>Material</th><th>Notes</th></tr>${rows.map(r => {
    let h = ''; if (r.grp !== last) { last = r.grp; h = `<tr><td colspan="9" style="background:var(--panel2);font-weight:600">${esc(gname(r.grp))}</td></tr>`; }
    const from = boardFrom[r.id] ? [...boardFrom[r.id]].join('; ') : '—';
    return h + `<tr><td class="n">${++i}</td><td>${esc(r.name)}</td><td class="n">${r.qty}</td><td class="n">${inch(r.T)}</td><td class="n">${inch(r.W)}</td><td class="n">${inch(r.L)}</td><td>${esc(from)}</td><td>${esc(r.mat)}</td><td>${esc(note(r.spec))}</td></tr>`;
  }).join('')}</table>`;
  $('#mbody').innerHTML = `<div class="mtabs"><button type="button" class="btn sm on" data-mtab="buy">1 · Buy list</button><button type="button" class="btn sm" data-mtab="parts">2 · Parts</button></div>
    <div class="mtab on" id="mtab-buy">${buyHtml}</div><div class="mtab" id="mtab-parts">${partsHtml}</div>`;
  $$('#mbody [data-mtab]').forEach(b => b.onclick = () => {
    $$('#mbody [data-mtab]').forEach(x => x.classList.toggle('on', x === b));
    $$('#mbody .mtab').forEach(p => p.classList.toggle('on', p.id === 'mtab-' + b.dataset.mtab));
  });
  $('#modal').style.display = 'block'; $('#mcsv').onclick = () => deliver('cut_list', [{ name: safe(S.M.meta.name) + '_cut_list.csv', data: cutCSV() }]);
}
$('#mclose').onclick = () => $('#modal').style.display = 'none';

/* ---------------- review ---------------- */
function renderReview() { $('#p-review').innerHTML = `<h3>Design checks</h3><button class="btn pri sm" id="rRun" style="width:100%">Run all checks</button><div id="rOut"></div><h3>AI loop log</h3><div class="log" id="rLog">${S.ai.log.length ? S.ai.log.map(esc).join('<br>') : 'No AI run yet.'}</div>`; $('#rRun').onclick = runChecks; }
function runChecks() {
  const out = $('#rOut'); out.innerHTML = '<div class="card">Running…</div>';
  setTimeout(() => { const M = S.M, t0 = performance.now(), man = CAD.manifoldReport(M).filter(r => r.bad), it = CAD.interference(M), fl = CAD.jointFill(M), bad = fl.filter(r => r.ratio < .999); fillRows = fl;
    const { plates, over } = CAD.exporter.nest(M, mult(), S.ex.bed, S.ex.split); let rtBad = 0, n = 0; [...M.defs.values()].slice(0, 8).forEach(d => CAD.exporter.printPieces(d, 1, [99999, 99999, 99999], false).forEach(p => { const back = CAD.stlParse(CAD.stlBinary([p.pos])); const g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(back, 3)); n++; if (Math.abs(CAD.volume(g) - d.vol) / Math.max(1, d.vol) > .001) rtBad++; }));
    const row = (ok, t, d) => `<tr><td class="${ok ? 'pass' : 'fail'}">${ok ? '✓' : '✗'}</td><td>${t}</td><td>${d}</td></tr>`, exact = [...M.defs.values()].filter(d => d.solid.exact).length;
    out.innerHTML = `<table>${row(!S.lastErrors.length, 'Spec', S.lastErrors.length ? esc(S.lastErrors.slice(0, 3).join('; ')) : 'valid' + (S.lastWarnings.length ? ' · ' + S.lastWarnings.length + ' warning(s)' : ''))}
      ${row(!man.length, 'Watertight meshes', man.length ? esc(man.map(r => r.id).join(', ')) : 'all ' + M.defs.size + ' part meshes closed &amp; manifold')}
      ${row(!it.length, 'Part-to-part interference', it.length ? it.length + ' pairs: ' + esc(it.slice(0, 3).map(x => x.a + '×' + x.b).join('; ')) : 'exact solid test on ' + exact + ' solid part types: no overlap')}
      ${row(!bad.length, 'Joint fill (' + fl.length + ' mortises, dados, grooves…)', bad.length ? bad.length + ' not filled: ' + esc(bad.slice(0, 3).map(r => r.part + '/' + r.tag).join('; ')) : fl.length ? 'every cut that should hold a mating part is filled 100 %' : 'no "fill" joints declared')}
      ${row(!over.length, 'Fits ' + S.ex.bed.join('×') + ' bed at 1:' + S.ex.scale, over.length ? over.length + ' oversize pieces (round parts are not split)' : plates.length + ' plate(s) hold every piece')}
      ${row(!rtBad, 'STL round-trip', n + ' parts exported and re-read; volume matches within 0.1 %')}${row(true, 'Elapsed', fmt(performance.now() - t0) + ' ms')}</table>`; }, 20);
}

/* ---------------- Spec editor ---------------- */
function renderSpecPane() {
  $('#p-spec').innerHTML = `<div class="row"><button class="btn pri sm" id="spApply">Apply</button><button class="btn sm" id="spFmt">Format</button><button class="btn sm" id="spDl">Download</button><label class="btn sm" style="margin:0">Upload<input type="file" id="spUp" accept=".json,application/json" hidden></label></div>
  <textarea id="specTxt" spellcheck="false" style="width:100%;height:46vh;font:12px/1.35 ui-monospace,Menlo,Consolas,monospace;background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:8px;resize:vertical"></textarea><div id="specErr"></div>
  <div class="card"><b>Edit &amp; apply</b>This JSON is the whole model. Change a number or add a part and press Apply. See <code>docs/SPEC.md</code>.</div>`;
  $('#spApply').onclick = () => { let spec; try { spec = JSON.parse($('#specTxt').value); } catch (e) { S.lastErrors = ['JSON: ' + e.message]; S.lastWarnings = []; return renderSpecErrors(); } if (loadSpec(spec, {})) toast('Applied'); };
  $('#spFmt').onclick = () => { try { $('#specTxt').value = JSON.stringify(JSON.parse($('#specTxt').value), null, 1); } catch (e) { toast('Not valid JSON: ' + e.message); } };
  $('#spDl').onclick = () => deliver('spec', [{ name: safe(S.M.meta.name) + '.spec.json', data: $('#specTxt').value }]);
  $('#spUp').onchange = e => { const f = e.target.files[0]; if (!f) return; f.text().then(t => { $('#specTxt').value = t; $('#spApply').click(); }); };
}
function setSpecText() { const t = $('#specTxt'); if (t && S.spec) t.value = jsonOf(S.spec); }
function renderSpecErrors() { const el = $('#specErr'); if (!el) return; el.innerHTML = (S.lastErrors.length ? `<div class="card fail"><b>Errors</b>${S.lastErrors.slice(0, 12).map(esc).join('<br>')}</div>` : '') + (S.lastWarnings.length ? `<div class="card warn"><b>Warnings</b>${S.lastWarnings.slice(0, 8).map(esc).join('<br>')}</div>` : ''); }

/* ---------------- AI: picture → design (builder ⇄ critic loop) ---------------- */
const AI_MODELS = [
  { id: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5', hint: 'Recommended' },
  { id: 'claude-sonnet-5-5', label: 'Claude Sonnet 5.5', hint: 'Newest Sonnet' },
  { id: 'claude-opus-4-6', label: 'Claude Opus 4.6', hint: 'Highest quality' },
  { id: 'claude-opus-4-5', label: 'Claude Opus 4.5', hint: 'High quality' },
  { id: 'claude-haiku-4-5', label: 'Claude Haiku 4.5', hint: 'Faster / cheaper' }
];
function aiLog(m) { S.ai.log.push(m); const el = $('#aiLog'); if (el) { el.innerHTML = S.ai.log.map(esc).join('<br>'); el.scrollTop = 1e9; } const r = $('#rLog'); if (r) r.innerHTML = S.ai.log.map(esc).join('<br>'); }
function downscale(file, max) { return new Promise((res, rej) => { const img = new Image(), url = URL.createObjectURL(file); img.onload = () => { const k = Math.min(1, max / Math.max(img.width, img.height)), c = document.createElement('canvas'); c.width = Math.round(img.width * k); c.height = Math.round(img.height * k); c.getContext('2d').drawImage(img, 0, 0, c.width, c.height); URL.revokeObjectURL(url); res(c.toDataURL('image/jpeg', .86)); }; img.onerror = () => rej(new Error('could not read the image')); img.src = url; }); }
async function setImage(file) { if (!file || !/^image\//.test(file.type)) return toast('Please choose an image file'); try { const u = await downscale(file, 1568); S.ai.img = u; const prev = $('#aiPrev'); if (prev) { prev.src = u; prev.style.display = 'block'; } const t = $('#aiDropT'); if (t) t.textContent = file.name || 'pasted image'; } catch (e) { toast(e.message); } }
const frames = n => new Promise(r => { const f = () => --n <= 0 ? r() : requestAnimationFrame(f); requestAnimationFrame(f); });
function setAIConn(text, ok) { const el = $('#aiConn'); if (!el) return; el.textContent = text; el.className = 'aiConn' + (ok === true ? ' ok' : ok === false ? ' bad' : ''); }
async function checkConnection() {
  const kind = $('#aiProv') && $('#aiProv').value, model = $('#aiModel') && $('#aiModel').value;
  if (!kind) return; setAIConn('Checking ' + model + '…');
  try {
    if (kind === 'proxy') {
      const r = await fetch('/api/status'); const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error('proxy not reachable');
      if (!j.hasKey) throw new Error('server is up but ANTHROPIC_API_KEY is not set');
      setAIConn('Connected · ' + model + ' via server proxy', true);
    } else if (kind === 'anthropic') {
      const key = $('#aiKey').value.trim(); if (!key) throw new Error('paste an Anthropic API key');
      const r = await fetch('https://api.anthropic.com/v1/models', { headers: { 'x-api-key': key, 'anthropic-version': '2023-06-01', 'anthropic-dangerous-direct-browser-access': 'true' } });
      if (!r.ok) throw new Error('Anthropic rejected the key (' + r.status + ')');
      setAIConn('Connected · API key valid · ' + model, true);
    } else setAIConn('Using Claude on this page · ' + (model || 'account default'), true);
  } catch (e) { setAIConn('Not connected: ' + e.message, false); }
}
function openAI() { $('#aiBox').classList.add('open'); $('#bAI').classList.add('on'); checkConnection(); syncAIFocus(); }
function closeAI() { $('#aiBox').classList.remove('open'); $('#bAI').classList.remove('on'); }
function syncAIFocus() {
  const el = $('#aiFocus'); if (!el) return;
  const ids = selectedPartIds();
  if (!ids.length) { el.innerHTML = '<div class="card">No parts selected — changes apply to the <b>whole design</b>. Shift-click parts in the viewer to focus a revise.</div>'; return; }
  const names = ids.map(id => (S.M.defs.get(id) || {}).name || id);
  el.innerHTML = `<div class="card"><b>Focus</b>${esc(names.join(', '))}<div class="chk" style="margin-top:6px"><input type="checkbox" id="aiFocusOnly" checked><label for="aiFocusOnly">Limit revise to these parts</label></div></div>`;
}
function renderAI() {
  const inClaude = !!window.claude, remembered = (() => { try { return localStorage.getItem('image-to-cad.key') || ''; } catch (e) { return ''; } })();
  const hosted = location.protocol !== 'file:';
  $('#p-ai').innerHTML = `
  <h3>Revise this design</h3>
  <div id="aiFocus"></div>
  <textarea id="aiRevise" rows="4" placeholder="e.g. make it 4&quot; taller, add a third drawer, change the selected legs to 1 1/2&quot; square maple" style="width:100%;background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:6px"></textarea>
  <button class="btn pri" id="aiRev" style="width:100%;margin-top:6px">Apply changes</button>
  <h3>From a picture</h3>
  <div id="aiDrop" style="border:2px dashed var(--line);border-radius:10px;padding:18px;text-align:center;cursor:pointer;background:var(--panel2)"><div id="aiDropT" style="font-weight:600">Drop, paste or click to upload a photo</div><div style="color:var(--dim);margin-top:4px">Generates a new design from the image</div><input type="file" id="aiFile" accept="image/*" hidden><img id="aiPrev" style="display:none;max-width:100%;max-height:200px;margin:8px auto 0;border-radius:6px"></div>
  <textarea id="aiHints" rows="2" placeholder="Optional brief: e.g. overall height 33 1/2&quot;, solid oak, two drawers" style="width:100%;margin-top:8px;background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:6px"></textarea>
  <div class="row"><label>Max rounds</label><select id="aiRounds" class="btn"><option>1</option><option>2</option><option selected>3</option><option>4</option><option>5</option><option>6</option></select><div class="chk" style="margin:0"><input type="checkbox" id="aiVis"><label for="aiVis">visual critic</label></div></div>
  <div class="grid2"><button class="btn pri" id="aiGo">Generate from picture</button><button class="btn" id="aiStop" disabled>Stop</button></div>
  <details style="margin-top:14px"><summary style="cursor:pointer;color:var(--dim);font-size:11px;letter-spacing:.06em;text-transform:uppercase">Connection &amp; model</summary>
  <div class="row"><label>Provider</label><select id="aiProv" class="btn" style="flex:1"><option value="proxy"${hosted && !inClaude ? ' selected' : ''}>Server proxy (Vercel / npm run serve)</option><option value="anthropic"${!hosted && !inClaude ? ' selected' : ''}>Claude API key (browser)</option>${inClaude ? '<option value="artifact" selected>Claude (this page, your account)</option>' : ''}</select></div>
  <div class="row" id="aiKeyRow"><label>API key</label><input id="aiKey" type="password" placeholder="sk-ant-…" value="${esc(remembered)}" style="flex:1;background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:4px 6px"></div>
  <div class="row"><label>Model</label><select id="aiModel" class="btn" style="flex:1">${AI_MODELS.map((m, i) => `<option value="${esc(m.id)}"${i === 0 ? ' selected' : ''}>${esc(m.label)} — ${esc(m.hint)}</option>`).join('')}</select></div>
  <div class="chk"><input type="checkbox" id="aiRem"><label for="aiRem">remember key in this browser (localStorage)</label></div>
  <button class="btn sm" id="aiPing" style="width:100%">Check connection</button></details>
  <div class="log" id="aiLog" style="max-height:220px;overflow:auto;margin-top:8px">${S.ai.log.map(esc).join('<br>')}</div>`;
  syncAIFocus(); if (S.ai.img) { const prev = $('#aiPrev'); prev.src = S.ai.img; prev.style.display = 'block'; $('#aiDropT').textContent = 'Picture ready'; }
  const drop = $('#aiDrop'); drop.onclick = () => $('#aiFile').click(); $('#aiFile').onchange = e => setImage(e.target.files[0]);
  drop.ondragover = e => { e.preventDefault(); drop.style.borderColor = 'var(--acc)'; }; drop.ondragleave = () => drop.style.borderColor = ''; drop.ondrop = e => { e.preventDefault(); drop.style.borderColor = ''; setImage(e.dataTransfer.files[0]); };
  const sync = () => { $('#aiKeyRow').style.display = $('#aiProv').value === 'anthropic' ? 'flex' : 'none'; checkConnection(); };
  $('#aiProv').onchange = sync; $('#aiModel').onchange = checkConnection; $('#aiKey').onchange = checkConnection; $('#aiPing').onclick = checkConnection; sync();
  $('#aiGo').onclick = () => runAI('design'); $('#aiRev').onclick = () => runAI('revise'); $('#aiStop').onclick = () => S.ai.abort && S.ai.abort.abort();
}
addEventListener('paste', e => { const f = [...(e.clipboardData ? e.clipboardData.files : [])].find(f => /^image\//.test(f.type)); if (f) { openAI(); setImage(f); } });
function viewNow(name) { viewTo(name); if (tween) { camera.position.copy(tween.p1); controls.target.copy(tween.t1); tween = null; controls.update(); S.need = true; } }
async function runAI(task) {
  if (S.ai.busy) return; task = task || 'design';
  const kind = $('#aiProv').value, key = $('#aiKey').value.trim(), model = $('#aiModel').value;
  if (kind === 'anthropic' && !key) return toast('Paste your Anthropic API key');
  if (task === 'design' && !S.ai.img) return toast('Choose a picture first');
  if (task === 'revise' && !S.spec) return toast('Load a design first');
  const hints = task === 'revise' ? $('#aiRevise').value.trim() : $('#aiHints').value.trim();
  if (task === 'revise' && !hints) return toast('Describe the changes you want');
  const focusIds = (task === 'revise' && $('#aiFocusOnly') && $('#aiFocusOnly').checked) ? selectedPartIds() : [];
  const focusParts = focusIds.map(id => ({ id, name: (S.M.defs.get(id) || {}).name || id }));
  if ($('#aiRem').checked) { try { localStorage.setItem('image-to-cad.key', key); } catch (e) { } }
  let aiDocId = null;
  if (task === 'design') { persistActive(); aiDocId = addDoc(blankSpec('AI design'), { name: 'AI design' }); refreshDocSel(); }
  const adoptAIDoc = () => { if (aiDocId) { S.docId = aiDocId; aiDocId = null; refreshDocSel(); } };
  S.ai.busy = true; S.ai.log = []; $('#aiGo').disabled = true; $('#aiRev').disabled = true; $('#aiStop').disabled = false; const ac = new AbortController(); S.ai.abort = ac;
  aiLog('Using ' + model + ' (' + (kind === 'proxy' ? 'server proxy' : kind === 'anthropic' ? 'browser API key' : 'this page') + ')' + (focusParts.length ? ' · focused on ' + focusParts.map(p => p.name).join(', ') : ''));
  try {
    const res = await CAD.vision.run({ image: S.ai.img, hints, task, focusParts, prevSpec: task === 'revise' ? S.spec : null, provider: { kind, apiKey: key, model }, maxRounds: +$('#aiRounds').value, visual: $('#aiVis').checked, signal: ac.signal, onLog: aiLog,
      onSpec: (spec) => { adoptAIDoc(); if (loadSpec(spec, {}, true)) { viewNow('iso'); setSpecText(); } }, render: async (spec) => { adoptAIDoc(); loadSpec(spec, {}, true); viewNow('iso'); await frames(4); return renderer.domElement.toDataURL('image/jpeg', .85); } });
    res.spec.__ai = true; adoptAIDoc(); loadSpec(res.spec, {}, true); viewNow('iso'); setSpecText();
    toast(res.rep.ok ? 'Design ready: passes every check' : 'Design loaded with remaining issues, see the log'); closeAI(); setTab('insp');
  } catch (e) {
    aiLog('Error: ' + (e.name === 'AbortError' ? 'stopped' : e.message)); toast('AI run failed: see the log');
    if (aiDocId) { delete S.docs[aiDocId]; writeWS(); refreshDocSel(); }
  }
  finally { S.ai.busy = false; $('#aiGo').disabled = false; $('#aiRev').disabled = false; $('#aiStop').disabled = true; }
}


/* ---------------- UI wiring ---------------- */
function toast(t) { const e = $('#toast'); e.textContent = t; e.style.display = 'block'; clearTimeout(toast.t); toast.t = setTimeout(() => e.style.display = 'none', 2600); }
$$('#views button[data-v]').forEach(b => b.onclick = () => viewTo(b.dataset.v)); $('#bFit').onclick = () => fitView(); $('#exs').oninput = e => { S.exF = +e.target.value; applyTransforms(); };
$('#cmode').onchange = e => { S.mode = e.target.value; updateVisuals(); };
$('#bEdge').classList.add('on');
$('#bEdge').onclick = e => { const btn = e.currentTarget; S.edges = !S.edges; btn.classList.toggle('on', S.edges); updateVisuals(); };
$('#bSec').onclick = e => { const btn = e.currentTarget; S.sec.on = !S.sec.on; btn.classList.toggle('on', S.sec.on); if (S.sec.on && !S.sec.off) S.sec.off = Math.round(sceneBox().getCenter(V(0, 0, 0))[S.sec.axis]); applySection(); setTab('motion'); };
$('#bMeas').onclick = e => { const btn = e.currentTarget; S.meas.on = !S.meas.on; btn.classList.toggle('on', S.meas.on); applyNavMode(); if (!S.meas.on) clearMeasure(); toast(S.meas.on ? 'Measure: click two points (snaps to vertices)' : 'Measure off'); };
$('#bBom').onclick = showCut; $('#bExp').onclick = () => setTab('export'); $('#tq').oninput = e => { S.q = e.target.value; buildTree(); }; $('#bShowAll').onclick = showAll;
$('#bNew').onclick = newDesign; $('#bDup').onclick = duplicateDesign; $('#bRename').onclick = renameDesign; $('#bDel').onclick = deleteDesign;
$('#docsel').onchange = e => { if (e.target.value && e.target.value !== S.docId) openDoc(e.target.value); };
function setPanels() {
  const m = $('main'); m.classList.toggle('left-off', !S.leftOn); m.classList.toggle('right-off', !S.rightOn);
  $('#edgeL').textContent = S.leftOn ? '‹' : '›'; $('#edgeR').textContent = S.rightOn ? '›' : '‹';
  $('#left').classList.toggle('open', S.leftOn); $('#right').classList.toggle('open', S.rightOn); S.need = true;
}
$('#edgeL').onclick = () => { S.leftOn = !S.leftOn; setPanels(); };
$('#edgeR').onclick = () => { S.rightOn = !S.rightOn; setPanels(); };
$('#bLeft').onclick = () => { S.leftOn = !S.leftOn; setPanels(); };
$('#bRight').onclick = () => { S.rightOn = !S.rightOn; setPanels(); };
$$('#navMode button').forEach(b => b.onclick = () => { S.nav = b.dataset.nav; applyNavMode(); });
$$('#movePlane button').forEach(b => b.onclick = () => { S.movePlane = b.dataset.plane; applyNavMode(); });
$('#bAI').onclick = () => { $('#aiBox').classList.contains('open') ? closeAI() : openAI(); };
$('#aiClose').onclick = closeAI;
function setTab(t) {
  if (t === 'ai') { openAI(); return; }
  S.rightOn = true; setPanels();
  $$('.tabs button').forEach(b => b.classList.toggle('on', b.dataset.t === t)); $$('.pane').forEach(p => p.classList.toggle('on', p.id === 'p-' + t)); $('#right').classList.add('open');
}
$$('.tabs button').forEach(b => b.onclick = () => setTab(b.dataset.t));
applyNavMode();
let exAnim = null;
addEventListener('keydown', e => {
  if ($('#aiBox').classList.contains('open') && e.key === 'Escape') { e.preventDefault(); closeAI(); return; }
  const mod = e.metaKey || e.ctrlKey, k = e.key.toLowerCase();
  if (mod && k === 'z' && !e.shiftKey) { if (!/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) { e.preventDefault(); undo(); } return; }
  if (mod && (k === 'y' || (k === 'z' && e.shiftKey))) { if (!/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) { e.preventDefault(); redo(); } return; }
  if (/INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName) && document.activeElement.type !== 'range') return; if ($('#guide').style.display === 'flex') return;
  if (k === 'f') focusSel(); else if (k === 'e') { const to = S.exF > .5 ? 0 : 1, from = S.exF, t0 = performance.now(); cancelAnimationFrame(exAnim); const st = () => { const t = Math.min(1, (performance.now() - t0) / 700); S.exF = from + (to - from) * (t * t * (3 - 2 * t)); $('#exs').value = S.exF; applyTransforms(); if (t < 1) exAnim = requestAnimationFrame(st); }; st(); }
  else if (k === 's') $('#bSec').click(); else if (k === 'm') $('#bMeas').click(); else if (k === 'escape') { setSel([]); clearMeasure(); S.iso = null; updateVisuals(); } else if (k === 'h') { if (e.altKey) showAll(); else { S.sel.forEach(R => S.hiddenDef.add(R.def.id)); setSel([]); updateVisuals(); buildTree(); } }
  else if (k === 'i') { if (S.sel.size) { S.iso = new Set(S.sel); updateVisuals(); } } else if (k === ' ') { e.preventDefault(); playT ? stopPlay() : startPlay(); } else if ('12345'.includes(k) && k) viewTo(['iso', 'front', 'right', 'top', 'back'][+k - 1]);
  else if (k === '[') { S.leftOn = !S.leftOn; setPanels(); } else if (k === ']') { S.rightOn = !S.rightOn; setPanels(); }
});


/* ---------------- gizmo + loop ---------------- */
const gz = new T.Scene(), gcam = new T.OrthographicCamera(-1.6, 1.6, 1.6, -1.6, .1, 10); gcam.up.set(0, 0, 1);
[['x', 0xe5484d, [1, 0, 0]], ['y', 0x30a46c, [0, 1, 0]], ['z', 0x3e63dd, [0, 0, 1]]].forEach(([n, c, d]) => { gz.add(new T.Line(new T.BufferGeometry().setFromPoints([V(0, 0, 0), V(...d)]), new T.LineBasicMaterial({ color: c })));
  const cvs = document.createElement('canvas'); cvs.width = cvs.height = 64; const x = cvs.getContext('2d'); x.fillStyle = '#' + c.toString(16); x.font = 'bold 44px sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(n.toUpperCase(), 32, 34);
  const sp = new T.Sprite(new T.SpriteMaterial({ map: new T.CanvasTexture(cvs), depthTest: false })); sp.position.set(d[0] * 1.25, d[1] * 1.25, d[2] * 1.25); sp.scale.set(.5, .5, .5); gz.add(sp); });
function resize() { const r = wrap.getBoundingClientRect(); renderer.setSize(r.width, r.height, false); camera.aspect = r.width / Math.max(1, r.height); camera.updateProjectionMatrix(); S.need = true; } new ResizeObserver(resize).observe(wrap);
function frame(now) {
  requestAnimationFrame(frame);
  if (tween) { const t = Math.min(1, (now - tween.t) / tween.d), e = t * t * (3 - 2 * t); camera.position.lerpVectors(tween.p0, tween.p1, e); controls.target.lerpVectors(tween.t0, tween.t1, e); if (t >= 1) tween = null; S.need = true; }
  let an = false; S.R.forEach(R => { if (R.anim < 1) { R.anim = Math.min(1, R.anim + .035); an = true; } }); if (an) applyTransforms();
  controls.update(); if (S.meas.pts.length === 2) placeMeasureLabel(); if (!S.need || window.__pause) return; S.need = false;
  renderer.setScissorTest(false); renderer.setViewport(0, 0, wrap.clientWidth, wrap.clientHeight); renderer.autoClear = true; renderer.render(scene, camera);
  const g = 96; renderer.autoClear = false; renderer.clearDepth(); renderer.setScissorTest(true); renderer.setScissor(8, 8, g, g); renderer.setViewport(8, 8, g, g); gcam.position.copy(camera.position).sub(controls.target).setLength(4); gcam.lookAt(0, 0, 0);
  renderer.clippingPlanes = []; renderer.render(gz, gcam); renderer.clippingPlanes = S.sec.on ? [plane] : []; renderer.setScissorTest(false);
  const h = $('#hudTL'); if (h) h.textContent = `${S.R.filter(R => R.mesh.visible).length}/${S.R.length} pieces shown · ${S.sel.size ? S.sel.size + ' selected' : 'nothing selected'}`; const hr = $('#hudTR'); if (hr) hr.textContent = S.sec.on ? `Section ${S.sec.axis.toUpperCase()} = ${inch(S.sec.off)}` : '';
}
requestAnimationFrame(frame);


/* ---------------- boot ---------------- */
async function loadExamples() {
  if (window.EXAMPLES) { S.examples = window.EXAMPLES; return; }
  try { const idx = await (await fetch('examples/index.json')).json(); for (const e of idx) S.examples[e.id] = await (await fetch('examples/' + e.file)).json(); } catch (e) { /* file:// or offline: fall back to the built-in example */ }
  if (!Object.keys(S.examples).length) S.examples = { 'plant-stand': CAD.vision.EXAMPLE };
}
function loadExample(id) {
  const ex = S.examples[id]; if (!ex) return false;
  const source = 'example:' + id;
  let doc = Object.values(S.docs).find(d => d.source === source);
  const spec = JSON.parse(JSON.stringify(ex)); spec.__trusted = true;
  if (doc) { doc.spec = spec; doc.name = spec.name || id; doc.ov = {}; doc.updated = Date.now(); }
  else doc = S.docs[addDoc(spec, { name: spec.name || id, source })];
  return openDoc(doc.id);
}
function seedWorkspace() {
  Object.entries(S.examples).forEach(([id, ex]) => {
    const spec = JSON.parse(JSON.stringify(ex)); spec.__trusted = true;
    addDoc(spec, { name: spec.name || id, source: 'example:' + id });
  });
}
function boot() {
  const lb = $('#lbar'); lb.style.width = '35%';
  setTimeout(async () => {
    await loadExamples();
    const ws = readWS();
    if (ws && ws.docs && Object.keys(ws.docs).length) {
      S.docs = ws.docs;
      Object.values(S.docs).forEach(d => { if (!d.id) d.id = uid(); });
    } else seedWorkspace();
    renderSpecPane(); renderAI();
    const want = new URLSearchParams(location.search).get('example');
    lb.style.width = '70%'; resize();
    if (want && S.examples[want]) loadExample(want);
    else {
      const prefer = (ws && ws.activeId && S.docs[ws.activeId]) ? ws.activeId
        : (Object.values(S.docs).find(d => d.source === 'example:sideboard') || Object.values(S.docs)[0] || {}).id;
      if (prefer) openDoc(prefer); else { seedWorkspace(); openDoc(Object.keys(S.docs)[0]); }
    }
    if (CAD.makeGuide) window.__guide = CAD.makeGuide({ T, S, CAD, renderer, scene, camera, getMat, geomOf, TEX, toast, deliver, safe });
    lb.style.width = '100%'; setTimeout(() => { $('#loading').style.display = 'none'; S.need = true; }, 150);
  }, 30);
}
$('#bGuide').onclick = () => window.__guide && window.__guide.open();
window.__cad = { S, T, CAD, loadSpec, loadExample, newDesign, duplicateDesign, renameDesign, deleteDesign, openDoc, viewTo, viewNow, fitView, undo, redo, applyMotion, applySection, setSel, selectDef, exportSelected, exportAll, exportAssembly, exportPlates, exportGroup, runChecks, gotoStep, showAll, camera, controls, renderer, scene, root, sceneBox, updateVisuals, showCut, setTab, deliver, runAI, setImage, aiLog };
boot();
})();
