/* Shared Anthropic proxy used by the local server and the Vercel /api/messages function.
   Only whitelisted fields are forwarded; the API key never leaves the server. */
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

async function handleMessagesRequest({ body, ip }) {
  const KEY = key();
  if (!KEY) return { status: 500, json: { error: { message: 'ANTHROPIC_API_KEY is not set on the server' } } };
  if (limited(ip || 'unknown')) return { status: 429, json: { error: { message: 'rate limit: ' + rate() + ' requests per minute' } } };
  let b;
  try { b = parseBody(body); } catch (e) { return { status: 400, json: { error: { message: 'invalid JSON' } } }; }
  const payload = { model: String(b.model || 'claude-sonnet-4-5'), max_tokens: Math.min(+b.max_tokens || 16000, 32000), messages: b.messages };
  if (b.system) payload.system = String(b.system);
  if (!Array.isArray(payload.messages)) return { status: 400, json: { error: { message: 'messages must be an array' } } };
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), +(process.env.UPSTREAM_TIMEOUT_MS || 280000));
  try {
    const r = await fetch(upstream() + '/v1/messages', {
      method: 'POST',
      signal: ctrl.signal,
      headers: { 'content-type': 'application/json', 'x-api-key': KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify(payload)
    });
    return { status: r.status, text: await r.text() };
  } catch (e) {
    if (e && e.name === 'AbortError') return { status: 504, json: { error: { message: 'upstream timed out waiting for Anthropic — try fewer AI rounds or a shorter revise' } } };
    return { status: 502, json: { error: { message: 'upstream error: ' + e.message } } };
  } finally { clearTimeout(timer); }
}

module.exports = { handleMessagesRequest, limited, MAX_BODY, rate };
