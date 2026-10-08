/* model.js — walnut console / sideboard, marble top, 2 drawers, 2 sliding slatted doors. No hardware: glue + wood joinery only.
   World: mm, Z-up, X along length, Y depth (front = −Y). Origin on the floor at the centre. */
(function (root) {
'use strict';
const CAD = root.CAD, T = root.THREE, Solid = CAD.Solid, D2R = Math.PI / 180;

CAD.MATS = {
  wood:   { name: 'American walnut',          color: 0xb88457, metal: 0, rough: .62, rho: 650, tex: 'wood' },
  woodL:  { name: 'Walnut (pegs & keys, end grain)', color: 0xcfa070, metal: 0, rough: .6, rho: 650, tex: 'wood' },
  ply:    { name: 'Walnut-veneer ply 6 mm',   color: 0xa87a50, metal: 0, rough: .65, rho: 680, tex: 'wood' },
  marble: { name: 'Marble (honed)',           color: 0xe7e3dc, metal: 0, rough: .35, rho: 2700, tex: 'marble' },
};
CAD.GROUPS = [
  { id: 'base',   name: 'Base frame (legs, rails, stretchers)', color: 0x6aa6ff },
  { id: 'carcass',name: 'Carcass',                             color: 0x7bd88f },
  { id: 'drawers',name: 'Drawers',                             color: 0xffb454 },
  { id: 'doors',  name: 'Sliding slatted doors',               color: 0xc792ea },
  { id: 'top',    name: 'Stone top & keys',                    color: 0xf5d547 },
  { id: 'pegs',   name: 'Pegs (wood)',                         color: 0xe0a458 },
];
CAD.STEPS = [
  'Glue the two end frames: legs, end rails and end stretchers',
  'Join the end frames with the front & back aprons and the long stretcher',
  'Drive the draw-bore pegs',
  'Set the carcass floor (bottom panel) on the leg tenons',
  'Stand the end panels, divider, drawer rail and guide strips',
  'Slide in the floating back panel',
  'Drop on the carcass roof (top panel)',
  'Insert the two drawers',
  'Lift in the two sliding doors',
  'Fit the stone keys',
  'Bed the marble top',
];

const M4 = (x, y, z, rz, rx) => { const m = new T.Matrix4().makeTranslation(x, y, z); if (rz) m.multiply(new T.Matrix4().makeRotationZ(rz * D2R)); if (rx) m.multiply(new T.Matrix4().makeRotationX(rx * D2R)); return m; };

function layout(p) {
  const L = Object.assign({}, p);
  L.Wc = p.W - 20; L.Dc = p.D - 20; L.Hc = 270; L.Hl = p.H - 20 - L.Hc;
  L.hx = L.Wc / 2; L.hy = L.Dc / 2; L.panT = 22; L.zTop = L.Hl + L.Hc; L.zb0 = L.Hl; L.zb1 = L.Hl + 22; L.zt0 = L.zTop - 22; L.zt1 = L.zTop;
  L.xL = -L.hx + 26; L.xR = L.hx - 26; L.clearW = L.xR - L.xL;
  L.Wbay = Math.round(L.clearW * .355 / 10) * 10; L.xd = L.xL + L.Wbay; L.xdd = L.xd + 18;
  L.Wdb = L.xR - L.xdd; L.Wd = (L.Wdb + 40) / 2; L.zm = L.Hl + L.Hc / 2;
  L.zs = Math.round(L.Hl * .36);                      // stretcher centre height
  L.yb0 = L.hy - 20; L.yb1 = L.yb0 + 6;               // back panel (20 mm from the rear edge)
  L.ys0 = -L.hy + 26; L.ys1 = L.yb0 - 5; L.Ls = L.ys1 - L.ys0;   // drawer guide strips
  L.Wdr = L.Wbay - 3; L.Ld = L.Dc - 25; L.hdr = 100;
  L.Hd = (L.Hc - 44) + 7;                             // door height
  L.slat = 12; L.stile = 24; L.rail = 30; L.dT = 16;
  const inner = L.Wd - 2 * L.stile; L.nSlat = Math.floor((inner + 12) / 24); L.gap = (inner - L.nSlat * L.slat) / (L.nSlat + 1);
  L.legC = [[-L.hx + 22, -L.hy + 22, 0], [L.hx - 22, -L.hy + 22, 90], [L.hx - 22, L.hy - 22, 180], [-L.hx + 22, L.hy - 22, 270]];
  L.keys = [[-(L.hx - 140), -60], [-(L.hx - 140), 60], [L.hx - 140, -60], [L.hx - 140, 60]];
  L.tracks = [[-L.hy + 24, -L.hy + 42], [-L.hy + 48, -L.hy + 66]];
  return L;
}
CAD.sbLayout = layout;

class Sideboard {
  constructor(params) { this.P = Object.assign({ W: 1400, D: 400, H: 850 }, params || {}); this.L = layout(this.P); this.defs = new Map(); this.insts = []; this.build(); }
  def(id, o) { o.id = id; this.defs.set(id, o); return o; }
  put(id, m, step, o) { const i = Object.assign({ def: id, m, step }, o || {}); this.insts.push(i); return i; }
  finalize() {
    const cnt = {}; this.insts.forEach(i => { cnt[i.def] = (cnt[i.def] || 0) + 1; i.qtyIdx = cnt[i.def]; });
    this.defs.forEach(d => {
      d.qty = cnt[d.id] || 0; d.vol = d.solid.volume(); d.box = d.solid.bbox(); d.boxes = d.solid.boxes(); const mt = CAD.MATS[d.solid.mat];
      d.mass = d.vol * 1e-9 * mt.rho; d.size = [d.box[3] - d.box[0], d.box[4] - d.box[1], d.box[5] - d.box[2]];
    });
    return this;
  }
  build() {
    const M = this, L = this.L, { hx, hy, Hl, Wc, Dc, zb0, zb1, zt0, zt1, xL, xR, xd, xdd, zm, zs } = L;
    const wood = 'wood', legZc = Hl - 35;                    // apron tenon centre height
    const feat = (s, tag, fill, ...b) => s.cut(...b, tag, { fill });

    /* ===== LEGS: type A (FL, BR) and type B (FR, BL) are mirror pairs; local x,y ∈ [0,44], outer faces at x=0,y=0 ===== */
    const mkLeg = (variant) => {
      const leg = new Solid({ grain: 'z' }); leg.add(0, 0, 0, 44, 44, Hl);
      leg.add(10, 10, Hl, 34, 34, Hl + 14, 'tenonTop');
      leg.cut(20, 11, legZc - 20, 44, 19, legZc + 20, 'mortiseA', { fill: true, label: 'Rail mortise 24 × 8 × 40' });
      leg.cut(11, 20, legZc - 20, 19, 44, legZc + 20, 'mortiseB', { fill: true, label: 'Rail mortise 24 × 8 × 40' });
      leg.cut(29, 0, legZc - 3, 35, 22, legZc + 3, 'pegA', { fill: true, label: 'Peg hole 6 × 6 × 22' });
      leg.cut(0, 29, legZc - 3, 22, 35, legZc + 3, 'pegB', { fill: true, label: 'Peg hole 6 × 6 × 22' });
      if (variant === 'A') { leg.cut(17, 20, zs - 10, 27, 44, zs + 10, 'mortiseS', { fill: true, label: 'Stretcher mortise 24 × 10 × 20' }); leg.cut(0, 29, zs - 3, 30, 35, zs + 3, 'pegS', { fill: true, label: 'Peg hole 6 × 6 × 30' }); }
      else { leg.cut(20, 17, zs - 10, 44, 27, zs + 10, 'mortiseS', { fill: true, label: 'Stretcher mortise 24 × 10 × 20' }); leg.cut(29, 0, zs - 3, 35, 30, zs + 3, 'pegS', { fill: true, label: 'Peg hole 6 × 6 × 30' }); }
      return leg;
    };
    M.def('leg_A', { name: 'Leg 44 × 44 — type A (front-left, back-right)', grp: 'base', solid: mkLeg('A'), spec: 'Straight-grain walnut, ' + Hl + ' mm + 14 mm top tenon', note: 'Mirror pair with type B.' });
    M.def('leg_B', { name: 'Leg 44 × 44 — type B (front-right, back-left)', grp: 'base', solid: mkLeg('B'), spec: 'Straight-grain walnut, ' + Hl + ' mm + 14 mm top tenon', note: 'Mirror pair with type A.' });

    /* ===== APRON RAILS ===== */
    const Lr = Wc - 88, Le = Dc - 88, th = 8, tl = 24;
    const pegHole = (s, along, pos, y0, y1, z0, z1, x0, x1, tag) => 0;
    const apL = new Solid({ grain: 'x' }); apL.add(-Lr / 2, 0, 0, Lr / 2, 22, 60);
    [-1, 1].forEach(sg => { const a = sg * Lr / 2, b = sg * (Lr / 2 + tl); apL.add(a, 7, 5, b, 15, 45, 'tenon', { label: 'Tenon 24 × 8 × 40' });
      const h0 = sg * (Lr / 2 + 9), h1 = sg * (Lr / 2 + 15); apL.cut(h0, 7, 22, h1, 15, 28, 'pegHole', { fill: true }); });
    M.def('apron_long', { name: 'Apron rail — front / back', grp: 'base', solid: apL, spec: '22 × 60 × ' + (Lr + 2 * tl) + ' mm incl. tenons' });
    const apE = new Solid({ grain: 'y' }); apE.add(0, -Le / 2, 0, 22, Le / 2, 60);
    [-1, 1].forEach(sg => { apE.add(7, sg * Le / 2, 5, 15, sg * (Le / 2 + tl), 45, 'tenon', { label: 'Tenon 24 × 8 × 40' }); apE.cut(7, sg * (Le / 2 + 9), 22, 15, sg * (Le / 2 + 15), 28, 'pegHole', { fill: true }); });
    M.def('apron_end', { name: 'Apron rail — end', grp: 'base', solid: apE, spec: '22 × 60 × ' + (Le + 2 * tl) + ' mm incl. tenons' });

    /* ===== STRETCHERS ===== */
    const sE = new Solid({ grain: 'y' }); sE.add(0, -Le / 2, 0, 30, Le / 2, 30);
    [-1, 1].forEach(sg => { sE.add(10, sg * Le / 2, 5, 20, sg * (Le / 2 + tl), 25, 'tenon', { label: 'Tenon 24 × 10 × 20' }); sE.cut(10, sg * (Le / 2 + 9), 12, 20, sg * (Le / 2 + 15), 18, 'pegHole', { fill: true }); });
    sE.cut(8, -5, 5, 30, 5, 25, 'mortiseL', { fill: true, label: 'Mortise 22 × 10 × 20' });
    M.def('stretcher_end', { name: 'End stretcher 30 × 30', grp: 'base', solid: sE, spec: '30 × 30 × ' + (Le + 2 * tl) + ' mm incl. tenons' });
    const Lb = Wc - 74, sL = new Solid({ grain: 'x' }); sL.add(-Lb / 2, -15, 0, Lb / 2, 15, 30);
    [-1, 1].forEach(sg => sL.add(sg * Lb / 2, -5, 5, sg * (Lb / 2 + 22), 5, 25, 'tenon', { label: 'Tenon 22 × 10 × 20' }));
    M.def('stretcher_long', { name: 'Long stretcher 30 × 30', grp: 'base', solid: sL, spec: '30 × 30 × ' + (Lb + 44) + ' mm incl. tenons' });

    /* ===== PEGS ===== */
    const pg = (len) => { const s = new Solid({ grain: 'z', mat: 'woodL' }); s.add(-3, -3, 0, 3, 3, len); return s; };
    M.def('peg22', { name: 'Square peg 6 × 6 × 22', grp: 'pegs', solid: pg(22), spec: 'Walnut or oak, tapered tip' });
    M.def('peg30', { name: 'Square peg 6 × 6 × 30', grp: 'pegs', solid: pg(30), spec: 'Walnut or oak, tapered tip' });

    /* ===== BOTTOM / TOP PANELS ===== */
    const back = (s, z0, z1) => s.cut(xL, L.yb0, z0, xR, L.yb1, z1, 'grooveBack', { fill: true, label: 'Back-panel groove 6 wide' });
    const dados = (s, z0, z1) => {
      s.cut(-hx + 8, -hy + 14, z0, -hx + 26, hy, z1, 'dadoEnd', { fill: true, label: 'End-panel dado 18 × 8' });
      s.cut(hx - 26, -hy + 14, z0, hx - 8, hy, z1, 'dadoEnd', { fill: true, label: 'End-panel dado 18 × 8' });
      s.cut(xd, -hy + 14, z0, xdd, L.yb0, z1, 'dadoDiv', { fill: true, label: 'Divider dado 18 × 8' });
    };
    const pb = new Solid({ grain: 'x' }); pb.add(-hx, -hy, zb0, hx, hy, zb1);
    L.legC.forEach(([cx, cy]) => pb.cut(cx - 12, cy - 12, zb0, cx + 12, cy + 12, zb0 + 14, 'mortiseTop', { fill: true, label: 'Leg-tenon mortise 24 × 24 × 14' }));
    dados(pb, zb1 - 8, zb1); back(pb, zb1 - 6, zb1);
    L.tracks.forEach(([a, b]) => pb.cut(xdd, a, zb1 - 5, xR, b, zb1, 'track', { fill: false, label: 'Door track 18 × 5' }));
    M.def('panel_bottom', { name: 'Carcass bottom panel', grp: 'carcass', solid: pb, spec: Wc + ' × ' + Dc + ' × 22 mm', note: 'Edge-glue 3–4 boards if needed.' });
    const pt = new Solid({ grain: 'x' }); pt.add(-hx, -hy, zt0, hx, hy, zt1);
    dados(pt, zt0, zt0 + 8); back(pt, zt0, zt0 + 6);
    L.tracks.forEach(([a, b]) => pt.cut(xdd, a, zt0, xR, b, zt0 + 12, 'track', { fill: false, label: 'Door track 18 × 12' }));
    L.keys.forEach(([kx, ky]) => pt.cut(kx - 6, ky - 6, zt1 - 8, kx + 6, ky + 6, zt1, 'mortiseKey', { fill: true, label: 'Key mortise 12 × 12 × 8' }));
    M.def('panel_top', { name: 'Carcass top panel', grp: 'carcass', solid: pt, spec: Wc + ' × ' + Dc + ' × 22 mm' });

    /* ===== END PANELS (L has drawer features) ===== */
    const endPanel = (sg) => {
      const s = new Solid({ grain: 'y' }), x0 = sg < 0 ? -hx + 8 : hx - 26, x1 = x0 + 18, inner = sg < 0 ? x1 : x0;
      s.add(x0, -hy, zb1, x1, hy, zt0); s.add(x0, -hy + 14, zb1 - 8, x1, hy, zb1, 'tongue'); s.add(x0, -hy + 14, zt0, x1, hy, zt0 + 8, 'tongue');
      s.cut(sg < 0 ? inner - 6 : inner, L.yb0, zb1, sg < 0 ? inner : inner + 6, L.yb1, zt0, 'grooveBack', { fill: true, label: 'Back-panel groove 6 × 6' });
      if (sg < 0) {
        s.cut(inner - 6, -hy + 10, zm - 10, inner, L.yb0, zm + 10, 'dadoRail', { fill: true, label: 'Drawer-rail dado 20 × 6' });
        [zb1 + 1.5 + 50, zm + 11.5 + 50].forEach(zc => s.cut(inner - 4, L.ys0, zc - 5, inner, L.ys1, zc + 5, 'dadoStrip', { fill: true, label: 'Guide-strip dado 10 × 4' }));
      }
      return s;
    };
    M.def('endpanel_L', { name: 'End panel — left (drawer side)', grp: 'carcass', solid: endPanel(-1), spec: '18 × ' + Dc + ' × ' + (L.Hc - 44) + ' mm + 8 mm tongues' });
    M.def('endpanel_R', { name: 'End panel — right', grp: 'carcass', solid: endPanel(1), spec: '18 × ' + Dc + ' × ' + (L.Hc - 44) + ' mm + 8 mm tongues' });

    /* ===== DIVIDER, DRAWER RAIL, STRIPS ===== */
    const dv = new Solid({ grain: 'z' }); dv.add(xd, -hy, zb1, xdd, L.yb0, zt0); dv.add(xd, -hy + 14, zb1 - 8, xdd, L.yb0, zb1, 'tongue'); dv.add(xd, -hy + 14, zt0, xdd, L.yb0, zt0 + 8, 'tongue');
    dv.cut(xd, -hy + 10, zm - 10, xd + 6, L.yb0, zm + 10, 'dadoRail', { fill: true, label: 'Drawer-rail dado 20 × 6' });
    [zb1 + 1.5 + 50, zm + 11.5 + 50].forEach(zc => dv.cut(xd, L.ys0, zc - 5, xd + 4, L.ys1, zc + 5, 'dadoStrip', { fill: true, label: 'Guide-strip dado 10 × 4' }));
    M.def('divider', { name: 'Divider panel', grp: 'carcass', solid: dv, spec: '18 × ' + (hy + L.yb0) + ' × ' + (L.Hc - 44) + ' mm + 8 mm tongues' });
    const dr = new Solid({ grain: 'x' }); dr.add(xL, -hy, zm - 10, xd, L.yb0, zm + 10);
    dr.add(xL - 6, -hy + 10, zm - 10, xL, L.yb0, zm + 10, 'tongue', { label: 'Tongue 20 × 6' }); dr.add(xd, -hy + 10, zm - 10, xd + 6, L.yb0, zm + 10, 'tongue', { label: 'Tongue 20 × 6' });
    M.def('drawer_rail', { name: 'Drawer rail (muntin)', grp: 'carcass', solid: dr, spec: '20 × ' + (hy + L.yb0) + ' × ' + (L.Wbay + 12) + ' mm incl. tongues' });
    const gs = new Solid({ grain: 'y' }); gs.add(0, 0, 0, 10, L.Ls, 10); gs.feat.push({ kind: 'add', tag: 'embed', box: [0, 0, 0, 4, L.Ls, 10] });
    M.def('guide_strip', { name: 'Drawer guide strip 10 × 10', grp: 'carcass', solid: gs, spec: '10 × 10 × ' + L.Ls + ' mm, 4 mm sits in dado' });
    const bk = new Solid({ grain: 'x', mat: 'ply' }); bk.add(xL - 6, L.yb0, zb1 - 6, xR + 6, L.yb1, zt0 + 6);
    [[xL - 6, xL], [xR, xR + 6]].forEach(([a, b]) => { bk.cut(a, L.yb0, zb1 - 6, b, L.yb1, zb1, 'notch'); bk.cut(a, L.yb0, zt0, b, L.yb1, zt0 + 6, 'notch'); });
    M.def('back_panel', { name: 'Back panel (floating)', grp: 'carcass', solid: bk, spec: '6 mm veneered ply, ' + (xR - xL + 12) + ' × ' + (L.Hc - 32) + ' mm, corners notched' });

    /* ===== DRAWER (local: x centred, y front→back from 0, z from 0) ===== */
    const W2 = L.Wdr / 2, hd = L.hdr, Ld = L.Ld, sl = 20, bz0 = 14, bs = (hd - bz0) / 4;
    const front = new Solid({ grain: 'x' }); front.add(-W2 + 12, 0, 0, W2 - 12, 22, hd);
    [-1, 1].forEach(sg => [0, 2, 4].forEach(k => { const a = sg * W2, b = sg * (W2 - 12); front.add(Math.min(a, b), 0, k * sl, Math.max(a, b), 22, k * sl + sl, 'finger', { label: 'Box-joint finger 20 × 12' }); }));
    front.cut(-W2 + 12, 14, 8, W2 - 12, 22, 14, 'grooveBottom', { fill: true, label: 'Bottom groove 6 × 8' });
    front.cut(-60, 0, 68, 60, 12, 88, 'pull', { fill: false, label: 'Finger pull 120 × 20 × 12' });
    M.def('drawer_front', { name: 'Drawer front', grp: 'drawers', solid: front, spec: '22 × ' + hd + ' × ' + L.Wdr + ' mm incl. fingers' });
    const side = (sg) => { const s = new Solid({ grain: 'y' }), a = sg * W2, b = sg * (W2 - 12), x0 = Math.min(a, b), x1 = Math.max(a, b);
      s.add(x0, 0, 0, x1, Ld, hd); [0, 2, 4].forEach(k => s.cut(x0, 0, k * sl, x1, 22, k * sl + sl, 'fingerSlot', { fill: true, label: 'Slot 20 × 22' }));
      [0, 2].forEach(j => s.cut(x0, Ld - 12, bz0 + j * bs, x1, Ld, bz0 + (j + 1) * bs, 'fingerSlot', { fill: true, label: 'Rear slot' }));
      const ix0 = sg < 0 ? x1 - 5 : x0, ix1 = sg < 0 ? x1 : x0 + 5; s.cut(ix0, 22, 8, ix1, Ld, 14, 'grooveBottom', { fill: true, label: 'Bottom groove 6 × 5' });
      const ox0 = sg < 0 ? x0 : x1 - 5.5, ox1 = sg < 0 ? x0 + 5.5 : x1; s.cut(ox0, 22, 44, ox1, Ld, 56, 'guideGroove', { fill: false, label: 'Runner groove 12 × 5.5' });
      return s; };
    M.def('drawer_side_L', { name: 'Drawer side — left', grp: 'drawers', solid: side(-1), spec: '12 × ' + hd + ' × ' + Ld + ' mm' });
    M.def('drawer_side_R', { name: 'Drawer side — right', grp: 'drawers', solid: side(1), spec: '12 × ' + hd + ' × ' + Ld + ' mm' });
    const bkd = new Solid({ grain: 'x' }); bkd.add(-W2 + 12, Ld - 12, bz0, W2 - 12, Ld, hd);
    [-1, 1].forEach(sg => [0, 2].forEach(j => { const a = sg * W2, b = sg * (W2 - 12); bkd.add(Math.min(a, b), Ld - 12, bz0 + j * bs, Math.max(a, b), Ld, bz0 + (j + 1) * bs, 'finger', { label: 'Finger' }); }));
    M.def('drawer_back', { name: 'Drawer back', grp: 'drawers', solid: bkd, spec: '12 × ' + (hd - bz0) + ' × ' + L.Wdr + ' mm incl. fingers' });
    const bt = new Solid({ grain: 'y', mat: 'ply' }); bt.add(-W2 + 12, 14, 8, W2 - 12, Ld, 14); bt.add(-W2 + 7, 22, 8, -W2 + 12, Ld, 14); bt.add(W2 - 12, 22, 8, W2 - 7, Ld, 14);
    M.def('drawer_bottom', { name: 'Drawer bottom (floating)', grp: 'drawers', solid: bt, spec: '6 mm ply, ' + (L.Wdr - 14) + ' × ' + (Ld - 8) + ' mm' });

    /* ===== DOOR PARTS ===== */
    const Hd = L.Hd, Wd = L.Wd, dT = L.dT, st = L.stile, rl = L.rail, Lrd = Wd - 2 * st;
    const stile = new Solid({ grain: 'z' }); stile.add(0, 0, 0, st, dT, Hd);
    stile.cut(st - 18, 5.5, 5, st, 10.5, 25, 'mortiseRail', { fill: true, label: 'Mortise 18 × 5 × 20' }); stile.cut(st - 18, 5.5, Hd - 25, st, 10.5, Hd - 5, 'mortiseRail', { fill: true, label: 'Mortise 18 × 5 × 20' });
    M.def('door_stile', { name: 'Door stile 24 × 16', grp: 'doors', solid: stile, spec: '16 × 24 × ' + Hd + ' mm' });
    const rail = new Solid({ grain: 'x' }); rail.add(-Lrd / 2, 0, 0, Lrd / 2, dT, rl);
    [-1, 1].forEach(sg => rail.add(sg * Lrd / 2, 5.5, 5, sg * (Lrd / 2 + 18), 10.5, 25, 'tenon', { label: 'Tenon 18 × 5 × 20' }));
    const sx = i => st + L.gap + L.slat / 2 + i * (L.slat + L.gap);
    for (let i = 0; i < L.nSlat; i++) rail.cut(sx(i) - Wd / 2 - 4, 5.5, rl - 12, sx(i) - Wd / 2 + 4, 10.5, rl, 'mortiseSlat', { fill: true, label: 'Slat mortise 8 × 5 × 12' });
    M.def('door_rail', { name: 'Door rail 30 × 16', grp: 'doors', solid: rail, spec: '16 × 30 × ' + (Lrd + 36) + ' mm incl. tenons' });
    const Hs = Hd - 2 * rl, slat = new Solid({ grain: 'z' }); slat.add(0, 0, 12, L.slat, dT, 12 + Hs);
    slat.add(2, 5.5, 0, 10, 10.5, 12, 'tenon', { label: 'Tenon 8 × 5 × 12' }); slat.add(2, 5.5, 12 + Hs, 10, 10.5, 24 + Hs, 'tenon', { label: 'Tenon 8 × 5 × 12' });
    M.def('door_slat', { name: 'Door slat 12 × 16', grp: 'doors', solid: slat, spec: '12 × 16 × ' + (Hs + 24) + ' mm incl. tenons' });

    /* ===== STONE + KEYS ===== */
    const mb = new Solid({ grain: 'x', mat: 'marble' }); mb.add(-L.W / 2, -L.D / 2, L.H - 20, L.W / 2, L.D / 2, L.H);
    L.keys.forEach(([kx, ky]) => mb.cut(kx - 6, ky - 6, L.H - 20, kx + 6, ky + 6, L.H - 14, 'socketKey', { fill: true, label: 'Key socket 12 × 12 × 6' }));
    M.def('marble', { name: 'Marble top', grp: 'top', solid: mb, spec: L.W + ' × ' + L.D + ' × 20 mm, honed, 4 blind key sockets (drilled by stone fabricator)' });
    const key = new Solid({ grain: 'z', mat: 'woodL' }); key.add(-6, -6, 0, 6, 6, 14);
    M.def('stone_key', { name: 'Stone key 12 × 12 × 14', grp: 'top', solid: key, spec: 'End-grain up: walnut, glued in panel mortise only' });

    /* ===================== PLACEMENTS ===================== */
    const legM = ([cx, cy, th_]) => M4(cx, cy, 0, th_).multiply(M4(-22, -22, 0));
    const lm = L.legC.map(legM);
    lm.forEach((m, i) => M.put(i % 2 === 0 ? 'leg_A' : 'leg_B', m, 0, { ex: [Math.sign(L.legC[i][0]) * 160, Math.sign(L.legC[i][1]) * 120, 0] }));
    M.put('apron_end', M4(-hx + 4, 0, Hl - 60), 0, { ex: [-170, 0, 0] }); M.put('apron_end', M4(hx - 4, 0, Hl - 60, 180), 0, { ex: [170, 0, 0] });
    M.put('stretcher_end', M4(-hx + 7, 0, L.zs - 15), 0, { ex: [-170, 0, -80] }); M.put('stretcher_end', M4(hx - 7, 0, L.zs - 15, 180), 0, { ex: [170, 0, -80] });
    M.put('apron_long', M4(0, -hy + 4, Hl - 60), 1, { ex: [0, -230, 0] }); M.put('apron_long', M4(0, hy - 4, Hl - 60, 180), 1, { ex: [0, 230, 0] });
    M.put('stretcher_long', M4(0, 0, L.zs - 15), 1, { ex: [0, 0, -190] });
    // pegs: local peg frame z = peg length; rotate to leg-local axis then into world through the leg matrix
    const Ry = new T.Matrix4().makeRotationX(-Math.PI / 2), Rx = new T.Matrix4().makeRotationY(Math.PI / 2);
    lm.forEach((m, i) => {
      const T_ = (x, y, z) => new T.Matrix4().makeTranslation(x, y, z);
      M.put('peg22', m.clone().multiply(T_(32, 0, legZc)).multiply(Ry), 2, {});
      M.put('peg22', m.clone().multiply(T_(0, 32, legZc)).multiply(Rx), 2, {});
      if (i % 2 === 0) M.put('peg30', m.clone().multiply(T_(0, 32, L.zs)).multiply(Rx), 2, {}); else M.put('peg30', m.clone().multiply(T_(32, 0, L.zs)).multiply(Ry), 2, {});
    });
    // fix explode dirs for pegs: outward along their insertion axis (world)
    M.insts.filter(i => i.def.startsWith('peg')).forEach(i => { const o = new T.Vector3(0, 0, 1).transformDirection(i.m).multiplyScalar(-150); i.ex = [o.x, o.y, o.z]; });
    M.put('panel_bottom', M4(0, 0, 0), 3, { ex: [0, 0, 110] });
    M.put('endpanel_L', M4(0, 0, 0), 4, { ex: [-230, 0, 210] }); M.put('endpanel_R', M4(0, 0, 0), 4, { ex: [230, 0, 210] });
    M.put('divider', M4(0, 0, 0), 4, { ex: [0, 0, 260] }); M.put('drawer_rail', M4(0, 0, 0), 4, { ex: [0, 0, 300] });
    const stripZ = [zb1 + 51.5, zm + 61.5];
    stripZ.forEach(zc => { M.put('guide_strip', M4(xL - 4, L.ys0, zc - 5), 4, { ex: [60, 0, 330] }); M.put('guide_strip', M4(xd + 4, L.ys1, zc - 5, 180), 4, { ex: [-60, 0, 330] }); });
    M.put('back_panel', M4(0, 0, 0), 5, { ex: [0, 260, 120] });
    M.put('panel_top', M4(0, 0, 0), 6, { ex: [0, 0, 420] });
    [zb1 + 1.5, zm + 11.5].forEach((z0, di) => {
      const x0 = (xL + xd) / 2, y0 = -hy + 1, o = { ex: [0, -420, 0], kin: 'drawer' + di };
      M.put('drawer_front', M4(x0, y0, z0), 7, o);
      M.put('drawer_side_L', M4(x0, y0, z0), 7, o); M.put('drawer_side_R', M4(x0, y0, z0), 7, o);
      M.put('drawer_back', M4(x0, y0, z0), 7, o); M.put('drawer_bottom', M4(x0, y0, z0), 7, o);
    });
    const z0d = zb1 - 5, dx = [xdd, xR - Wd], dy = [L.tracks[0][0] + 1, L.tracks[1][0] + 1];
    for (let d = 0; d < 2; d++) {
      const xl = dx[d], yd = dy[d], ex = [0, -170 - d * 70, 340], kin = d ? 'doorB' : 'doorA';
      M.put('door_stile', M4(xl, yd, z0d), 8, { ex, kin }); M.put('door_stile', M4(xl + Wd, yd + dT, z0d, 180), 8, { ex, kin });
      M.put('door_rail', M4(xl + Wd / 2, yd, z0d), 8, { ex, kin }); M.put('door_rail', M4(xl + Wd / 2, yd + dT, z0d + Hd, 0, 180), 8, { ex, kin });
      for (let i = 0; i < L.nSlat; i++) M.put('door_slat', M4(xl + sx(i) - L.slat / 2, yd, z0d + rl - 12), 8, { ex, kin });
    }
    L.keys.forEach(([kx, ky]) => M.put('stone_key', M4(kx, ky, L.zt1 - 8), 9, { ex: [0, 0, 480] }));
    M.put('marble', M4(0, 0, 0), 10, { ex: [0, 0, 560] });
    this.finalize();
  }
}
CAD.Sideboard = Sideboard;
})(typeof globalThis !== 'undefined' ? globalThis : window);
