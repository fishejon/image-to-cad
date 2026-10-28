/* Dev server: static app + Anthropic proxy + telemetry / HITL APIs.
   ANTHROPIC_API_KEY=sk-ant-... node server/proxy.js      →  http://localhost:8787 */
const http = require('http'), fs = require('fs'), path = require('path');
const { handleMessagesRequest, pipeStream, MAX_BODY } = require('./messages');
const { handleEventsRequest, handleFeedbackRequest } = require('./telemetry');
const db = require('./db');
const storage = require('./storage');
const hitl = require('./hitl');
const PORT = +process.env.PORT || 8787, ROOT = path.join(__dirname, '..');
const ALLOW = new Set(['index.html', 'src', 'examples', 'dist', 'docs', 'evals', 'favicon.ico']);
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
      posthogHost: posthogKey ? posthogHost : null,
      hasDatabase: db.enabled(),
      hasObjectStorage: storage.enabled()
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
  if (req.method === 'POST' && req.url === '/api/examples') {
    readBody(req, res, 256 * 1024).then(async buf => {
      if (!buf) return;
      let body; try { body = JSON.parse(buf.toString()); } catch (e) { return send(res, 400, { error: { message: 'invalid JSON' } }); }
      const v = hitl.validateExample(body);
      if (!v.ok) return send(res, 400, { error: { message: v.error } });
      if (!db.enabled()) return send(res, 202, { ok: true, persisted: false, runId: v.row.runId, reason: 'DATABASE_URL unset' });
      try {
        const r = await hitl.insertExample(v.row);
        const id = r && r.rows && r.rows[0] && r.rows[0].id;
        send(res, 202, { ok: true, persisted: true, id, runId: v.row.runId });
      } catch (e) { send(res, 500, { error: { message: e.message || 'persist failed' } }); }
    });
    return;
  }
  if (req.method === 'POST' && req.url === '/api/image') {
    readBody(req, res, MAX_BODY).then(async buf => {
      if (!buf) return;
      let body; try { body = JSON.parse(buf.toString()); } catch (e) { return send(res, 400, { error: { message: 'invalid JSON' } }); }
      const runId = String(body.runId || '').trim();
      if (!runId) return send(res, 400, { error: { message: 'runId required' } });
      if (!body.consent) return send(res, 400, { error: { message: 'consent must be true to upload images' } });
      try {
        const up = await storage.uploadRunImage({ runId, consent: true, dataUrl: body.dataUrl || body.image || null });
        if (!up.ok) return send(res, 400, { error: { message: up.error || 'upload failed' } });
        if (db.enabled()) await hitl.updateRunImage(runId, { imageHash: up.imageHash, imageUrl: up.imageUrl, imageConsent: true });
        send(res, 202, { ok: true, runId, imageHash: up.imageHash, imageUrl: up.imageUrl || null, uploaded: !up.skippedUpload });
      } catch (e) { send(res, 500, { error: { message: e.message || 'upload failed' } }); }
    });
    return;
  }
  if (req.method === 'GET' && (req.url === '/api/dataset' || req.url.startsWith('/api/dataset?'))) {
    if (!db.enabled()) return send(res, 503, { error: { message: 'DATABASE_URL not set' } });
    const u = new URL(req.url, 'http://x');
    hitl.buildServerDataset({ limit: u.searchParams.get('limit') }).then(out => {
      if (!out || !out.ok) return send(res, 500, { error: { message: (out && out.error) || 'export failed' } });
      if ((u.searchParams.get('format') || '').toLowerCase() === 'jsonl') {
        return send(res, 200, out.jsonl.feedback + out.jsonl.examples, 'application/x-ndjson; charset=utf-8');
      }
      send(res, 200, out.pack);
    }).catch(e => send(res, 500, { error: { message: e.message || 'export failed' } }));
    return;
  }
  if (req.method === 'GET' || req.method === 'HEAD') return serveStatic(req, res); send(res, 405, { error: 'method not allowed' });
});
if (require.main === module) server.listen(PORT, () => console.log('image-to-cad on http://localhost:' + PORT + (process.env.ANTHROPIC_API_KEY ? '' : '   (ANTHROPIC_API_KEY not set: the proxy provider will not work)')));
module.exports = server;
