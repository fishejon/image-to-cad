/* Langfuse helper + OTEL wiring tests:  node tests/langfuse.js */
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
  check(L.generationName('inventory') === 'generate-inventory', 'stable generation names');
  check(L.maskData({ data: { source: { data: 'x'.repeat(100) } } }).source.data === '[omitted]', 'mask drops long data fields');
}

console.log('meta + usage');
{
  const m = L.metaFrom({ metadata: { task: 'inventory', quality: 'fast' } }, { 'x-domain': 'manual' });
  check(m.task === 'inventory' && m.quality === 'fast' && m.domain === 'manual', 'headers/body metadata merge');
  const u = L.parseUsage(JSON.stringify({ usage: { input_tokens: 10, output_tokens: 5 } }));
  check(u && u.input === 10 && u.output === 5 && u.total === 15, 'parses Anthropic usage');
}

console.log('trace no-op / otel path');
(async () => {
  L.resetForTests();
  delete process.env.LANGFUSE_PUBLIC_KEY;
  delete process.env.LANGFUSE_SECRET_KEY;
  const skip = await L.traceMessages({ runId: 'r1', model: 'm', status: 200 });
  check(skip && skip.skipped, 'no-ops without keys');

  process.env.LANGFUSE_PUBLIC_KEY = 'pk-lf-test';
  process.env.LANGFUSE_SECRET_KEY = 'sk-lf-test';
  process.env.LANGFUSE_BASE_URL = 'https://cloud.langfuse.com';
  L.resetForTests();
  const r = await L.traceMessages({
    runId: 'r_test',
    metadata: { task: 'design', quality: 'balanced', domain: 'furniture' },
    model: 'claude-test',
    modelParameters: { max_tokens: 100, stream: false },
    input: { messages: L.sanitizeMessages([{ role: 'user', content: 'hi' }]) },
    responseText: JSON.stringify({ content: [{ type: 'text', text: '{"ok":true}' }], usage: { input_tokens: 1, output_tokens: 2 } }),
    status: 200
  });
  check(r && r.ok === true, 'OTEL traceMessages completes with keys (flush may 401 to cloud)');
  check(L.ensureOtel() === true, 'otel provider registered');

  delete process.env.LANGFUSE_PUBLIC_KEY;
  delete process.env.LANGFUSE_SECRET_KEY;
  delete process.env.LANGFUSE_BASE_URL;
  L.resetForTests();
  console.log(fails ? '\n' + fails + ' FAILED' : '\nlangfuse tests passed');
  process.exit(fails ? 1 : 0);
})();
