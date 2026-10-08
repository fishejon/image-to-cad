/* Proxy tests against a local fake upstream:  node tests/proxy.js */
const http = require('http'); let fails = 0; const check = (c, m) => { console.log((c ? '  ✓ ' : '  ✗ ') + m); if (!c) fails++; };
const up = http.createServer((req, res) => { const ch = []; req.on('data', c => ch.push(c)); req.on('end', () => { up.last = { headers: req.headers, body: JSON.parse(Buffer.concat(ch).toString()), url: req.url }; res.writeHead(200, { 'content-type': 'application/json' }); res.end(JSON.stringify({ content: [{ type: 'text', text: '{"ok":true}' }] })); }); });
up.listen(0, async () => {
  process.env.ANTHROPIC_API_KEY = 'sk-ant-SERVERSIDE'; process.env.ANTHROPIC_BASE_URL = 'http://127.0.0.1:' + up.address().port; process.env.RATE_PER_MIN = '6'; const app = require('../server/proxy.js'); await new Promise(r => app.listen(0, r));
  const base = 'http://127.0.0.1:' + app.address().port, post = (b, raw) => fetch(base + '/api/messages', { method: 'POST', headers: { 'content-type': 'application/json' }, body: raw || JSON.stringify(b) });
  let r = await post({ model: 'm', max_tokens: 999999, messages: [{ role: 'user', content: 'hi' }], evil: 'x', tools: [1] }); let j = await r.json();
  check(r.status === 200 && j.content[0].text === '{"ok":true}', 'forwards a request and returns the answer'); check(up.last.headers['x-api-key'] === 'sk-ant-SERVERSIDE' && up.last.url === '/v1/messages', 'server-side key is attached upstream'); check(up.last.body.max_tokens === 32000 && !('evil' in up.last.body) && !('tools' in up.last.body), 'only whitelisted fields are forwarded and max_tokens is capped');
  check(!JSON.stringify([...r.headers]).includes('SERVERSIDE') && !JSON.stringify(j).includes('SERVERSIDE'), 'the key never reaches the browser');
  r = await post(null, '{bad'); check(r.status === 400, 'invalid JSON → 400'); r = await post({ model: 'm' }); check(r.status === 400, 'missing messages → 400');
  r = await fetch(base + '/'); check(r.status === 200 && /Image → CAD/.test(await r.text()), 'serves index.html'); r = await fetch(base + '/examples/stool.json'); check(r.status === 200 && (await r.json()).name === 'Three-leg stool', 'serves examples');
  for (const p of ['/package.json', '/server/proxy.js', '/tests/run.js', '/.git/config', '/%2e%2e/%2e%2e/etc/passwd', '/..%2fpackage.json', '/src/../package.json', '/node_modules/three/package.json']) { r = await fetch(base + p); check(r.status === 404 || r.status === 400, 'blocks ' + p + ' (' + r.status + ')'); }
  r = await fetch(base + '/api/messages', { method: 'PUT' }); check(r.status === 405, 'other methods rejected');
  let last; for (let i = 0; i < 8; i++) last = await post({ model: 'm', messages: [{ role: 'user', content: 'x' }] }); check(last.status === 429, 'rate limit kicks in');
  console.log(fails ? '\n' + fails + ' FAILED' : '\nproxy tests passed'); app.close(); up.close(); process.exit(fails ? 1 : 0);
});
