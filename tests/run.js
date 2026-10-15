/* Zero-dependency test runner:  node tests/run.js   (needs `npm install` for three) */
const fs = require('fs'), vm = require('vm'), path = require('path');
const H = require('./helpers.js'), { CAD, THREE, root, load, examples } = H;
vm.runInThisContext(fs.readFileSync(path.join(root, 'src/ai/vision.js'), 'utf8'), { filename: 'vision.js' });
const V = CAD.vision; let pass = 0, fail = 0; const failures = [];
const t = async (name, fn) => { try { await fn(); pass++; console.log('  ✓ ' + name); } catch (e) { fail++; failures.push(name + ': ' + e.message); console.log('  ✗ ' + name + '\n      ' + e.message); } };
const eq = (a, b, m) => { if (a !== b) throw new Error((m || 'expected equal') + ': got ' + a + ', want ' + b); };
const ok = (c, m) => { if (!c) throw new Error(m || 'assertion failed'); };
const near = (a, b, tol, m) => { if (Math.abs(a - b) > tol) throw new Error((m || 'not near') + ': ' + a + ' vs ' + b); };
const ev = (s, sc) => CAD.expr.ev(s, sc || {});
const full = M => { const man = CAD.manifoldReport(M).filter(r => r.bad), it = CAD.interference(M).filter(h => !h.coarse || h.severe), fl = CAD.jointFill(M); return { man, it, fl, bad: fl.filter(r => r.ratio < .999) }; };
(async () => {
  console.log('display units');
  await t('inches snap to 1/16 and print as fractions', () => {
    eq(CAD.fmtInch(0), '0"'); eq(CAD.fmtInch(25.4), '1"'); eq(CAD.fmtInch(12.7), '1/2"'); eq(CAD.fmtInch(19.05), '3/4"');
    eq(CAD.fmtInch(25.4 + 12.7), '1 1/2"'); eq(CAD.fmtInch(25.4 * 12 + 25.4 * 3 / 16), '12 3/16"');
    eq(CAD.fmtThick(19.05), '3/4"'); eq(CAD.fmtThick(25.4 * 1.75), '7/4"'); eq(CAD.fmtThick(25.4), '4/4"');
    eq(CAD.fmtBlank(25.4 * 1.75, 25.4 * 5.5, 25.4 * 24), '7/4" × 5 1/2" × 24"');
    ok(CAD.fmtInch3([25.4, 50.8, 76.2]).indexOf(' × ') > 0);
    ok(/lb$/.test(CAD.fmtLb(1))); near(parseFloat(CAD.fmtLb(1)), 2.2, .05);
    ok(/1\/2"/.test(CAD.inchifyText('Cut a 12.7 mm tenon'))); ok(!/mm/.test(CAD.inchifyText('40 × 40 mm, 15 mm tenon')));
    ok(/11\/16"/.test(CAD.inchifyText('Divider dado 18 x 8'))); ok(/1\/4"/.test(CAD.inchifyText('Back-panel groove 6 wide')));
    const st = CAD.stockForPart(19, 89, 1200, 'American walnut'); ok(/1×|5\/4|4\/4|2×/.test(st.stock), 'stock ' + st.stock);
    const plan = CAD.lumberPlan(CAD.buildSpec(load('bookshelf'))); ok(plan.boards.length > 0 && plan.summary.length > 0, 'lumber plan');
    ok(plan.boards.every(b => b.cuts.length > 0), 'each board has a cut list');
  });
  console.log('expressions');
  await t('arithmetic & precedence', () => { eq(ev('2+3*4'), 14); eq(ev('(2+3)*4'), 20); eq(ev('-2^2'), -4); eq(ev('2^3^2'), 512); eq(ev('10/4'), 2.5); eq(ev('7%4'), 3); });
  await t('functions & conditionals', () => { eq(ev('max(1,5,3)'), 5); eq(ev('clamp(15,0,10)'), 10); near(ev('sin(30)'), .5, 1e-9); near(ev('cos(60)'), .5, 1e-9); eq(ev('if(3>2,10,20)'), 10); eq(ev('if(i==0,1,2)', { i: 0 }), 1); eq(ev('floor(2.7)+ceil(2.1)'), 5); });
  await t('variables', () => eq(ev('W/2-t', { W: 100, t: 8 }), 42));
  await t('rejects unknown variables/functions/characters (no code execution)', () => {
    for (const bad of ['foo+1', 'constructor', 'process', 'alert(1)', '1; 2', 'a.b', '__proto__', '"x"', '1/0', '0/0']) { let threw = false; try { ev(bad); } catch (e) { threw = true; } ok(threw, 'should throw: ' + bad); } });
  console.log('spec validation');
  await t('reports readable, path-qualified errors', () => {
    const M = CAD.buildSpec({ parts: [{ id: 'a', ops: [{ add: [0, 0, 0, 10, 10, 'bogus'] }] }, { id: 'a', ops: [{ add: [0, 0, 0, 1, 1, 1] }] }, { id: 'c', ops: [{ add: [0, 0, 0] }] }, { id: 'd', prims: [{ type: 'torus' }] }, { id: 'e', ops: [{ add: [0, 0, 0, 1, 1, 1], cut: [0, 0, 0, 1, 1, 1] }] }, { ops: [] }] });
    const e = M.errors.join('\n'); ok(/unknown variable "bogus"/.test(e), e); ok(/duplicate id/.test(e), e); ok(/box must be/.test(e), e); ok(/unknown prim type/.test(e), e); ok(/exactly one of/.test(e), e); ok(/missing string "id"/.test(e), e); ok(/parts\[0\]\.ops\[0\]/.test(e), 'path'); });
  await t('empty / non-object specs fail cleanly', () => {
    ok(CAD.buildSpec(null).errors.length); ok(CAD.buildSpec({}).errors.length);
    const empty = CAD.buildSpec({ name: 'Blank', parts: [] });
    eq(empty.errors.length, 0, empty.errors.join('; ')); eq(empty.insts.length, 0); eq(empty.defs.size, 0);
    ok(CAD.buildSpec({ parts: [{ id: 'x', ops: [{ add: [0, 0, 0, 1, 1, 1] }], instances: [] }] }).errors.some(e => /no parts were placed/.test(e)));
  });
  await t('repeat guard', () => ok(/too large/.test(CAD.buildSpec({ parts: [{ id: 'x', ops: [{ add: [0, 0, 0, 1, 1, 1], repeat: { count: 100000 } }] }] }).errors.join())));
  console.log('examples');
  for (const n of examples()) await t(n + ': builds, watertight, no interference, every joint filled', () => {
    const M = CAD.buildSpec(load(n)); eq(M.errors.length, 0, M.errors.join('; ')); const r = full(M); eq(r.man.length, 0, 'non-manifold ' + r.man.map(x => x.id)); eq(r.it.length, 0, 'interference ' + r.it.slice(0, 3).map(x => x.a + '×' + x.b)); eq(r.bad.length, 0, 'unfilled ' + r.bad.slice(0, 3).map(x => x.part + '/' + x.tag));
    if (['sideboard', 'bookshelf'].includes(n)) ok(r.fl.length > 20, 'joint-fill check must actually run (' + r.fl.length + ')'); });
  await t('sideboard spec reproduces the original generator exactly', () => {
    const ctx = {}; const prev = { MATS: CAD.MATS, GROUPS: CAD.GROUPS, STEPS: CAD.STEPS }; vm.runInThisContext(fs.readFileSync(path.join(root, 'tools/legacy/sideboard-model.js'), 'utf8'), { filename: 'legacy' });
    const L = new CAD.Sideboard(), S = CAD.buildSpec(load('sideboard')); eq(S.defs.size, L.defs.size, 'part types'); eq(S.insts.length, L.insts.length, 'pieces');
    L.defs.forEach((d, id) => { const s = S.defs.get(id); ok(s, 'missing ' + id); near(s.vol, d.vol, d.vol * 1e-6 + 1e-6, 'volume of ' + id); });
    const key = (M, i) => i.def + '#' + i.qtyIdx; const lb = {}; L.insts.forEach(i => lb[key(L, i)] = CAD.instAABB(L, i)); S.insts.forEach(i => { const a = CAD.instAABB(S, i), b = lb[key(S, i)]; ok(b, 'inst ' + key(S, i)); a.forEach((v, k) => near(v, b[k], .01, 'bounds of ' + key(S, i))); }); });
  console.log('parameter sweeps (every slider at min, max, and all-min / all-max)');
  for (const n of examples()) { const spec = load(n), M0 = CAD.buildSpec(spec); if (!M0.paramDefs.length) continue;
    await t(n + ': ' + M0.paramDefs.length + ' params stay valid across their ranges', () => {
      const cases = []; M0.paramDefs.forEach(p => { cases.push({ [p.key]: p.min }, { [p.key]: p.max }, { [p.key]: Math.round((p.min + p.max) / 2 / p.step) * p.step }); });
      const mn = {}, mx = {}; M0.paramDefs.forEach(p => { mn[p.key] = p.min; mx[p.key] = p.max; }); cases.push(mn, mx);
      cases.forEach(ov => { const M = CAD.buildSpec(spec, ov); eq(M.errors.length, 0, JSON.stringify(ov) + ' → ' + M.errors.join('; ')); const r = full(M); eq(r.man.length, 0, JSON.stringify(ov) + ' non-manifold'); eq(r.it.length, 0, JSON.stringify(ov) + ' interference ' + r.it.slice(0, 2).map(x => x.a + '×' + x.b)); eq(r.bad.length, 0, JSON.stringify(ov) + ' unfilled ' + r.bad.slice(0, 2).map(x => x.part + '/' + x.tag)); }); }); }
  console.log('export (orientation, scale, split, nest, zip)');
  const E = CAD.exporter;
  for (const n of examples()) await t(n + ': print pieces valid at 8 scale/bed combinations', () => {
    const M = CAD.buildSpec(load(n));
    for (const [div, bed] of [[1, [220, 220, 250]], [2, [256, 256, 256]], [4, [220, 220, 250]], [5, [180, 180, 180]], [8, [256, 256, 256]], [10, [150, 150, 150]], [20, [100, 100, 100]], [1, [400, 400, 400]]]) {
      const mult = 1 / div; let pieces = 0, nested = 0; M.defs.forEach(d => { const ps = E.printPieces(d, mult, bed, true); let vol = 0; ps.forEach(p => { pieces++; eq(CAD.manifoldPos(p.pos), 0, d.id + ' piece not watertight @1:' + div); const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p.pos, 3)); vol += CAD.volume(g) / Math.pow(mult, 3); if (d.solid.splittable) ok(!p.over, d.id + ' oversize @1:' + div + ' bed ' + bed); });
        if (d.solid.splittable) near(vol / d.vol, 1, .01, d.id + ' volume not conserved @1:' + div); });
      const N = E.nest(M, mult, bed, true); N.plates.forEach(pl => pl.items.forEach(() => nested++)); const mesh = [...M.defs.values()].filter(d => !d.solid.splittable).reduce((s, d) => s + d.qty, 0); ok(nested + N.over.length >= pieces - 0, 'nest must place or report every piece'); } });
  await t('ZIP + STL round trip with CRC', () => {
    const M = CAD.buildSpec(load('bookshelf')), files = E.stlFiles(M, [...M.defs.values()], { mult: .2, bed: [220, 220, 250], split: true }); const z = CAD.zip(files.map(f => ({ name: f.name, data: f.data })).concat([{ name: 'a/readme.txt', data: 'hello' }])), list = CAD.unzipList(z);
    eq(list.length, files.length + 1); list.forEach((e, i) => { ok(e.crcOk, 'crc ' + e.name); if (i < files.length) { const tr = CAD.stlParse(e.data); eq(tr.length / 9, files[i].tris, 'triangle count ' + e.name); eq(CAD.manifoldPos(tr), 0, 'manifold ' + e.name); } }); });
  await t('cut list & CSV', () => { const M = CAD.buildSpec(load('bookshelf')), c = E.cutCSV(M); ok(c.split('\n').length > M.defs.size, 'rows'); ok(/Shelf/.test(c)); });
  console.log('mesh interference, wedge, schema');
  await t('validateSpec catches structural mistakes before build', () => {
    const bad = CAD.validateSpec({ parts: [{ id: 'a', ops: [{ add: [0, 0, 0, 1, 1] }] }, { id: 'a', prims: [{ type: 'torus' }] }] });
    ok(!bad.ok); ok(bad.errors.some(e => /duplicate id/.test(e))); ok(bad.errors.some(e => /box must be/.test(e))); ok(bad.errors.some(e => /unknown prim type/.test(e)));
    ok(CAD.validateSpec(V.EXAMPLE).ok);
    ok(CAD.validateSpec({ name: 'Blank', parts: [] }).ok);
  });
  await t('wedge and rotated box mesh prims build watertight', () => {
    const spec = {
      name: 'Mitre frame', units: 'mm', parts: [
        { id: 'rail', name: 'Rail', kind: 'mesh', material: 'oak', prims: [{ type: 'wedge', min: [0, 0, 0], max: [200, 40, 18], tip: '+x', angle: 45 }], instances: [{ pos: [0, 0, 0] }] },
        { id: 'rail2', name: 'Rail B', kind: 'mesh', material: 'oak', prims: [{ type: 'box', min: [0, 0, 0], max: [200, 40, 18], rot: [0, 0, 0] }], instances: [{ pos: [0, 80, 0] }] }
      ]
    };
    const M = CAD.buildSpec(spec); eq(M.errors.length, 0, M.errors.join('; '));
    ok(M.defs.get('rail').vol > 0); ok(M.defs.get('rail').vol < 200 * 40 * 18, 'wedge volume less than full box');
    const man = CAD.manifoldReport(M).filter(r => r.bad); eq(man.length, 0, 'non-manifold ' + man.map(x => x.id));
  });
  await t('coarse AABB interference reports mesh overlaps; exact solids unchanged', () => {
    const solidOk = CAD.buildSpec(V.EXAMPLE);
    eq(CAD.interference(solidOk).length, 0);
    const clash = {
      name: 'Clash', units: 'mm', parts: [
        { id: 'a', kind: 'mesh', material: 'oak', prims: [{ type: 'box', min: [0, 0, 0], max: [50, 50, 50] }], instances: [{ pos: [0, 0, 0] }] },
        { id: 'b', kind: 'mesh', material: 'oak', prims: [{ type: 'box', min: [5, 5, 5], max: [55, 55, 55] }], instances: [{ pos: [0, 0, 0] }] }
      ]
    };
    const M = CAD.buildSpec(clash); eq(M.errors.length, 0, M.errors.join('; '));
    const hits = CAD.interference(M); ok(hits.length >= 1, 'expected coarse hit'); ok(hits.every(h => h.coarse), 'mesh pairs are coarse');
    ok(hits.some(h => h.severe), 'near-coincident boxes are severe');
    const rep = V.evaluate(clash); ok(!rep.ok); ok(/coarse AABB/.test(rep.text));
    const lamp = CAD.buildSpec(load('lamp'));
    const soft = CAD.interference(lamp).filter(h => h.coarse && !h.severe);
    ok(soft.length >= 1, 'lamp has soft assembly contacts');
    ok(!CAD.interference(lamp).some(h => h.severe), 'lamp has no severe mesh clash');
  });
  await t('spatialPairs covers all pairs for small N and scales for large N', () => {
    const items = [];
    for (let i = 0; i < 40; i++) items.push({ _ab: [i * 30, 0, 0, i * 30 + 20, 20, 20] });
    const pairs = CAD.spatialPairs(items, x => x._ab, 25);
    ok(pairs.length >= 20, 'nearby pairs found ' + pairs.length);
    ok(pairs.length < 40 * 39 / 2, 'not full brute force when grid helps');
    const tiny = [{ _ab: [0, 0, 0, 1, 1, 1] }, { _ab: [2, 0, 0, 3, 1, 1] }];
    eq(CAD.spatialPairs(tiny, x => x._ab).length, 1);
    const many = [];
    for (let i = 0; i < 30; i++) many.push({ _ab: [i * 100, i * 100, 0, i * 100 + 10, i * 100 + 10, 10] });
    ok(CAD.spatialPairs(many, x => x._ab, 50).length < 30 * 29 / 2);
  });
  console.log('AI module (mock provider)');
  const INV = { object: 'Plant stand', aspect: { w: 1, d: 1, h: 1.4 }, counts: { legs: 4, drawers: 0, doors: 0, shelves: 0, slats: 0 }, parts: [{ role: 'leg', count: 4, shape: 'square' }, { role: 'top', count: 1, shape: 'panel' }] };
  await t('prompt example is itself a valid, clean spec (prompt cannot drift from the engine)', () => { const r = V.evaluate(V.EXAMPLE); ok(r.ok, r.text); ok(r.fillChecked >= 4); });
  await t('prompt documents every primitive, op and top-level key the engine accepts', () => { for (const w of ['box', 'cylinder', 'cone', 'tube', 'sphere', 'revolve', 'extrude', 'wedge', '"add"', '"cut"', '"fill"', 'params', 'materials', 'groups', 'steps', 'kinematics', 'instances', 'repeat', 'explode', 'if(c,a,b)']) ok(V.SPEC_DOC.includes(w), 'doc missing ' + w); });
  await t('extractJSON: fences, prose, braces inside strings, truncation', () => {
    eq(V.extractJSON('```json\n{"a":1}\n```').a, 1); eq(V.extractJSON('Here you go: {"a":{"b":"}{"}} thanks').a.b, '}{'); let threw = false; try { V.extractJSON('{"a":[1,2'); } catch (e) { threw = /truncated/.test(e.message); } ok(threw, 'truncation not detected'); threw = false; try { V.extractJSON('no json'); } catch (e) { threw = true; } ok(threw); });
  await t('evaluate flags overlap, unfilled joints and bad expressions with actionable text', () => {
    const bad = JSON.parse(JSON.stringify(V.EXAMPLE)); bad.parts[1].ops.pop(); bad.parts[0].instances[0].pos[2] = 5; const r = V.evaluate(bad); ok(!r.ok); ok(r.interference.length > 0, 'interference'); ok(/INTERFERENCE/.test(r.text)); const bad2 = JSON.parse(JSON.stringify(V.EXAMPLE)); bad2.parts[1].ops[1].cut[5] = 'H-2'; const r2 = V.evaluate(bad2); ok(r2.underfilled.length > 0, 'underfilled'); ok(/UNFILLED/.test(r2.text)); const r3 = V.evaluate({ parts: [{ id: 'x', ops: [{ add: [0, 0, 0, 1, 1, 'zz'] }] }] }); ok(/unknown variable "zz"/.test(r3.text)); });
  await t('likeness scores aspect and role counts against inventory', () => {
    const good = V.evaluate(V.EXAMPLE, { inventory: INV }); ok(good.ok); ok(good.likeness); ok(good.likeness.penalty < 20, 'good penalty ' + good.likeness.penalty);
    const tall = JSON.parse(JSON.stringify(INV)); tall.aspect = { w: 1, d: 1, h: 4 }; const badAsp = V.evaluate(V.EXAMPLE, { inventory: tall }); ok(badAsp.likeness.penalty >= 20, 'aspect penalty'); ok(/LIKENESS aspect/.test(badAsp.text));
    const many = JSON.parse(JSON.stringify(INV)); many.counts.legs = 8; const badCnt = V.evaluate(V.EXAMPLE, { inventory: many }); ok(badCnt.likeness.countMismatches.some(m => m.role === 'legs')); ok(/LIKENESS count/.test(badCnt.text));
    eq(V.maskIoU([1, 1, 0, 0], [1, 0, 1, 0]), 1 / 3); eq(V.maskIoU([1, 1], [1, 1]), 1);
  });
  await t('parseDims reads fractions, triplets, and structured fields', () => {
    near(V.parseInch('12 3/16'), (12 + 3 / 16) * 25.4, .01);
    near(V.parseInch('3/4'), 19.05, .01);
    const a = V.parseDims('overall height 33 1/2", oak'); ok(a.hMm > 800 && a.hMm < 860, 'h from labeled ' + a.hMm);
    near(V.parseDims('height 420 mm').hMm, 420, .5); near(V.parseInch('420 mm'), 420, .01);
    const b = V.parseDims('36 × 18 × 30'); near(b.wMm, 36 * 25.4, .5); near(b.dMm, 18 * 25.4, .5); near(b.hMm, 30 * 25.4, .5);
    const c = V.parseDims('', { w: '24', d: '12', h: '36' }); near(c.wMm, 24 * 25.4, .5); near(c.hMm, 36 * 25.4, .5);
    ok(/TARGET OVERALL SIZE/.test(V.composeHints('oak', c)));
  });
  await t('drawing mode prompts mention technical drawing and USER METRICS', () => {
    const metrics = { wMm: 900, dMm: 400, hMm: 750 };
    const inv = V.buildInventoryPrompt({ inputMode: 'drawing', metrics, hints: 'oak' });
    ok(/TECHNICAL DRAWING|dimensioned sketch/i.test(inv)); ok(/USER METRICS/.test(inv)); ok(/900/.test(inv));
    const p = V.buildPrompt({ round: 1, inputMode: 'drawing', metrics, hints: 'oak', inventory: INV });
    ok(/TECHNICAL DRAWING|dimensioned sketch/i.test(p)); ok(/USER METRICS/.test(p)); ok(/authoritative/i.test(p));
  });
  await t('metric size mismatch adds likeness penalty', () => {
    const M0 = CAD.buildSpec(V.EXAMPLE);
    const wrong = V.evaluate(V.EXAMPLE, { inventory: INV, metrics: { wMm: M0.size[0] * 2, dMm: M0.size[1], hMm: M0.size[2] } });
    ok(wrong.likeness.penalty >= 20, 'metric penalty ' + wrong.likeness.penalty); ok(/METRIC size/.test(wrong.text));
    const okM = V.evaluate(V.EXAMPLE, { inventory: INV, metrics: { wMm: M0.size[0], dMm: M0.size[1], hMm: M0.size[2] } });
    ok(okM.likeness.penalty < 5, 'exact metrics ok ' + okM.likeness.penalty);
  });
  await t('workspace pack + unpack round-trips designs', () => {
    const Store = CAD.store;
    const docs = { d1: { id: 'd1', name: 'A', spec: { name: 'A', parts: [] }, ov: {}, updated: 1 } };
    const pack = Store.pack(docs, 'd1');
    eq(pack.kind, 'image-to-cad-workspace'); eq(pack.activeId, 'd1');
    const back = Store.unpack(JSON.stringify(pack));
    eq(Object.keys(back.docs).length, 1); eq(back.docs.d1.name, 'A');
    let threw = false; try { Store.unpack({ kind: 'nope', docs: {} }); } catch (e) { threw = true; } ok(threw);
    ok(Store.normalize({ docs: { d1: docs.d1 }, activeId: 'd1' }));
  });
  await t('drawing design run injects metrics into inventory and builder', async () => {
    const mock = { responses: [JSON.stringify(INV), JSON.stringify(V.EXAMPLE)] }, logs = [];
    const metrics = { wMm: 300, dMm: 300, hMm: 420 };
    const res = await V.run({ image: 'data:image/png;base64,AAAA', hints: 'oak', metrics, inputMode: 'drawing', provider: { kind: 'mock', mock }, maxRounds: 1, onLog: m => logs.push(m) });
    ok(res.rep.ok); ok(logs.some(l => /drawing/i.test(l)));
    ok(/TECHNICAL DRAWING|dimensioned sketch|USER METRICS/i.test(mock.calls[0].text));
    ok(/USER METRICS/.test(mock.calls[1].text) && /300/.test(mock.calls[1].text));
    ok(res.inventory && res.inventory.overallGuessMm && res.inventory.overallGuessMm.w === 300);
  });
  await t('revise prompt sends the current spec and the requested changes', async () => {
    const mock = { responses: [JSON.stringify(V.EXAMPLE)] };
    const res = await V.run({ task: 'revise', prevSpec: V.EXAMPLE, hints: 'make it 4 inches taller', focusParts: [{ id: 'leg', name: 'Leg' }], provider: { kind: 'mock', mock }, maxRounds: 1 });
    ok(res.rep.ok); eq(mock.calls.length, 1); ok(/REQUESTED CHANGES/.test(mock.calls[0].text) && /make it 4 inches taller/.test(mock.calls[0].text) && /CURRENT SPEC/.test(mock.calls[0].text) && /FOCUS/.test(mock.calls[0].text) && /leg/.test(mock.calls[0].text));
  });
  await t('inventory pass runs before design and seeds the builder prompt', async () => {
    const mock = { responses: [JSON.stringify(INV), JSON.stringify(V.EXAMPLE)] }, logs = [];
    const res = await V.run({ image: 'data:image/png;base64,AAAA', hints: 'oak', provider: { kind: 'mock', mock }, maxRounds: 1, onLog: m => logs.push(m) });
    ok(res.rep.ok); ok(res.inventory); eq(mock.calls.length, 2);
    ok(/visual inventory|INVENTORY_DOC|aspect/.test(mock.calls[0].text) || /Study the attached picture and return ONE JSON object/.test(mock.calls[0].text), 'inventory prompt');
    ok(/INVENTORY/.test(mock.calls[1].text) && /Plant stand/.test(mock.calls[1].text), 'builder got inventory');
    ok(logs.some(l => /Inventory/.test(l)));
    ok(!res.staged, 'simple inventory skips stages');
  });
  await t('mergeSpecs keeps base parts and overlays next by id', () => {
    const a = { name: 'A', parts: [{ id: 'leg', name: 'Leg' }, { id: 'top', name: 'Top' }], materials: { oak: { base: 'oak' } } };
    const b = { name: 'B', parts: [{ id: 'top', name: 'Top v2' }, { id: 'drawer', name: 'Drawer' }], materials: { pine: { base: 'pine' } } };
    const m = V.mergeSpecs(a, b);
    eq(m.name, 'B'); eq(m.parts.length, 3); ok(m.parts.some(p => p.id === 'leg')); ok(m.parts.find(p => p.id === 'top').name === 'Top v2'); ok(m.materials.oak && m.materials.pine);
  });
  await t('staged design runs carcass → interiors → refine for complex inventory', async () => {
    const complex = { object: 'Sideboard', aspect: { w: 3, d: 1, h: 1.5 }, counts: { legs: 4, drawers: 2, doors: 0, shelves: 0, slats: 0 }, parts: [{ role: 'leg', count: 4 }, { role: 'drawer', count: 2 }, { role: 'top', count: 1 }, { role: 'side', count: 2 }, { role: 'bottom', count: 1 }, { role: 'back', count: 1 }] };
    ok(V.needsStages(complex)); ok(!V.needsStages(INV));
    const mock = { responses: [JSON.stringify(complex), JSON.stringify(V.EXAMPLE), JSON.stringify(V.EXAMPLE), JSON.stringify(V.EXAMPLE)] }, logs = [];
    const res = await V.run({ image: 'data:image/png;base64,AAAA', provider: { kind: 'mock', mock }, maxRounds: 1, staged: true, inventory: complex, onLog: m => logs.push(m) });
    ok(res.staged); ok(res.rep.ok);
    ok(logs.some(l => /Staged design/.test(l)));
    ok(mock.calls.some(c => /STAGE FOCUS/.test(c.text) && /carcass/i.test(c.text)));
    ok(mock.calls.some(c => /STAGE FOCUS/.test(c.text) && /interior/i.test(c.text)));
  });
  await t('Gauntlet loop: bad first draft → critic feedback reaches the model → fixed draft accepted', async () => {
    const bad = JSON.parse(JSON.stringify(V.EXAMPLE)); bad.parts[0].instances[0].pos[2] = 5; const mock = { responses: [JSON.stringify(INV), 'Sure!\n```json\n' + JSON.stringify(bad) + '\n```', JSON.stringify(V.EXAMPLE)] }, logs = [];
    const res = await V.run({ image: 'data:image/png;base64,AAAA', hints: 'height 420 mm', provider: { kind: 'mock', mock }, maxRounds: 3, onLog: m => logs.push(m) });
    ok(res.rep.ok, 'final must pass'); eq(res.round, 2); eq(mock.calls.length, 3); ok(/CRITIC REPORT/.test(mock.calls[2].text) && /INTERFERENCE/.test(mock.calls[2].text), 'feedback missing'); ok(/PREVIOUS SPEC/.test(mock.calls[2].text)); ok(/height 420 mm/.test(mock.calls[1].text), 'hints missing'); eq(mock.calls[0].images, 1); ok(logs.some(l => /passes every check/.test(l))); });
  await t('Gauntlet loop: unparsable reply is retried, loop gives best effort after max rounds', async () => {
    const mock = { responses: [JSON.stringify(INV), '{"parts": [ {"id":"x"', 'not json at all', JSON.stringify({ parts: [{ id: 'a', ops: [{ add: [0, 0, 0, 10, 10, 'q'] }] }] })] };
    const res = await V.run({ image: 'data:image/png;base64,AAAA', provider: { kind: 'mock', mock }, maxRounds: 3 }); ok(!res.rep.ok); eq(mock.calls.length, 4); ok(/could not be parsed/.test(mock.calls[2].text), 'parse feedback'); });
  await t('Visual critic round attaches the render as image 2 and keeps the last passing spec', async () => {
    const mock = { responses: [JSON.stringify(INV), JSON.stringify(V.EXAMPLE), JSON.stringify({ parts: [{ id: 'z', ops: [{ add: [0, 0, 0, 1, 1, 'nope'] }] }] })] }; let rendered = 0;
    const res = await V.run({ image: 'data:image/png;base64,AAAA', provider: { kind: 'mock', mock }, maxRounds: 2, visual: true, render: async () => { rendered++; return 'data:image/png;base64,BBBB'; } });
    eq(rendered, 1); eq(mock.calls.length, 3); eq(mock.calls[2].images, 2); ok(/VISUAL CRITIQUE/.test(mock.calls[2].text)); ok(res.rep.ok, 'must fall back to the passing spec'); eq(res.round, 1); });
  console.log('\n' + pass + ' passed, ' + fail + ' failed'); if (fail) { console.log('\nFAILURES:\n - ' + failures.join('\n - ')); process.exit(1); }
})();
