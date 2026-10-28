/* Telemetry validation + ring buffer:  node tests/telemetry.js */
const T = require('../server/telemetry');
let fails = 0;
const check = (c, m) => { console.log((c ? '  ✓ ' : '  ✗ ') + m); if (!c) fails++; };

T.resetForTests();

console.log('validateEvent');
{
  const bad = T.validateEvent({});
  check(!bad.ok && /type/.test(bad.error), 'rejects missing type');
  const badId = T.validateEvent({ type: 'run_started' });
  check(!badId.ok && /runId/.test(badId.error), 'run_started requires runId');
  const ok = T.validateEvent({
    type: 'run_started', runId: 'r_abc-1', task: 'design', inputMode: 'drawing',
    quality: 'balanced', model: 'claude-haiku', staged: true, visual: false
  });
  check(ok.ok && ok.row.runId === 'r_abc-1' && ok.row.inputMode === 'drawing' && ok.row.domain === 'furniture', 'accepts run_started');
  const fin = T.validateEvent({
    type: 'run_finished', runId: 'r_abc-1', geometryOk: true, rounds: 2,
    likenessPenalty: 10, unlabeledContacts: 1, durationMs: 1234
  });
  check(fin.ok && fin.row.geometryOk === true && fin.row.unlabeledContacts === 1, 'accepts run_finished');
  const ui = T.validateEvent({ type: 'ui', name: 'guide_opened', runId: 'r1', props: { page: 2 } });
  check(ui.ok && ui.row.name === 'guide_opened', 'accepts ui event');
  check(!T.normalizeRunId('bad id!'), 'rejects unsafe runId chars');
  check(T.normalizeRunId('r:ok_1.2') === 'r:ok_1.2', 'allows safe runId charset');
}

console.log('validateFeedback');
{
  check(!T.validateFeedback({ rating: 'maybe' }).ok, 'rejects bad rating');
  const ok = T.validateFeedback({
    runId: 'r1', rating: 'close', failureTags: ['legs', 'joinery'], note: 'off',
    object: 'stool', model: 'm', quality: 'fast'
  });
  check(ok.ok && ok.row.rating === 'close' && ok.row.failureTags.length === 2, 'accepts match/close/wrong feedback');
  check(T.validateFeedback({ rating: 'match', runId: 'r2' }).ok, 'match ok without tags');
}

console.log('append + handle');
(async () => {
  T.resetForTests();
  const e = await T.handleEventsRequest({
    body: JSON.stringify({ type: 'run_started', runId: 'r99', task: 'revise' })
  });
  check(e.status === 202 && e.json.ok === true && e.json.runId === 'r99', 'POST events → 202');
  const bad = await T.handleEventsRequest({ body: '{nope' });
  check(bad.status === 400, 'invalid JSON → 400');
  const f = await T.handleFeedbackRequest({
    body: { rating: 'wrong', runId: 'r99', failureTags: ['proportions'], note: 'x' }
  });
  check(f.status === 202 && f.json.ok === true, 'POST feedback → 202');
  const snap = T.snapshot();
  check(snap.events.length === 1 && snap.feedback.length === 1, 'ring buffer keeps rows');
  console.log(fails ? '\n' + fails + ' FAILED' : '\ntelemetry tests passed');
  process.exit(fails ? 1 : 0);
})();
