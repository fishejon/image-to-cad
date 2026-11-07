/* Shared Vercel ↔ worker jobs relay (Phase 2+). */
async function readBody(req) {
  if (req.body != null) {
    return typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
  }
  const chunks = [];
  for await (const c of req) chunks.push(c);
  return Buffer.concat(chunks).toString('utf8');
}

async function relayJobs(req, res, suffix) {
  res.setHeader('cache-control', 'no-store');
  res.setHeader('x-content-type-options', 'nosniff');
  res.setHeader('access-control-allow-origin', '*');
  if (req.method === 'OPTIONS') {
    res.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS');
    res.setHeader('access-control-allow-headers', 'content-type');
    return res.status(204).end();
  }
  const base = (process.env.WORKER_JOBS_URL || '').replace(/\/$/, '');
  if (!base) {
    return res.status(503).json({
      error: {
        message: 'WORKER_JOBS_URL unset — start worker: python -m furniture_cad jobs --port 8787',
        vercel_role: 'job starter / progress relay only'
      }
    });
  }
  try {
    const incoming = new URL(req.url || '/api/jobs', 'http://local');
    const pathSuffix = suffix != null
      ? ('/jobs' + (suffix ? '/' + String(suffix).replace(/^\/+/, '') : ''))
      : (incoming.pathname.replace(/^\/api\/jobs/, '/jobs') || '/jobs');
    const target = base + pathSuffix + incoming.search;
    const init = { method: req.method, headers: { 'content-type': 'application/json' } };
    if (req.method === 'POST') init.body = await readBody(req);
    const r = await fetch(target, init);
    const ctype = r.headers.get('content-type') || '';
    res.status(r.status);
    if (ctype.includes('application/json') || ctype.includes('text/')) {
      res.setHeader('content-type', ctype || 'application/json');
      return res.send(await r.text());
    }
    const buf = Buffer.from(await r.arrayBuffer());
    res.setHeader('content-type', ctype || 'application/octet-stream');
    const cd = r.headers.get('content-disposition');
    if (cd) res.setHeader('content-disposition', cd);
    return res.send(buf);
  } catch (e) {
    return res.status(502).json({ error: { message: 'worker relay failed: ' + (e && e.message) } });
  }
}

module.exports = { relayJobs, readBody };
