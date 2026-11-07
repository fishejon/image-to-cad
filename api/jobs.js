/* Vercel: /api/jobs — job starter / status relay for the photo→cutlist worker (Phase 2).
   Does NOT run build123d. Set WORKER_JOBS_URL to proxy to the Docker/local worker. */
async function readBody(req) {
  if (req.body != null) {
    return typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
  }
  const chunks = [];
  for await (const c of req) chunks.push(c);
  return Buffer.concat(chunks).toString('utf8');
}

module.exports = async (req, res) => {
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
    const suffix = incoming.pathname.replace(/^\/api\/jobs/, '/jobs') || '/jobs';
    const target = base + suffix + incoming.search;
    const init = { method: req.method, headers: { 'content-type': 'application/json' } };
    if (req.method === 'POST') init.body = await readBody(req);
    const r = await fetch(target, init);
    const text = await r.text();
    res.status(r.status);
    res.setHeader('content-type', r.headers.get('content-type') || 'application/json');
    return res.send(text);
  } catch (e) {
    return res.status(502).json({ error: { message: 'worker relay failed: ' + (e && e.message) } });
  }
};
