/* Tiny zero-dependency dev server: serves the app and proxies POST /api/messages to Anthropic so your API key stays on the server.
   Also accepts POST /api/events and /api/feedback (Phase 1 telemetry).
   ANTHROPIC_API_KEY=sk-ant-... node server/proxy.js      →  http://localhost:8787   (choose "Server proxy" in the AI tab) */
const http = require('http'), fs = require('fs'), path = require('path');
const { handleMessagesRequest, pipeStream, MAX_BODY } = require('./messages');
const { handleEventsRequest, handleFeedbackRequest } = require('./telemetry');
const PORT = +process.env.PORT || 8787, ROOT = path.join(__dirname, '..');
const ALLOW = new Set(['index.html', 'src', 'examples', 'dist', 'docs', 'favicon.ico']);
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.md': 'text/markdown; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon' };
const send = (res, code, body, type, extraHeaders) => {
  res.writeHead(code, Object.assign({
    'content-type': type || 'application/json',
    'x-content-type-options': 'nosniff',
    'cache-control': 'no-store'
  }, extraHeaders || {}));
  res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body));
};
function readBody(req, res, max) {
  return new Promise(resolve => {
    const chunks = []; let size = 0, dead = false;
    req.on('data', c => {
      size += c.length;
      if (size > max) { dead = true; send(res, 413, { error: { message: 'request too large' } }); req.destroy(); }
      else chunks.push(c);
    });
    req.on('end', () => { if (!dead) resolve(Buffer.concat(chunks)); });
  });
}
function serveStatic(req, res) {
  let p; try { p = decodeURIComponent(new URL(req.url, 'http://x').pathname); } catch (e) { return send(res, 400, { error: 'bad url' }); } if (p === '/') p = '/index.html';
  const f = path.normalize(path.join(ROOT, p)), rel = path.relative(ROOT, f); if (rel.startsWith('..') || path.isAbsolute(rel) || !ALLOW.has(rel.split(path.sep)[0])) return send(res, 404, { error: 'not found' });
  fs.stat(f, (e, st) => { if (e || !st.isFile()) return send(res, 404, { error: 'not found' }); send(res, 200, fs.readFileSync(f), MIME[path.extname(f)] || 'application/octet-stream'); });
}
const server = http.createServer((req, res) => {
  if ((req.method === 'GET' || req.method === 'HEAD') && (req.url === '/api/status' || req.url.startsWith('/api/status?'))) {
    const posthogKey = process.env.POSTHOG_KEY || process.env.NEXT_PUBLIC_POSTHOG_KEY || '';
    const posthogHost = process.env.POSTHOG_HOST || process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://us.i.posthog.com';
    return send(res, 200, {
      ok: true,
      hasKey: !!process.env.ANTHROPIC_API_KEY,
      posthogKey: posthogKey || null,
      posthogHost: posthogKey ? posthogHost : null
    });
  }
  if (req.method === 'POST' && req.url === '/api/messages') {
    readBody(req, res, MAX_BODY).then(async buf => {
      if (!buf) return;
      const result = await handleMessagesRequest({
        body: buf,
        ip: req.socket.remoteAddress,
        runId: req.headers['x-run-id'],
        headers: {
          'x-task': req.headers['x-task'],
          'x-quality': req.headers['x-quality'],
          'x-domain': req.headers['x-domain']
        }
      });
      if (result.stream) return pipeStream(res, result);
      const type = result.json ? 'application/json' : 'application/json';
      send(res, result.status, result.json || result.text, type, result.headers);
    });
    return;
  }
  if (req.method === 'POST' && (req.url === '/api/events' || req.url === '/api/feedback')) {
    readBody(req, res, 256 * 1024).then(async buf => {
      if (!buf) return;
      const result = req.url === '/api/events'
        ? await handleEventsRequest({ body: buf })
        : await handleFeedbackRequest({ body: buf });
      send(res, result.status, result.json);
    });
    return;
  }
  if (req.method === 'GET' || req.method === 'HEAD') return serveStatic(req, res); send(res, 405, { error: 'method not allowed' });
});
if (require.main === module) server.listen(PORT, () => console.log('image-to-cad on http://localhost:' + PORT + (process.env.ANTHROPIC_API_KEY ? '' : '   (ANTHROPIC_API_KEY not set: the proxy provider will not work)')));
module.exports = server;
