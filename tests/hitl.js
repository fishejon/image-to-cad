/* Phase 3 HITL helpers (no live DB required):  node tests/hitl.js */
const fs = require('fs');
const path = require('path');
const hitl = require('../server/hitl');
const storage = require('../server/storage');
const { scoreCase, loadCases } = require('../tools/score-golden');
let fails = 0;
const check = (c, m) => { console.log((c ? '  ✓ ' : '  ✗ ') + m); if (!c) fails++; };

console.log('schema + validate');
{
  const sql = fs.readFileSync(path.join(__dirname, '..', 'server', 'sql', '001_hitl.sql'), 'utf8');
  check(/CREATE TABLE IF NOT EXISTS runs/.test(sql) && /feedback/.test(sql) && /examples/.test(sql), 'SQL defines runs/feedback/examples');
  const bad = hitl.validateExample({});
  check(!bad.ok, 'example requires payload');
  const ok = hitl.validateExample({ runId: 'r1', object: 'stool', inventory: { object: 'stool' } });
  check(ok.ok && ok.row.runId === 'r1', 'accepts example');
}

console.log('storage consent + hash');
{
  check(storage.enabled() === false, 'storage disabled without R2 env');
  const png = Buffer.from('89504e470d0a1a0a', 'hex');
  (async () => {
    const no = await storage.uploadRunImage({ runId: 'r1', consent: false, bytes: png });
    check(!no.ok && /consent/.test(no.error), 'rejects without consent');
    const yes = await storage.uploadRunImage({ runId: 'r_ok', consent: true, bytes: png, mediaType: 'image/png' });
    check(yes.ok && yes.imageHash && yes.imageConsent === true && yes.skippedUpload === true, 'hashes image when R2 unset');

    console.log('golden scorer');
    const cases = loadCases();
    check(cases.length >= 5, 'at least 5 golden cases');
    const pass = scoreCase(cases[0].expected, cases[0].actual);
    check(pass.ok, 'seeded actual matches expected for g01');
    const fail = scoreCase(cases[0].expected, { counts: { legs: 99 }, structure: { memberContinuity: 'separate', dominantSection: 'round' } });
    check(!fail.ok && fail.issues.length > 0, 'detects count/structure mismatch');

    console.log('dataset stats');
    const st = hitl.datasetStats(
      [{ rating: 'match', failureTags: ['legs'] }, { rating: 'wrong', failureTags: ['legs', 'joinery'] }],
      [{ object: 'x' }]
    );
    check(st.feedbackCount === 2 && st.exampleCount === 1 && st.byRating.match === 1 && st.tagCounts.legs === 2, 'stats aggregate');

    console.log(fails ? '\n' + fails + ' FAILED' : '\nhitl tests passed');
    process.exit(fails ? 1 : 0);
  })().catch(e => { console.error(e); process.exit(1); });
}
