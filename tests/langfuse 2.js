/* Langfuse helper tests:  node tests/langfuse.js */
const L = require('../server/langfuse');
let fails = 0;
const check = (c, m) => { console.log((c ? '  ✓ ' : '  ✗ ') + m); if (!c) fails++; };

console.log('sanitize');
{
  const msgs = L.sanitizeMessages([{
    role: 'user',
    content: [
      { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: 'AAAA' } },
      { type: 'text', text: 'design a stool' }
    ]
  }]);
  check(msgs[0].content[0].omitted === true && !JSON.stringify(msgs).includes('AAAA'), 'strips image base64');
  check(msgs[0].content[1].text === 'design a stool', 'keeps text');
}

console.log('meta + usage');
{
  const m = L.metaFrom({ metadata: { task: 'inventory', quality: 'fast' } }, { 'x-domain': 'manual' });
  check(m.task === 'inventory' && m.quality === 'fast' && m.domain === 'manual', 'headers/body metadata merge');
  const u = L.parseUsage(JSON.stringify({ usage: { input_tokens: 10, output_tokens: 5 } }));
  check(u && u.input === 10 && u.output === 5 && u.total === 15, 'parses Anthropic usage');
}

console.log('trace no-op / ingest mock');
(async () => {
  delete process.env.LANGFUSE_PUBLIC_KEY;
  delete process.env.LANGFUSE_SECRET_KEY;
  const skip = await L.traceMessages({ runId: 'r1', model: 'm', status: 200 });
  check(skip && skip.skipped, 'no-ops without keys');

  process.env.LANGFUSE_PUBLIC_KEY = 'pk-lf-test';
  process.env.LANGFUSE_SECRET_KEY = 'sk-lf-test';
  process.env.LANGFUSE_BASE_URL = 'http://127.0.0.1:9'; // closed port → catch path
  const realFetch = global.fetch;
  let saw = null;
  global.fetch = async (url, opts) => {
    saw = { url: String(url), body: JSON.parse(opts.body), auth: opts.headers.authorization };
    return { ok: true, status: 207 };
  };
  const r = await L.traceMessages({
    runId: 'r_test',
    metadata: { task: 'design', quality: 'balanced', domain: 'furniture' },
    model: 'claude-test',
    input: { messages: L.sanitizeMessages([{ role: 'user', content: 'hi' }]) },
    responseText: JSON.stringify({ content: [{ type: 'text', text: '{"ok":true}' }], usage: { input_tokens: 1, output_tokens: 2 } }),
    status: 200,
    startedAt: Date.now() - 50,
    endedAt: Date.now()
  });
  global.fetch = realFetch;
  check(r && r.ok, 'ingest returns ok');
  check(saw && /\/api\/public\/ingestion$/.test(saw.url), 'posts to ingestion endpoint');
  check(saw.body.batch.length === 2, 'sends trace + generation');
  check(saw.body.batch[0].body.sessionId === 'r_test', 'sessionId = runId');
  check(saw.body.batch[1].body.model === 'claude-test' && saw.body.batch[1].body.usage.total === 3, 'generation has model + usage');
  check(/^Basic /.test(saw.auth), 'basic auth header set');

  delete process.env.LANGFUSE_PUBLIC_KEY;
  delete process.env.LANGFUSE_SECRET_KEY;
  delete process.env.LANGFUSE_BASE_URL;
  console.log(fails ? '\n' + fails + ' FAILED' : '\nlangfuse tests passed');
  process.exit(fails ? 1 : 0);
})();
