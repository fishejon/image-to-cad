/* Shared Vercel ↔ worker jobs relay (Phase 2+).
   Env: WORKER_JOBS_URL (required), WORKER_JOBS_TOKEN (Bearer to worker when set). */
async function readBody(req) {
  if (req.body != null) {
    return typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
  }
  const chunks = [];
  for await (const c of req) chunks.push(c);
  return Buffer.concat(chunks).toString('utf8');
}

function workerHeaders() {
  const headers = { 'content-type': 'application/json' };
  const token = (process.env.WORKER_JOBS_TOKEN || process.env.JOBS_TOKEN || '').trim();
  if (token) headers.authorization = 'Bearer ' + token;
  return headers;
}

async function relayJobs(req, res, suffix) {
  res.setHeader('cache-control', 'no-store');
  res.setHeader('x-content-type-options', 'nosniff');
  res.setHeader('access-control-allow-origin', '*');
  if (req.method === 'OPTIONS') {
    res.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS');
    res.setHeader('access-control-allow-headers', 'content-type, authorization, x-jobs-token');
    return res.status(204).end();
  }
  const base = (process.env.WORKER_JOBS_URL || '').replace(/\/$/, '');
  if (!base) {
    return res.status(503).json({
      error: {
        message: 'WORKER_JOBS_URL unset — deploy the worker (docs/deploy-worker.md) or run locally: python -m furniture_cad jobs --port 8787',
        vercel_role: 'job starter / progress relay only'
      }
    });
  }
  const token = (process.env.WORKER_JOBS_TOKEN || process.env.JOBS_TOKEN || '').trim();
  if (!token) {
    return res.status(503).json({
      error: {
        message: 'WORKER_JOBS_TOKEN unset on Vercel — set it to the same secret as the Fly worker, then redeploy',
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
    const init = { method: req.method, headers: workerHeaders() };
    if (req.method === 'POST') init.body = await readBody(req);
    const r = await fetch(target, init);
    if (r.status === 401 || r.status === 403) {
      return res.status(401).json({
        error: {
          message: 'Worker rejected the token — WORKER_JOBS_TOKEN on Vercel must match Fly WORKER_JOBS_TOKEN exactly'
        }
      });
    }
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

module.exports = { relayJobs, readBody, workerHeaders };
