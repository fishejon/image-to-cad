/* guide.js — step-by-step build guide (renders with the live model so dimensions always match the parameters) */
(function (root) {
'use strict';
const CAD = root.CAD;
const N = v => CAD.fmtInch(v);

const escH = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
CAD.sanitizeHTML = s => escH(s).replace(/&lt;(\/?)(b|i|br)&gt;/g, '<$1$2>');
/* Guide pages for the current model. A spec may carry its own hand-written "guide" array (the sideboard does); otherwise pages are generated
   from the parts' tagged joinery features and the assembly steps. */
function guideSteps(M) {
  const trusted = !!M.spec.__trusted, clean = t => trusted ? String(t) : CAD.sanitizeHTML(t), E = escH, S = [], add = o => { o.n = S.length + 1; S.push(o); return o; };
  const has = id => M.defs.has(id), defs = [...M.defs.values()], gi = id => Math.max(0, CAD.GROUPS.findIndex(g => g.id === id));
  if (Array.isArray(M.spec.guide) && M.spec.guide.length) {
    const inch = t => CAD.inchifyText(t);
    M.spec.guide.forEach(g => { const o = Object.assign({}, g); o.text = (o.text || []).map(t => clean(inch(t))); if (o.tip) o.tip = clean(inch(o.tip)); if (o.chk) o.chk = clean(inch(o.chk)); o.title = E(inch(o.title)); o.phase = E(o.phase || ''); o.tools = (o.tools || []).map(t => E(inch(t)));
      if (o.focus) { o.focus = o.focus.filter(has); if (!o.focus.length) return; } if (o.show) { o.show = o.show.filter(s => has(s.def)); if (!o.show.length) return; } if (o.parts) o.parts = o.parts.filter(p => has(p.def)); if (o.kind === 'asm' && !(o.asm >= 0 && o.asm < M.steps.length)) return; add(o); });
    if (S.length) return S;
  }
  add({ kind: 'hero', phase: 'Welcome', title: E(M.meta.name), text: [].concat(M.meta.description ? [E(M.meta.description)] : [], [`Finished size <b>${CAD.fmtInch3(M.size)}</b>: ${defs.length} part types, ${M.insts.length} pieces.`,
    'How to read the pictures: <span style="color:#e86a00">orange parts</span> are new in this step; <span style="color:#e86a00">orange boxes</span> inside a part are material to remove; <span style="color:#18a34a">green boxes</span> are tenons and tongues you leave standing.'], M.meta.assumptions.slice(0, 2).map(a => 'Assumed: ' + E(a))), tools: [], tip: 'Dry-fit every joint before gluing.' });
  add({ kind: 'flat', phase: 'Welcome', title: 'Parts overview', text: [`<b>${defs.length} part types, ${M.insts.length} pieces.</b> Each tile shows the part name and the quantity you need.`, 'Part names match the cut list on the next page.'], tools: [], tip: 'Label every part with its name and an orientation arrow as soon as you make it.' });
  add({ kind: 'cutlist', phase: 'Prepare', title: 'Cut list & milling', text: [] });
  defs.filter(d => (d.solid.feat || []).some(f => f.label)).sort((a, b) => gi(a.grp) - gi(b.grp)).slice(0, 22).forEach(d => {
    const feats = d.solid.feat.filter(f => f.label), tags = [...new Set(feats.map(f => f.tag))], seen = new Set(), tx = [];
    feats.forEach(f => { if (seen.has(f.label)) return; seen.add(f.label); const lab = E(CAD.inchifyText(f.label)); tx.push(f.kind === 'cut' ? `Remove <b>${lab}</b> (orange): mark it with a knife and gauge, remove the waste, then pare to the lines.` : `Leave <b>${lab}</b> (green) standing: saw the cheeks and shoulders, then pare it to fit its mating part.`); });
    (d.notes || []).forEach(n => tx.push(E(CAD.inchifyText(n)))); tx.push(`Make <b>${d.qty}</b> of these.`);
    add({ kind: 'part', phase: 'Joinery', title: 'Make the joints: ' + E(CAD.inchifyText(d.name)), focus: [d.id], tags, dir: [.8, .85, .6], zoom: 'first', parts: [{ def: d.id, qty: d.qty }], text: tx.slice(0, 6), tools: d.tools.length ? d.tools.map(t => E(CAD.inchifyText(t))) : ['Marking knife', 'Square', 'Chisels', 'Saw'], tip: 'Cut one test joint in scrap first.', chk: 'Dry-fit with its mating part before any glue.' });
  });
  M.steps.forEach((s, k) => { if (!M.insts.some(i => i.step === k)) return; const nt = (s.notes || []).map(E);
    add({ kind: 'asm', phase: 'Assembly', title: E(s.title), asm: k, dir: [.7, -.9, .6], text: nt.length ? nt : ['Dry-fit the new parts first.', 'Glue only where the joints meet and clamp until set.', 'Check the assembly is square and flat before the next step.'], tools: (s.tools || []).length ? s.tools.map(E) : ['Glue', 'Clamps', 'Square'], tip: s.tip ? E(s.tip) : undefined, chk: s.check ? E(s.check) : undefined }); });
  add({ kind: 'hero', phase: 'Finish', title: 'Finish and enjoy', final: true, text: ['Sand, finish and check every moving part.', 'Keep this guide with the spec file so the design can be changed and rebuilt.'], tools: [] });
  return S;
}
CAD.guideSteps = guideSteps;

CAD.makeGuide = function (ctx) {
  const T = ctx.T, S = ctx.S, V = (x, y, z) => new T.Vector3(x, y, z), $ = s => document.querySelector(s);
  const gs = new T.Scene(); gs.environment = ctx.scene.environment; gs.add(new T.HemisphereLight(0xffffff, 0x8a8478, .62)); const sun = new T.DirectionalLight(0xfff4e6, 1.0); sun.position.set(-1400, -2200, 2600); gs.add(sun); const f2 = new T.DirectionalLight(0xdbe6ff, .35); f2.position.set(2000, 1200, 900); gs.add(f2);
  const cam = new T.PerspectiveCamera(28, 1, 5, 40000); cam.up.set(0, 0, 1); const lineMat = new T.LineBasicMaterial({ color: 0x24160d, transparent: true, opacity: .42 });
  let steps = null, pages = null, cur = 0, thumbs = {};
  const clear = () => { while (gs.children.length > 3) gs.remove(gs.children[gs.children.length - 1]); };
  function orientM(size) { const idx = [0, 1, 2].sort((a, b) => size[b] - size[a]), m = new T.Matrix4(), r = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]; idx.forEach((ax, i) => r[i][ax] = 1); m.set(...r[0], 0, ...r[1], 0, ...r[2], 0, 0, 0, 0, 1); if (m.determinant() < 0) { r[2] = r[2].map(v => -v); m.set(...r[0], 0, ...r[1], 0, ...r[2], 0, 0, 0, 0, 1); } return m; }
  function addInst(def, matrix, kind, parent) {
    const g = ctx.geomOf(def), mat = ctx.getMat(kind || 'real', def.solid.mat), me = new T.Mesh(g, mat); me.matrixAutoUpdate = false; me.matrix.copy(matrix); const ln = new T.LineSegments(def.edgeGeom, lineMat); ln.matrixAutoUpdate = false; ln.matrix.copy(matrix); (parent || gs).add(me, ln); return me;
  }
  function featBoxes(def, matrix, tags, onlyNear) {
    const out = []; def.solid.feat.forEach(f => { if (!tags.includes(f.tag)) return; const b = f.box, g = f.kind === 'cut' ? 0 : .35, w = [b[3] - b[0] + 2 * g, b[4] - b[1] + 2 * g, b[5] - b[2] + 2 * g];
      const m = new T.Mesh(new T.BoxGeometry(w[0], w[1], w[2]), new T.MeshBasicMaterial({ color: f.kind === 'cut' ? 0xff7a00 : 0x16a34a, transparent: true, opacity: f.kind === 'cut' ? .62 : .5, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }));
      m.position.set((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2); const e = new T.LineSegments(new T.EdgesGeometry(m.geometry), new T.LineBasicMaterial({ color: f.kind === 'cut' ? 0xb34700 : 0x0b6b2e })); e.position.copy(m.position); const grp = new T.Group(); grp.add(m, e); grp.applyMatrix4(matrix); gs.add(grp); out.push({ f, c: V(m.position.x, m.position.y, m.position.z).applyMatrix4(matrix), size: w, box: b, matrix }); }); return out;
  }
  const SZ3 = [1000, 1150], SZF = [1400, 1230], SZD = [680, 540];
  function frame(cam_, box, dir, fill, aspect) {
    fill = fill || .86; cam_.aspect = aspect; cam_.updateProjectionMatrix(); const dv = V(...dir).normalize(), c = box.getCenter(V(0, 0, 0)), r = Math.max(40, box.getSize(V(0, 0, 0)).length() / 2);
    const cs = []; for (let i = 0; i < 8; i++) cs.push(V(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z));
    const solve = (tg) => { let lo = r * .3, hi = r * 40; for (let k = 0; k < 40; k++) { const d = (lo + hi) / 2; cam_.position.copy(tg).addScaledVector(dv, d); cam_.up.set(0, 0, 1); cam_.lookAt(tg); cam_.updateMatrixWorld(); let m = 0; cs.forEach(p => { const q = p.clone().project(cam_); m = Math.max(m, Math.abs(q.x), Math.abs(q.y)); }); if (m > fill) lo = d; else hi = d; } return hi; };
    let tg = c.clone(), d = solve(tg);
    for (let it = 0; it < 2; it++) { let x0 = 9, x1 = -9, y0 = 9, y1 = -9; cs.forEach(p => { const q = p.clone().project(cam_); x0 = Math.min(x0, q.x); x1 = Math.max(x1, q.x); y0 = Math.min(y0, q.y); y1 = Math.max(y1, q.y); });
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, hh = Math.tan(cam_.fov * Math.PI / 360) * d, right = V(1, 0, 0).applyQuaternion(cam_.quaternion), up = V(0, 1, 0).applyQuaternion(cam_.quaternion); tg.addScaledVector(right, cx * hh * aspect).addScaledVector(up, cy * hh); d = solve(tg); }
  }
  function snap(w, h, bgTop, bgBot) {
    const r = ctx.renderer, size = r.getSize(V(0, 0, 0)), pr = r.getPixelRatio(), vp = r.getViewport(new T.Vector4()), clips = r.clippingPlanes; r.clippingPlanes = []; r.setScissorTest(false); r.setPixelRatio(1); r.setSize(w, h, false); r.setViewport(0, 0, w, h); cam.aspect = w / h; cam.updateProjectionMatrix(); r.autoClear = true; r.render(gs, cam);
    const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d'), g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, bgTop || '#ffffff'); g.addColorStop(1, bgBot || '#e6eaf0'); x.fillStyle = g; x.fillRect(0, 0, w, h); x.drawImage(r.domElement, 0, 0, w, h);
    r.setPixelRatio(pr); r.setSize(size.x, size.y, false); r.setViewport(vp); r.clippingPlanes = clips; ctx.S.need = true; return c;
  }
  const proj = (p, w, h) => { const v = p.clone().project(cam); return [(v.x * .5 + .5) * w, (-v.y * .5 + .5) * h, v.z]; };
  function pill(ctx2, text, px, py, col, fs) {
    ctx2.font = `bold ${fs}px system-ui,Segoe UI,sans-serif`; const w = ctx2.measureText(text).width + fs, h = fs * 1.7, rr = h / 2.4; ctx2.fillStyle = col || '#1b2430'; ctx2.strokeStyle = '#fff'; ctx2.lineWidth = Math.max(2, fs * .12); ctx2.beginPath(); ctx2.moveTo(px + rr, py); ctx2.arcTo(px + w, py, px + w, py + h, rr); ctx2.arcTo(px + w, py + h, px, py + h, rr); ctx2.arcTo(px, py + h, px, py, rr); ctx2.arcTo(px, py, px + w, py, rr); ctx2.closePath(); ctx2.fill(); ctx2.stroke(); ctx2.fillStyle = '#fff'; ctx2.textBaseline = 'middle'; ctx2.fillText(text, px + fs / 2, py + h / 2 + 1); return { w, h };
  }
  function labels(canvas, items, fs) {
    const x = canvas.getContext('2d'), W = canvas.width, H = canvas.height; items = items.filter(i => i.p[2] < 1).sort((a, b) => a.p[1] - b.p[1]); const Ls = [], Rs = []; items.forEach(it => (it.p[0] < W / 2 ? Ls : Rs).push(it));
    const place = (arr, side) => { let lastY = -999; arr.forEach(it => { x.font = `bold ${fs}px system-ui,sans-serif`; const w = x.measureText(it.text).width + fs, h = fs * 1.7; let y = Math.max(8, Math.min(H - h - 8, it.p[1] - h / 2)); if (y < lastY + h + 8) y = lastY + h + 8; lastY = y; const px = side === 0 ? 12 : W - w - 12;
      x.strokeStyle = '#1b2430'; x.lineWidth = Math.max(2.5, fs * .13); x.beginPath(); x.moveTo(side === 0 ? px + w : px, y + h / 2); x.lineTo(it.p[0], it.p[1]); x.stroke(); x.fillStyle = '#ffd400'; x.beginPath(); x.arc(it.p[0], it.p[1], fs * .38, 0, 7); x.fill(); x.stroke(); pill(x, it.text, px, y, it.col, fs); }); }; place(Ls, 0); place(Rs, 1);
  }
  function arrow(x, a, b, col, k) {
    const dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy); if (len < 22 * k) return; const ux = dx / len, uy = dy / len, hw = 17 * k, hl = 34 * k, e = [b[0] - ux * 8 * k, b[1] - uy * 8 * k];
    x.save(); x.lineCap = 'round'; x.lineJoin = 'round'; [['#1b2430', 16 * k, 1.35], [col || '#ffd400', 9.5 * k, 1]].forEach(([c, w, m]) => { x.strokeStyle = c; x.fillStyle = c; x.lineWidth = w; x.beginPath(); x.moveTo(a[0], a[1]); x.lineTo(e[0] - ux * hl, e[1] - uy * hl); x.stroke(); x.beginPath(); x.moveTo(e[0], e[1]); x.lineTo(e[0] - ux * hl - uy * hw * m, e[1] - uy * hl + ux * hw * m); x.lineTo(e[0] - ux * hl + uy * hw * m, e[1] - uy * hl - ux * hw * m); x.closePath(); x.fill(); }); x.restore();
  }
  const tbox = (def, m) => ctx.geomOf(def).boundingBox.clone().applyMatrix4(m);
  const exVec = (i, f) => V(...(i.ex || [0, 0, 0])).multiplyScalar(f);
  const instMat = (i, off) => new T.Matrix4().makeTranslation(off.x, off.y, off.z).multiply(i.m);
  function shadowDisc(box) {
    const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d'), g = x.createRadialGradient(128, 128, 10, 128, 128, 126); g.addColorStop(0, 'rgba(40,30,20,.34)'); g.addColorStop(.55, 'rgba(40,30,20,.14)'); g.addColorStop(1, 'rgba(40,30,20,0)'); x.fillStyle = g; x.fillRect(0, 0, 256, 256);
    const sz = box.getSize(V(0, 0, 0)), m = new T.Mesh(new T.PlaneGeometry(sz.x * 1.5, sz.y * 2.1), new T.MeshBasicMaterial({ map: new T.CanvasTexture(c), transparent: true, depthWrite: false })); m.position.set((box.min.x + box.max.x) / 2, (box.min.y + box.max.y) / 2, Math.max(0, box.min.z) + .3); gs.add(m);
  }
  function addAll(M, maxStep, newStep, exf) {
    clear(); const box = new T.Box3(), news = []; M.insts.forEach(i => { if (i.step > maxStep) return; const isNew = newStep !== null && i.step === newStep, off = isNew ? exVec(i, exf) : V(0, 0, 0), def = M.defs.get(i.def); addInst(def, instMat(i, off), isNew ? 'new' : 'real'); box.union(tbox(def, instMat(i, off))); box.union(tbox(def, i.m)); if (isNew) news.push({ i, off, def }); }); return { box, news };
  }
  function heroAsm(st) {
    const M = S.M, [w, h] = SZ3, k = w / 1000, { box, news } = addAll(M, st.asm, st.asm, st.exf || .5), fl = new T.Box3(); M.insts.forEach(i => { if (i.step <= st.asm) fl.union(tbox(M.defs.get(i.def), i.m)); }); shadowDisc(fl);
    frame(cam, box, st.dir || [.7, -.9, .6], .9, w / h); const c = snap(w, h), x = c.getContext('2d'), seen = new Set(); let na = 0;
    news.forEach(({ i, off, def }) => { if (seen.has(i.def) || na >= 8) return; seen.add(i.def); const cc = tbox(def, instMat(i, off)).getCenter(V(0, 0, 0)); if (off.length() > 10) { arrow(x, proj(cc, w, h), proj(cc.clone().sub(off), w, h), null, k); na++; } });
    let detail = null; if (st.detail && news.length) { const pick = st.detail === 'first' ? news[0] : news[st.detail]; const bb = tbox(pick.def, instMat(pick.i, pick.off)).union(tbox(pick.def, pick.i.m)); const home = tbox(pick.def, pick.i.m), cen = home.getCenter(V(0, 0, 0)); const bx = new T.Box3().setFromCenterAndSize(cen, V(150, 150, 150)); bx.union(bb); frame(cam, bx, st.dir || [.7, -.9, .6], .8, SZD[0] / SZD[1]); detail = snap(SZD[0], SZD[1]); const xd = detail.getContext('2d'); const cc = bb.getCenter(V(0, 0, 0)); arrow(xd, proj(cc, SZD[0], SZD[1]), proj(cc.clone().sub(pick.off), SZD[0], SZD[1]), null, SZD[0] / 1000); }
    return { hero: c, detail };
  }
  function heroSubset(st) {
    const M = S.M, [w, h] = SZ3, k = w / 1000, box = new T.Box3(), arrows = [], feats = []; clear();
    st.show.forEach(s => { const i = M.insts.filter(q => q.def === s.def)[s.idx - 1]; if (!i) return; const off = V(...s.ex), def = M.defs.get(i.def); addInst(def, instMat(i, off), s.ex.some(v => v) ? 'new' : 'real'); box.union(tbox(def, instMat(i, off))); box.union(tbox(def, i.m)); if (st.tags) featBoxes(def, instMat(i, off), st.tags).forEach(f => feats.push(f)); if (off.length() > 10) { const cc = tbox(def, instMat(i, off)).getCenter(V(0, 0, 0)); arrows.push([cc, cc.clone().sub(off)]); } });
    frame(cam, box, st.dir, .88, w / h); const c = snap(w, h), x = c.getContext('2d'); arrows.slice(0, 6).forEach(([a, b]) => arrow(x, proj(a, w, h), proj(b, w, h), null, k));
    if (feats.length) { const its = []; feats.forEach(f => { if (f.f.label) its.push({ p: proj(f.c, w, h), text: featLabel(f.f), col: f.f.kind === 'cut' ? '#b34700' : '#0b6b2e' }); }); labels(c, dedupe(its).slice(0, 4), Math.round(w * .021)); } return { hero: c };
  }
  function featLabel(f) {
    const raw = CAD.inchifyText(f.label || f.tag || 'joint');
    if (/^(cut|leave|remove|mortise|dado|groove|tenon|tongue)\b/i.test(raw)) return raw;
    return (f.kind === 'cut' ? 'Cut out · ' : 'Leave · ') + raw;
  }
  function heroPart(st) {
    const M = S.M, [w, h] = SZ3, k = w / 1000; clear(); let ox = 0; const feats = [], box = new T.Box3();
    st.focus.forEach(id => { const def = M.defs.get(id), b = def.box, m = new T.Matrix4().makeTranslation(ox - b[0], -(b[1] + b[4]) / 2, -b[2]); addInst(def, m, 'real'); box.union(tbox(def, m)); featBoxes(def, m, st.tags).forEach(f => feats.push(Object.assign(f, { def }))); ox += b[3] - b[0] + 70; });
    frame(cam, box, st.dir || [.8, -.85, .6], .9, w / h); const c = snap(w, h), x = c.getContext('2d'), seen = {}, items = [];
    feats.forEach(f => { if (!f.f.label) return; const key = f.def.id + f.f.tag + f.f.label; if (seen[key]) return; seen[key] = 1; items.push({ p: proj(f.c, w, h), text: featLabel(f.f), col: f.f.kind === 'cut' ? '#b34700' : '#0b6b2e' }); }); labels(c, items.slice(0, 6), Math.round(w * .021));
    let detail = null; if (st.zoom) { const base = feats.filter(f => st.tags.includes(f.f.tag)); if (base.length) { const first = base[0], rad = typeof st.zoom === 'number' ? Math.min(st.zoom, 260) : 95, near = base.filter(f => f.c.distanceTo(first.c) < rad), bb = new T.Box3(); near.forEach(f => { const hs = V(f.size[0], f.size[1], f.size[2]).multiplyScalar(.5); bb.expandByPoint(f.c.clone().add(hs)); bb.expandByPoint(f.c.clone().sub(hs)); }); const cen = bb.getCenter(V(0, 0, 0)), box2 = new T.Box3().setFromCenterAndSize(cen, V(1, 1, 1).multiplyScalar(Math.max(70, bb.getSize(V(0, 0, 0)).length() * 1.2))); frame(cam, box2, st.dir || [.8, -.85, .6], .78, SZD[0] / SZD[1]); detail = snap(SZD[0], SZD[1]); const its = near.filter(f => f.f.label).map(f => ({ p: proj(f.c, SZD[0], SZD[1]), text: featLabel(f.f), col: f.f.kind === 'cut' ? '#b34700' : '#0b6b2e' })); labels(detail, dedupe(its).slice(0, 3), Math.round(SZD[0] * .034)); } }
    return { hero: c, detail };
  }
  const dedupe = a => { const s = new Set(); return a.filter(i => !s.has(i.text) && s.add(i.text)); };
  function heroFlat() {
    const M = S.M, [w, h] = SZF; clear(); const defs = [...M.defs.values()].sort((a, b) => CAD.GROUPS.findIndex(g => g.id === a.grp) - CAD.GROUPS.findIndex(g => g.id === b.grp)); const items = defs.map(d => { const om = orientM(d.size), s = d.size.slice().sort((a, b) => b - a); return { d, om, w: s[0], h: s[1] }; });
    const W = 2300, gap = 90; let x = 0, y = 0, rowH = 0; items.forEach(it => { if (x + it.w > W) { x = 0; y += rowH + gap; rowH = 0; } it.x = x; it.y = y; x += it.w + gap; rowH = Math.max(rowH, it.h); });
    const box = new T.Box3(), labs = []; items.forEach(it => { const b = it.d.box, c = V((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, b[2]), m = new T.Matrix4().makeTranslation(it.x + it.w / 2, it.y + it.h / 2, 0).multiply(it.om).multiply(new T.Matrix4().makeTranslation(-c.x, -c.y, -c.z)); addInst(it.d, m, 'real'); const bb = tbox(it.d, m); box.union(bb); labs.push({ it, c: bb.getCenter(V(0, 0, 0)) }); });
    const g = new T.Mesh(new T.PlaneGeometry(12000, 12000), new T.MeshBasicMaterial({ color: 0xf1ede6 })); g.position.set(0, 0, -1); gs.add(g);
    frame(cam, box, [0, -.12, 1], .93, w / h); const c = snap(w, h, '#f6f3ee', '#ece7de'), xx = c.getContext('2d'), fs = Math.round(w * .0105); const rects = []; labs.forEach(l => { const t = l.it.d.name.replace(/\s*\(.*\)/g, '').replace('Carcass ', '').replace(' 44 × 44', '').slice(0, 34) + '  ×' + l.it.d.qty; xx.font = `bold ${fs}px system-ui,sans-serif`; const p = proj(l.c, w, h), tw = xx.measureText(t).width + fs, th = fs * 1.6; let rx = p[0] - tw / 2, ry = p[1] - th / 2; for (let it = 0; it < 14; it++) { const hit = rects.find(r => rx < r.x + r.w + 4 && r.x < rx + tw + 4 && ry < r.y + r.h + 3 && r.y < ry + th + 3); if (!hit) break; ry = hit.y + hit.h + 4; } rects.push({ x: rx, y: ry, w: tw, h: th }); if (Math.abs(ry - (p[1] - th / 2)) > th) { xx.strokeStyle = '#1b2430'; xx.lineWidth = 2; xx.beginPath(); xx.moveTo(p[0], p[1]); xx.lineTo(rx + tw / 2, ry + th / 2); xx.stroke(); xx.fillStyle = '#ffd400'; xx.beginPath(); xx.arc(p[0], p[1], fs * .3, 0, 7); xx.fill(); xx.stroke(); } xx.fillStyle = 'rgba(27,36,48,.92)'; xx.fillRect(rx, ry, tw, th); xx.fillStyle = '#fff'; xx.textBaseline = 'middle'; xx.fillText(t, rx + fs / 2, ry + th / 2); }); return { hero: c };
  }
  function heroAll() { const M = S.M, [w, h] = SZF; clear(); const box = new T.Box3(); M.insts.forEach(i => { const d = M.defs.get(i.def); addInst(d, i.m, 'real'); box.union(tbox(d, i.m)); }); shadowDisc(box); frame(cam, box, [.7, -1, .5], .8, w / h); return { hero: snap(w, h, '#ffffff', '#eceff4') }; }
  function thumb(id) {
    if (thumbs[id]) return thumbs[id]; const M = S.M, def = M.defs.get(id); clear(); const b = def.box, m = new T.Matrix4().makeTranslation(-(b[0] + b[3]) / 2, -(b[1] + b[4]) / 2, -(b[2] + b[5]) / 2); addInst(def, m, 'real'); const box = tbox(def, m), sz = def.size, long = sz.indexOf(Math.max(...sz)), dir = long === 2 ? [.9, -1, .45] : long === 0 ? [.45, -1, .8] : [1, -.45, .8]; frame(cam, box, dir, .9, 260 / 180); return thumbs[id] = snap(260, 180, '#ffffff', '#ffffff').toDataURL('image/jpeg', .9);
  }
  /* ----- pages ----- */
  const esc = escH; let css = ''; try { css = [...document.styleSheets].map(s => { try { return [...s.cssRules].map(r => r.cssText).join('\n'); } catch (e) { return ''; } }).join('\n'); } catch (e) { }
  function partsFor(st) {
    let list = st.parts; if (!list && st.kind === 'asm') { const m = {}; S.M.insts.forEach(i => { if (i.step === st.asm) m[i.def] = (m[i.def] || 0) + 1; }); list = Object.entries(m).map(([def, qty]) => ({ def, qty })); }
    if (!list && st.kind === 'subset') { const m = {}; st.show.forEach(s => m[s.def] = (m[s.def] || 0) + 1); list = Object.entries(m).map(([def, qty]) => ({ def, qty })); } return (list || []).slice(0, 5);
  }
  function pageHTML(st, i, total, imgs) {
    const full = st.kind === 'hero' || st.kind === 'flat' || st.kind === 'text' || st.kind === 'cutlist'; const parts = full ? '' : `<div class="parts"><h4>Parts needed</h4>${partsFor(st).map(p => `<div class="pt"><img src="${imgs.thumbs[p.def]}"><b>${p.qty}×</b><span>${esc(S.M.defs.get(p.def).name.replace(/\(.*\)/, ''))}</span></div>`).join('')}</div>`;
    let body = ''; if (st.kind === 'cutlist') body = cutTable(); else if (st.kind !== 'text') body = `<div class="hero"><img class="m" src="${imgs.hero}">${imgs.detail ? `<div class="inset"><i>DETAIL</i><img src="${imgs.detail}"></div>` : ''}</div>`; else body = `<div class="hero" style="background:var(--panel2)"><div style="padding:18px 26px;font-size:15px;line-height:1.45">${st.text.map(t => `<p style="margin:0 0 12px">${t}</p>`).join('')}</div></div>`;
    const showJoineryLegend = st.kind === 'part' || (st.kind === 'subset' && st.tags && st.tags.length);
    const legend = showJoineryLegend ? `<div class="legend"><b>Callouts</b> = joinery on this part (dado / mortise / tenon sizes), not the overall blank. Orange = wood to remove. Green = wood to leave.</div>` : '';
    const side = st.kind === 'text' || st.kind === 'cutlist' ? '' : `<div class="side"><ol>${st.text.map(t => `<li>${t}</li>`).join('')}</ol>${legend}${st.tools && st.tools.length ? `<div class="tools"><b>Tools</b>${st.tools.join(' · ')}</div>` : ''}${st.tip ? `<div class="tip"><b>TIP</b> ${st.tip}</div>` : ''}${st.chk ? `<div class="chk"><b>CHECK</b> ${st.chk}</div>` : ''}</div>`;
    const cls = 'pg' + (parts ? '' : ' full'); const wide = st.kind === 'cutlist' || st.kind === 'text';
    return `<section class="${cls}" ${wide ? 'style="grid-template-columns:1fr"' : ''}><div class="hd"><div class="badge">${st.n}</div><div><div class="ph">${st.phase}</div><h2>${st.title}</h2></div></div>${parts}${body}${side}<div class="ft"><span>${esc(S.M.meta.name)} · build guide</span><div class="bar"><i style="width:${(i + 1) / total * 100}%"></i></div><span>${i + 1} / ${total}</span></div></section>`;
  }
  function cutTable() {
    const plan = CAD.lumberPlan(S.M);
    const buy = `<table><tr><th>Buy</th><th>Material</th><th>Blanks</th></tr>${plan.summary.map(s => `<tr><td><b>${esc(s.buyLine)}</b></td><td>${esc(s.mat)}</td><td>${s.pieces}</td></tr>`).join('')}</table>`;
    const per = plan.boards.map(b => `<div style="margin-top:8px"><b>Board ${b.id}: ${esc(b.label)}</b><table><tr><th>Part blank</th><th>Finished size</th><th>Cut length</th></tr>${b.cuts.map(c => `<tr><td>${esc(c.name)}</td><td>${esc(c.finished)}</td><td>${esc(c.len)}</td></tr>`).join('')}</table></div>`).join('');
    return `<div class="hero tb" style="background:var(--panel);display:block;padding:8px 14px;overflow:auto"><p style="margin:0 0 8px;font-size:12px;color:var(--dim)"><b>Buy list first</b> — parts are nested onto shared boards. Finished sizes are the blank for each part (T×W×L); T is in quarters (7/4″), not joinery pocket sizes.</p>${buy}${per}</div>`;
  }
  async function generate(cb) {
    steps = CAD.guideSteps(S.M); pages = []; thumbs = {}; const imgs = []; const tick = () => new Promise(r => setTimeout(r, 0));
    for (let i = 0; i < steps.length; i++) {
      const st = steps[i]; cb && cb(i, steps.length); await tick(); let r = {}, th = {};
      if (st.kind === 'hero') r = { hero: heroAll().hero }; else if (st.kind === 'flat') r = heroFlat(); else if (st.kind === 'asm') r = heroAsm(st); else if (st.kind === 'subset') r = heroSubset(st); else if (st.kind === 'part') r = heroPart(st);
      const out = { hero: r.hero ? r.hero.toDataURL('image/jpeg', .88) : null, detail: r.detail ? r.detail.toDataURL('image/jpeg', .88) : null, thumbs: {} };
      if (!['hero', 'flat', 'text', 'cutlist'].includes(st.kind)) partsFor(st).forEach(p => { out.thumbs[p.def] = thumb(p.def); });
      imgs.push(out); pages.push(pageHTML(st, i, steps.length, out));
    } clear(); return pages.length;
  }
  const el = { box: () => $('#guide'), body: () => $('#gbody'), sel: () => $('#gsel') };
  function syncNav() {
    const n = pages ? pages.length : 0, atStart = cur <= 0, atEnd = !n || cur >= n - 1;
    ['gprev', 'gprev2'].forEach(id => { const b = $('#' + id); if (b) b.disabled = atStart; });
    ['gnext', 'gnext2'].forEach(id => { const b = $('#' + id); if (b) { b.disabled = atEnd; b.textContent = atEnd ? 'Last step' : 'Next step ▶'; } });
    const stepBar = document.querySelector('#guide .gstep'); if (stepBar) stepBar.style.display = el.body().parentNode.dataset.mode === 'all' ? 'none' : 'flex';
  }
  function show(i) { if (!pages || !pages.length) return; cur = Math.max(0, Math.min(pages.length - 1, i)); el.body().innerHTML = pages[cur]; el.box().dataset.mode = 'one'; el.body().parentNode.dataset.mode = 'one'; el.sel().value = cur; $('#gprog').textContent = `step ${cur + 1} of ${pages.length}`; el.body().scrollTop = 0; syncNav(); }
  function showAll() { el.body().innerHTML = '<div style="display:flex;flex-direction:column;gap:12px;width:100%;align-items:center">' + pages.join('') + '</div>'; el.box().dataset.mode = 'all'; el.body().parentNode.dataset.mode = 'all'; syncNav(); }
  async function open() {
    el.box().style.display = 'flex'; if (!pages) { el.body().innerHTML = '<div style="padding:40px;color:#445;font:16px system-ui">Rendering the guide from the live model… <b id="gp">0%</b></div>'; await generate((i, n) => { const p = $('#gp'); if (p) p.textContent = Math.round(i / n * 100) + '%  (step ' + (i + 1) + ' of ' + n + ')'; }); el.sel().innerHTML = steps.map((s, i) => `<option value="${i}">${s.n}. ${s.title}</option>`).join(''); } show(cur);
  }
  function invalidate() { pages = null; }
  function standalone() { return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>${esc(S.M.meta.name)}: build guide</title><style>${css}\nbody{overflow:auto!important;background:var(--bg,#eef1f4);height:auto!important}#guide{display:block!important;position:static!important;background:transparent}#gbody{display:flex;flex-direction:column;gap:12px;align-items:center;padding:18px}.pg{width:min(1100px,96vw);height:auto;max-height:none;min-height:480px}</style></head><body><div id="guide" data-mode="all"><div class="gb" id="gbody">${pages.join('')}</div></div></body></html>`; }
  async function save() { if (!pages) await generate(); const html = standalone(); return ctx.deliver('build_guide', [{ name: ctx.safe(S.M.meta.name) + '_build_guide.html', data: html }]); }
  $('#gclose').onclick = () => { el.box().style.display = 'none'; ctx.S.need = true; };
  const goPrev = () => show(cur - 1), goNext = () => show(cur + 1);
  $('#gprev').onclick = goPrev; $('#gnext').onclick = goNext; $('#gprev2').onclick = goPrev; $('#gnext2').onclick = goNext;
  $('#gsel').onchange = e => show(+e.target.value); $('#gall').onclick = () => { if (pages) showAll(); }; $('#gprint').onclick = () => { if (pages) { showAll(); setTimeout(() => window.print(), 100); } }; $('#gsave').onclick = save;
  addEventListener('keydown', e => { if (el.box().style.display !== 'flex') return; if (e.key === 'ArrowRight') goNext(); else if (e.key === 'ArrowLeft') goPrev(); else if (e.key === 'Escape') $('#gclose').click(); });
  return { open, save, generate, show, showAll, invalidate, steps: () => steps, pages: () => pages, standalone };
};
})(typeof globalThis !== 'undefined' ? globalThis : window);
