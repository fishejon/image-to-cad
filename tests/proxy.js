/* Proxy tests against a local fake upstream:  node tests/proxy.js */
const http = require('http'); let fails = 0; const check = (c, m) => { console.log((c ? '  ✓ ' : '  ✗ ') + m); if (!c) fails++; };
const up = http.createServer((req, res) => {
  const ch = [];
  req.on('data', c => ch.push(c));
  req.on('end', () => {
    const body = JSON.parse(Buffer.concat(ch).toString());
    up.last = { headers: req.headers, body, url: req.url };
    if (body.stream) {
      res.writeHead(200, { 'content-type': 'text/event-stream' });
      res.write('event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"type":"text_delta","text":"{\\"ok\\":true}"}}\n\n');
      res.write('event: message_stop\ndata: {"type":"message_stop"}\n\n');
      return res.end();
    }
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ content: [{ type: 'text', text: '{"ok":true}' }] }));
  });
});
up.listen(0, async () => {
  process.env.ANTHROPIC_API_KEY = 'sk-ant-SERVERSIDE'; process.env.ANTHROPIC_BASE_URL = 'http://127.0.0.1:' + up.address().port; process.env.RATE_PER_MIN = '8'; const app = require('../server/proxy.js'); await new Promise(r => app.listen(0, r));
  const base = 'http://127.0.0.1:' + app.address().port;
  const post = (b, raw, extraHeaders) => fetch(base + '/api/messages', {
    method: 'POST',
    headers: Object.assign({ 'content-type': 'application/json' }, extraHeaders || {}),
    body: raw || JSON.stringify(b)
  });
  let r = await post({ model: 'm', max_tokens: 999999, messages: [{ role: 'user', content: 'hi' }], evil: 'x', tools: [1] }); let j = await r.json();
  check(r.status === 200 && j.content[0].text === '{"ok":true}', 'forwards a request and returns the answer'); check(up.last.headers['x-api-key'] === 'sk-ant-SERVERSIDE' && up.last.url === '/v1/messages', 'server-side key is attached upstream'); check(up.last.body.max_tokens === 32000 && !('evil' in up.last.body) && !('tools' in up.last.body), 'only whitelisted fields are forwarded and max_tokens is capped');
  check(!JSON.stringify([...r.headers]).includes('SERVERSIDE') && !JSON.stringify(j).includes('SERVERSIDE'), 'the key never reaches the browser');
  r = await post({ model: 'm', messages: [{ role: 'user', content: 'hi' }], runId: 'r_body' });
  check(r.status === 200 && r.headers.get('x-run-id') === 'r_body', 'echoes runId from body as x-run-id');
  r = await post({ model: 'm', messages: [{ role: 'user', content: 'hi' }] }, null, { 'x-run-id': 'r_hdr' });
  check(r.status === 200 && r.headers.get('x-run-id') === 'r_hdr', 'echoes x-run-id request header');
  r = await post({ model: 'm', stream: true, messages: [{ role: 'user', content: 'hi' }], runId: 'r_stream' });
  const ct = r.headers.get('content-type') || '';
  const streamText = await r.text();
  check(r.status === 200 && /event-stream/i.test(ct) && up.last.body.stream === true, 'streaming request is forwarded');
  check(r.headers.get('x-run-id') === 'r_stream', 'streaming response echoes x-run-id');
  check(/text_delta/.test(streamText) && /\\"ok\\":true|{"ok":true}/.test(streamText), 'SSE body is piped through');
  r = await post(null, '{bad'); check(r.status === 400, 'invalid JSON → 400'); r = await post({ model: 'm' }); check(r.status === 400, 'missing messages → 400');
  r = await fetch(base + '/'); check(r.status === 200 && /Image → CAD/.test(await r.text()), 'serves index.html'); r = await fetch(base + '/examples/stool.json'); check(r.status === 200 && (await r.json()).name === 'Three-leg stool', 'serves examples');
  r = await fetch(base + '/api/status'); const st = await r.json(); check(r.status === 200 && st.hasKey === true && !JSON.stringify(st).includes('SERVERSIDE'), 'status reports the key is present without leaking it');
  check(st.posthogKey == null || typeof st.posthogKey === 'string', 'status includes optional posthogKey field');
  check(st.hasDatabase === false && st.hasObjectStorage === false, 'status reports DB/storage off without env');
  r = await fetch(base + '/api/examples', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ runId: 'r_ex', object: 'stool', inventory: { object: 'stool' } })
  });
  check(r.status === 202 && (await r.json()).persisted === false, 'POST /api/examples accepts without DATABASE_URL');
  r = await fetch(base + '/api/dataset');
  check(r.status === 503, 'GET /api/dataset → 503 without DATABASE_URL');
  r = await fetch(base + '/api/image', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ runId: 'r_img', consent: false })
  });
  check(r.status === 400, 'POST /api/image without consent → 400');
  r = await fetch(base + '/api/events', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ type: 'run_started', runId: 'r_evt', task: 'design', model: 'm' })
  });
  check(r.status === 202 && (await r.json()).ok === true, 'POST /api/events → 202');
  r = await fetch(base + '/api/feedback', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ rating: 'match', runId: 'r_evt', note: 'ok' })
  });
  check(r.status === 202 && (await r.json()).ok === true, 'POST /api/feedback → 202');
  r = await fetch(base + '/api/events', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ type: 'run_started' })
  });
  check(r.status === 400, 'events without runId → 400');
  for (const p of ['/package.json', '/server/proxy.js', '/tests/run.js', '/.git/config', '/%2e%2e/%2e%2e/etc/passwd', '/..%2fpackage.json', '/src/../package.json', '/node_modules/three/package.json']) { r = await fetch(base + p); check(r.status === 404 || r.status === 400, 'blocks ' + p + ' (' + r.status + ')'); }
  r = await fetch(base + '/api/messages', { method: 'PUT' }); check(r.status === 405, 'other methods rejected');
  let last; for (let i = 0; i < 10; i++) last = await post({ model: 'm', messages: [{ role: 'user', content: 'x' }] }); check(last.status === 429, 'rate limit kicks in');
  console.log(fails ? '\n' + fails + ' FAILED' : '\nproxy tests passed'); app.close(); up.close(); process.exit(fails ? 1 : 0);
});
