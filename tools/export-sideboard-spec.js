/* Regenerates examples/sideboard.json from the original hand-coded sideboard generator in tools/legacy.
   Run: node tools/export-sideboard-spec.js   (kept as proof that the spec format can express a fully detailed model) */
const fs = require('fs'), vm = require('vm'), path = require('path'); global.THREE = require('three'); global.window = global;
const root = path.join(__dirname, '..');
['src/core/geo.js', 'src/core/csg.js', 'tools/legacy/sideboard-model.js', 'src/core/checks.js', 'tools/legacy/sideboard-guide.js'].forEach(f => vm.runInThisContext(fs.readFileSync(path.join(root, f), 'utf8'), { filename: f }));
const T = THREE, M = new CAD.Sideboard(), L = M.L, hex = c => '#' + c.toString(16).padStart(6, '0'), r3 = v => Math.round(v * 1000) / 1000, eq = (a, b) => a.every((v, i) => Math.abs(v - b[i]) < 1e-6);
const spec = { name: 'Walnut console / sideboard with marble top', units: 'mm', description: 'Hardware-free walnut sideboard: pegged mortise-and-tenon base, housed-dado carcass with floating back, box-jointed drawers, slatted sliding doors in routed tracks, keyed stone top. Auto-exported from the original hand-coded generator (1400 × 400 × 850 mm).',
  assumptions: ['Dimensions come from the reference photo proportions, not a measured piece.'], params: {}, materials: {}, groups: CAD.GROUPS.map(g => ({ id: g.id, name: g.name, color: hex(g.color) })), steps: CAD.STEPS.slice(), kinematics: {}, parts: [] };
Object.entries(CAD.MATS).forEach(([k, m]) => { spec.materials[k] = { name: m.name, color: hex(m.color), metal: m.metal, rough: m.rough, rho: m.rho, tex: m.tex }; });
spec.materials.woodL.tint = '#f0cfa4'; spec.materials.ply.tint = '#e6c9a4'; spec.materials.wood.tint = '#ffffff'; spec.materials.marble.alpha = undefined;
const rotOf = m => { const q = new T.Quaternion(), p = new T.Vector3(), s = new T.Vector3(); m.decompose(p, q, s); const e = new T.Euler().setFromQuaternion(q, 'ZYX'); const sn = a => Math.round(a * 180 / Math.PI / 90) * 90; return { pos: [r3(p.x), r3(p.y), r3(p.z)], rot: [sn(e.x), sn(e.y), sn(e.z)] }; };
M.defs.forEach(d => { const s = d.solid, ops = [];
  s.adds.forEach(b => { const f = s.feat.find(f => f.kind === 'add' && eq(f.box, b)), o = { add: b }; if (f) { o.tag = f.tag; if (f.label) o.label = f.label; } ops.push(o); });
  s.cuts.forEach(b => { const f = s.feat.find(f => f.kind === 'cut' && eq(f.box, b)), o = { cut: b }; if (f) { o.tag = f.tag; if (f.fill) o.fill = true; if (f.label) o.label = f.label; } ops.push(o); });
  spec.parts.push({ id: d.id, name: d.name, group: d.grp, material: s.mat, grain: s.grain, spec: d.spec || '', notes: d.note ? [d.note] : [], ops,
    instances: M.insts.filter(i => i.def === d.id).map(i => { const o = rotOf(i.m); if (!o.rot.some(v => v)) delete o.rot; o.step = i.step; o.explode = i.ex.map(r3); if (i.kin) o.kin = i.kin; return o; }) }); });
const tr = Math.round(L.Wdb - L.Wd); spec.kinematics = { drawer0: { label: 'Lower drawer', axis: [0, -1, 0], range: [0, 300] }, drawer1: { label: 'Upper drawer', axis: [0, -1, 0], range: [0, 300] }, doorA: { label: 'Left door', axis: [1, 0, 0], range: [0, tr] }, doorB: { label: 'Right door', axis: [-1, 0, 0], range: [0, tr] } };
spec.guide = CAD.guideSteps(M);
fs.writeFileSync(path.join(root, 'examples/sideboard.json'), JSON.stringify(spec));
console.log('wrote examples/sideboard.json', (fs.statSync(path.join(root, 'examples/sideboard.json')).size / 1024).toFixed(0) + ' KB', 'parts', spec.parts.length);
