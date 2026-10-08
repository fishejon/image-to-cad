/* Tiny zero-dependency dev server: serves the app and proxies POST /api/messages to Anthropic so your API key stays on the server.
   ANTHROPIC_API_KEY=sk-ant-... node server/proxy.js      →  http://localhost:8787   (choose "Server proxy" in the AI tab) */
const http = require('http'), fs = require('fs'), path = require('path');
const { handleMessagesRequest, MAX_BODY } = require('./messages');
const PORT = +process.env.PORT || 8787, ROOT = path.join(__dirname, '..');
const ALLOW = new Set(['index.html', 'src', 'examples', 'dist', 'docs', 'favicon.ico']);
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.md': 'text/markdown; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon' };
const send = (res, code, body, type) => { res.writeHead(code, { 'content-type': type || 'application/json', 'x-content-type-options': 'nosniff', 'cache-control': 'no-store' }); res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body)); };
function serveStatic(req, res) {
  let p; try { p = decodeURIComponent(new URL(req.url, 'http://x').pathname); } catch (e) { return send(res, 400, { error: 'bad url' }); } if (p === '/') p = '/index.html';
  const f = path.normalize(path.join(ROOT, p)), rel = path.relative(ROOT, f); if (rel.startsWith('..') || path.isAbsolute(rel) || !ALLOW.has(rel.split(path.sep)[0])) return send(res, 404, { error: 'not found' });
  fs.stat(f, (e, st) => { if (e || !st.isFile()) return send(res, 404, { error: 'not found' }); send(res, 200, fs.readFileSync(f), MIME[path.extname(f)] || 'application/octet-stream'); });
}
const server = http.createServer((req, res) => {
  if (req.method === 'POST' && req.url === '/api/messages') {
    const chunks = []; let size = 0, dead = false;
    req.on('data', c => { size += c.length; if (size > MAX_BODY) { dead = true; send(res, 413, { error: { message: 'request too large' } }); req.destroy(); } else chunks.push(c); });
    req.on('end', async () => {
      if (dead) return;
      const result = await handleMessagesRequest({ body: Buffer.concat(chunks), ip: req.socket.remoteAddress });
      send(res, result.status, result.json || result.text);
    }); return;
  }
  if (req.method === 'GET' || req.method === 'HEAD') return serveStatic(req, res); send(res, 405, { error: 'method not allowed' });
});
if (require.main === module) server.listen(PORT, () => console.log('image-to-cad on http://localhost:' + PORT + (process.env.ANTHROPIC_API_KEY ? '' : '   (ANTHROPIC_API_KEY not set: the proxy provider will not work)')));
module.exports = server;
