/* Tiny zero-dependency dev server: serves the app and proxies POST /api/messages to Anthropic so your API key stays on the server.
   ANTHROPIC_API_KEY=sk-ant-... node server/proxy.js      →  http://localhost:8787   (choose "Local proxy" in the AI tab) */
const http = require('http'), fs = require('fs'), path = require('path');
const PORT = +process.env.PORT || 8787, KEY = process.env.ANTHROPIC_API_KEY, UP = (process.env.ANTHROPIC_BASE_URL || 'https://api.anthropic.com').replace(/\/$/, ''), ROOT = path.join(__dirname, '..');
const MAX_BODY = 25 * 1024 * 1024, ALLOW = new Set(['index.html', 'src', 'examples', 'dist', 'docs', 'favicon.ico']), RATE = +process.env.RATE_PER_MIN || 30;
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.md': 'text/markdown; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon' };
const hits = new Map(); const limited = ip => { const n = Date.now(), a = (hits.get(ip) || []).filter(t => n - t < 60000); a.push(n); hits.set(ip, a); return a.length > RATE; };
const send = (res, code, body, type) => { res.writeHead(code, { 'content-type': type || 'application/json', 'x-content-type-options': 'nosniff', 'cache-control': 'no-store' }); res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body)); };
function serveStatic(req, res) {
  let p; try { p = decodeURIComponent(new URL(req.url, 'http://x').pathname); } catch (e) { return send(res, 400, { error: 'bad url' }); } if (p === '/') p = '/index.html';
  const f = path.normalize(path.join(ROOT, p)), rel = path.relative(ROOT, f); if (rel.startsWith('..') || path.isAbsolute(rel) || !ALLOW.has(rel.split(path.sep)[0])) return send(res, 404, { error: 'not found' });
  fs.stat(f, (e, st) => { if (e || !st.isFile()) return send(res, 404, { error: 'not found' }); send(res, 200, fs.readFileSync(f), MIME[path.extname(f)] || 'application/octet-stream'); });
}
const server = http.createServer((req, res) => {
  if (req.method === 'POST' && req.url === '/api/messages') {
    if (!KEY) return send(res, 500, { error: { message: 'ANTHROPIC_API_KEY is not set on the server' } }); if (limited(req.socket.remoteAddress)) return send(res, 429, { error: { message: 'rate limit: ' + RATE + ' requests per minute' } });
    const chunks = []; let size = 0, dead = false;
    req.on('data', c => { size += c.length; if (size > MAX_BODY) { dead = true; send(res, 413, { error: { message: 'request too large' } }); req.destroy(); } else chunks.push(c); });
    req.on('end', async () => { if (dead) return; let b; try { b = JSON.parse(Buffer.concat(chunks).toString()); } catch (e) { return send(res, 400, { error: { message: 'invalid JSON' } }); }
      const body = { model: String(b.model || 'claude-sonnet-5-5'), max_tokens: Math.min(+b.max_tokens || 16000, 32000), messages: b.messages }; if (b.system) body.system = String(b.system); if (!Array.isArray(body.messages)) return send(res, 400, { error: { message: 'messages must be an array' } });
      try { const r = await fetch(UP + '/v1/messages', { method: 'POST', headers: { 'content-type': 'application/json', 'x-api-key': KEY, 'anthropic-version': '2023-06-01' }, body: JSON.stringify(body) }); send(res, r.status, await r.text()); }
      catch (e) { send(res, 502, { error: { message: 'upstream error: ' + e.message } }); } }); return;
  }
  if (req.method === 'GET' || req.method === 'HEAD') return serveStatic(req, res); send(res, 405, { error: 'method not allowed' });
});
if (require.main === module) server.listen(PORT, () => console.log('image-to-cad on http://localhost:' + PORT + (KEY ? '' : '   (ANTHROPIC_API_KEY not set: the proxy provider will not work)')));
module.exports = server;
