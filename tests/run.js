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
const full = M => { const man = CAD.manifoldReport(M).filter(r => r.bad), it = CAD.interference(M), fl = CAD.jointFill(M); return { man, it, fl, bad: fl.filter(r => r.ratio < .999) }; };
(async () => {
  console.log('display units');
  await t('inches snap to 1/16 and print as fractions', () => {
    eq(CAD.fmtInch(0), '0"'); eq(CAD.fmtInch(25.4), '1"'); eq(CAD.fmtInch(12.7), '1/2"'); eq(CAD.fmtInch(19.05), '3/4"');
    eq(CAD.fmtInch(25.4 + 12.7), '1 1/2"'); eq(CAD.fmtInch(25.4 * 12 + 25.4 * 3 / 16), '12 3/16"');
    ok(CAD.fmtInch3([25.4, 50.8, 76.2]).indexOf(' × ') > 0);
    ok(/lb$/.test(CAD.fmtLb(1))); near(parseFloat(CAD.fmtLb(1)), 2.2, .05);
    ok(/1\/2"/.test(CAD.inchifyText('Cut a 12.7 mm tenon'))); ok(!/mm/.test(CAD.inchifyText('40 × 40 mm, 15 mm tenon')));
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
  await t('empty / non-object specs fail cleanly', () => { ok(CAD.buildSpec(null).errors.length); ok(CAD.buildSpec({}).errors.length); ok(CAD.buildSpec({ parts: [] }).errors.length); });
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
  console.log('AI module (mock provider)');
  await t('prompt example is itself a valid, clean spec (prompt cannot drift from the engine)', () => { const r = V.evaluate(V.EXAMPLE); ok(r.ok, r.text); ok(r.fillChecked >= 4); });
  await t('prompt documents every primitive, op and top-level key the engine accepts', () => { for (const w of ['box', 'cylinder', 'cone', 'tube', 'sphere', 'revolve', 'extrude', '"add"', '"cut"', '"fill"', 'params', 'materials', 'groups', 'steps', 'kinematics', 'instances', 'repeat', 'explode', 'if(c,a,b)']) ok(V.SPEC_DOC.includes(w), 'doc missing ' + w); });
  await t('extractJSON: fences, prose, braces inside strings, truncation', () => {
    eq(V.extractJSON('```json\n{"a":1}\n```').a, 1); eq(V.extractJSON('Here you go: {"a":{"b":"}{"}} thanks').a.b, '}{'); let threw = false; try { V.extractJSON('{"a":[1,2'); } catch (e) { threw = /truncated/.test(e.message); } ok(threw, 'truncation not detected'); threw = false; try { V.extractJSON('no json'); } catch (e) { threw = true; } ok(threw); });
  await t('evaluate flags overlap, unfilled joints and bad expressions with actionable text', () => {
    const bad = JSON.parse(JSON.stringify(V.EXAMPLE)); bad.parts[1].ops.pop(); bad.parts[0].instances[0].pos[2] = 5; const r = V.evaluate(bad); ok(!r.ok); ok(r.interference.length > 0, 'interference'); ok(/INTERFERENCE/.test(r.text)); const bad2 = JSON.parse(JSON.stringify(V.EXAMPLE)); bad2.parts[1].ops[1].cut[5] = 'H-2'; const r2 = V.evaluate(bad2); ok(r2.underfilled.length > 0, 'underfilled'); ok(/UNFILLED/.test(r2.text)); const r3 = V.evaluate({ parts: [{ id: 'x', ops: [{ add: [0, 0, 0, 1, 1, 'zz'] }] }] }); ok(/unknown variable "zz"/.test(r3.text)); });
  await t('revise prompt sends the current spec and the requested changes', async () => {
    const mock = { responses: [JSON.stringify(V.EXAMPLE)] };
    const res = await V.run({ task: 'revise', prevSpec: V.EXAMPLE, hints: 'make it 4 inches taller', focusParts: [{ id: 'leg', name: 'Leg' }], provider: { kind: 'mock', mock }, maxRounds: 1 });
    ok(res.rep.ok); ok(/REQUESTED CHANGES/.test(mock.calls[0].text) && /make it 4 inches taller/.test(mock.calls[0].text) && /CURRENT SPEC/.test(mock.calls[0].text) && /FOCUS/.test(mock.calls[0].text) && /leg/.test(mock.calls[0].text));
  });
  await t('Gauntlet loop: bad first draft → critic feedback reaches the model → fixed draft accepted', async () => {
    const bad = JSON.parse(JSON.stringify(V.EXAMPLE)); bad.parts[0].instances[0].pos[2] = 5; const mock = { responses: ['Sure!\n```json\n' + JSON.stringify(bad) + '\n```', JSON.stringify(V.EXAMPLE)] }, logs = [];
    const res = await V.run({ image: 'data:image/png;base64,AAAA', hints: 'height 420 mm', provider: { kind: 'mock', mock }, maxRounds: 3, onLog: m => logs.push(m) });
    ok(res.rep.ok, 'final must pass'); eq(res.round, 2); eq(mock.calls.length, 2); ok(/CRITIC REPORT/.test(mock.calls[1].text) && /INTERFERENCE/.test(mock.calls[1].text), 'feedback missing'); ok(/PREVIOUS SPEC/.test(mock.calls[1].text)); ok(/height 420 mm/.test(mock.calls[0].text), 'hints missing'); eq(mock.calls[0].images, 1); ok(logs.some(l => /passes every check/.test(l))); });
  await t('Gauntlet loop: unparsable reply is retried, loop gives best effort after max rounds', async () => {
    const mock = { responses: ['{"parts": [ {"id":"x"', 'not json at all', JSON.stringify({ parts: [{ id: 'a', ops: [{ add: [0, 0, 0, 10, 10, 'q'] }] }] })] };
    const res = await V.run({ image: 'data:image/png;base64,AAAA', provider: { kind: 'mock', mock }, maxRounds: 3 }); ok(!res.rep.ok); eq(mock.calls.length, 3); ok(/could not be parsed/.test(mock.calls[1].text), 'parse feedback'); });
  await t('Visual critic round attaches the render as image 2 and keeps the last passing spec', async () => {
    const mock = { responses: [JSON.stringify(V.EXAMPLE), JSON.stringify({ parts: [{ id: 'z', ops: [{ add: [0, 0, 0, 1, 1, 'nope'] }] }] })] }; let rendered = 0;
    const res = await V.run({ image: 'data:image/png;base64,AAAA', provider: { kind: 'mock', mock }, maxRounds: 2, visual: true, render: async () => { rendered++; return 'data:image/png;base64,BBBB'; } });
    eq(rendered, 1); eq(mock.calls.length, 2); eq(mock.calls[1].images, 2); ok(/VISUAL CRITIQUE/.test(mock.calls[1].text)); ok(res.rep.ok, 'must fall back to the passing spec'); eq(res.round, 1); });
  console.log('\n' + pass + ' passed, ' + fail + ' failed'); if (fail) { console.log('\nFAILURES:\n - ' + failures.join('\n - ')); process.exit(1); }
})();
