/* Shared Anthropic proxy used by the local server and the Vercel /api/messages function.
   Only whitelisted fields are forwarded; the API key never leaves the server.
   Optional stream:true pipes Anthropic SSE so long generations keep the connection alive.
   Optional x-run-id (header or body.runId) is echoed and logged — never full prompts/images. */
const { normalizeRunId } = require('./telemetry');
const MAX_BODY = 25 * 1024 * 1024;
const hits = new Map();

function rate() { return +process.env.RATE_PER_MIN || 30; }
function key() { return process.env.ANTHROPIC_API_KEY; }
function upstream() { return (process.env.ANTHROPIC_BASE_URL || 'https://api.anthropic.com').replace(/\/$/, ''); }

function limited(ip) {
  const n = Date.now(), a = (hits.get(ip) || []).filter(t => n - t < 60000);
  a.push(n); hits.set(ip, a); return a.length > rate();
}

function parseBody(raw) {
  if (raw && typeof raw === 'object' && !Buffer.isBuffer(raw)) return raw;
  const text = Buffer.isBuffer(raw) ? raw.toString() : String(raw || '');
  return JSON.parse(text);
}

function runIdFrom(body, headerRunId) {
  return normalizeRunId(headerRunId)
    || normalizeRunId(body && body.runId)
    || normalizeRunId(body && body.metadata && body.metadata.runId)
    || '';
}

async function handleMessagesRequest({ body, ip, runId: headerRunId }) {
  const KEY = key();
  const t0 = Date.now();
  if (!KEY) return { status: 500, json: { error: { message: 'ANTHROPIC_API_KEY is not set on the server' } } };
  if (limited(ip || 'unknown')) return { status: 429, json: { error: { message: 'rate limit: ' + rate() + ' requests per minute' } } };
  let b;
  try { b = parseBody(body); } catch (e) { return { status: 400, json: { error: { message: 'invalid JSON' } } }; }
  const rid = runIdFrom(b, headerRunId);
  const wantStream = !!b.stream;
  const payload = { model: String(b.model || 'claude-sonnet-4-5'), max_tokens: Math.min(+b.max_tokens || 16000, 32000), messages: b.messages, stream: wantStream };
  if (b.system) payload.system = String(b.system);
  if (!Array.isArray(payload.messages)) return { status: 400, json: { error: { message: 'messages must be an array' } } };
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), +(process.env.UPSTREAM_TIMEOUT_MS || 280000));
  let result;
  try {
    const r = await fetch(upstream() + '/v1/messages', {
      method: 'POST',
      signal: ctrl.signal,
      headers: { 'content-type': 'application/json', 'x-api-key': KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify(payload)
    });
    if (wantStream && r.ok && r.body) {
      result = { status: r.status, stream: r.body, headers: { 'content-type': 'text/event-stream; charset=utf-8' } };
    } else {
      result = { status: r.status, text: await r.text() };
    }
  } catch (e) {
    if (e && e.name === 'AbortError') result = { status: 504, json: { error: { message: 'upstream timed out waiting for Anthropic — try fewer AI rounds or a shorter revise' } } };
    else result = { status: 502, json: { error: { message: 'upstream error: ' + e.message } } };
  } finally { clearTimeout(timer); }
  const headers = Object.assign({}, result.headers || {});
  if (rid) headers['x-run-id'] = rid;
  result.headers = headers;
  result.runId = rid || null;
  try {
    console.log(JSON.stringify({
      kind: 'proxy_messages',
      runId: rid || null,
      model: payload.model,
      ms: Date.now() - t0,
      status: result.status,
      stream: !!result.stream
    }));
  } catch (e) { /* ignore */ }
  return result;
}

async function pipeStream(res, result) {
  const headers = Object.assign({ 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' }, result.headers || {});
  res.writeHead(result.status, headers);
  const body = result.stream;
  if (body && typeof body.getReader === 'function') {
    const reader = body.getReader();
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        res.write(Buffer.from(value));
      }
    } finally { res.end(); }
    return;
  }
  if (body && typeof body.pipe === 'function') {
    body.pipe(res);
    return;
  }
  res.end();
}

module.exports = { handleMessagesRequest, pipeStream, limited, MAX_BODY, rate, runIdFrom };
