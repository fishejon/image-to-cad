/* Optional Langfuse tracing for the Anthropic proxy. No-ops without keys.
   Never throws into the request path. Strips image base64 from logged prompts. */
const crypto = require('crypto');

const MAX_TEXT = 40000;

function enabled() {
  return !!(process.env.LANGFUSE_PUBLIC_KEY && process.env.LANGFUSE_SECRET_KEY);
}

function baseUrl() {
  return (process.env.LANGFUSE_BASE_URL || 'https://cloud.langfuse.com').replace(/\/$/, '');
}

function uid() {
  return crypto.randomUUID ? crypto.randomUUID() : ('id' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10));
}

function clip(s, n) {
  const t = String(s == null ? '' : s);
  const lim = n || MAX_TEXT;
  return t.length > lim ? t.slice(0, lim) + '…[truncated]' : t;
}

/** Replace image blocks with placeholders so traces stay small and non-sensitive. */
function sanitizeContent(content) {
  if (typeof content === 'string') return clip(content);
  if (!Array.isArray(content)) return content;
  return content.map(block => {
    if (!block || typeof block !== 'object') return block;
    if (block.type === 'image' || (block.source && block.source.type === 'base64')) {
      const mt = (block.source && block.source.media_type) || block.media_type || 'image';
      return { type: 'image', omitted: true, media_type: mt };
    }
    if (block.type === 'text' && block.text != null) return { type: 'text', text: clip(block.text) };
    return block;
  });
}

function sanitizeMessages(messages) {
  if (!Array.isArray(messages)) return [];
  return messages.map(m => ({
    role: m && m.role,
    content: sanitizeContent(m && m.content)
  }));
}

function metaFrom(body, headers) {
  const h = headers || {};
  const m = (body && body.metadata) || {};
  const pick = (a, b, c) => {
    const v = a != null && a !== '' ? a : (b != null && b !== '' ? b : c);
    return v == null || v === '' ? null : String(v).slice(0, 128);
  };
  return {
    task: pick(h['x-task'], m.task, body && body.task),
    quality: pick(h['x-quality'], m.quality, body && body.quality),
    domain: pick(h['x-domain'], m.domain, body && body.domain) || 'furniture'
  };
}

function parseUsage(text) {
  if (!text || typeof text !== 'string') return null;
  try {
    const j = JSON.parse(text);
    const u = j.usage || {};
    const input = u.input_tokens != null ? +u.input_tokens : (u.prompt_tokens != null ? +u.prompt_tokens : null);
    const output = u.output_tokens != null ? +u.output_tokens : (u.completion_tokens != null ? +u.completion_tokens : null);
    if (input == null && output == null) return null;
    return {
      input: input || 0,
      output: output || 0,
      total: (input || 0) + (output || 0),
      unit: 'TOKENS'
    };
  } catch (e) { return null; }
}

function parseOutputText(text) {
  if (!text || typeof text !== 'string') return null;
  try {
    const j = JSON.parse(text);
    if (Array.isArray(j.content)) {
      return clip(j.content.filter(c => c && c.type === 'text').map(c => c.text).join(''));
    }
  } catch (e) { /* raw */ }
  return clip(text, 8000);
}

async function ingest(batch) {
  if (!enabled() || !batch || !batch.length) return { ok: true, skipped: true };
  const auth = Buffer.from(process.env.LANGFUSE_PUBLIC_KEY + ':' + process.env.LANGFUSE_SECRET_KEY).toString('base64');
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 8000);
  try {
    const r = await fetch(baseUrl() + '/api/public/ingestion', {
      method: 'POST',
      signal: ctrl.signal,
      headers: {
        'content-type': 'application/json',
        authorization: 'Basic ' + auth,
        'x-langfuse-sdk-name': 'image-to-cad-proxy',
        'x-langfuse-sdk-version': '0.1.0'
      },
      body: JSON.stringify({ batch })
    });
    return { ok: r.ok || r.status === 207, status: r.status };
  } catch (e) {
    return { ok: false, error: e && e.message };
  } finally { clearTimeout(timer); }
}

/**
 * Fire-and-forget generation trace. Safe to call without await.
 * @param {object} o
 */
function traceMessages(o) {
  if (!enabled()) return Promise.resolve({ skipped: true });
  const t0 = o.startedAt || Date.now();
  const ended = o.endedAt || Date.now();
  const runId = o.runId || null;
  const meta = Object.assign({ domain: 'furniture' }, o.metadata || {});
  if (runId) meta.runId = runId;
  const traceId = runId ? ('run_' + String(runId).slice(0, 64)) : uid();
  const genId = uid();
  const now = new Date(ended).toISOString();
  const startIso = new Date(t0).toISOString();
  const level = (o.status && o.status >= 400) ? 'ERROR' : 'DEFAULT';
  const usage = o.usage || (o.responseText ? parseUsage(o.responseText) : null);
  const batch = [
    {
      id: uid(),
      type: 'trace-create',
      timestamp: now,
      body: {
        id: traceId,
        name: 'proxy_messages',
        sessionId: runId || undefined,
        metadata: meta,
        tags: [meta.domain || 'furniture', meta.task || 'messages'].filter(Boolean),
        timestamp: startIso,
        input: o.inputSummary || undefined,
        output: o.stream ? '[stream]' : (o.output != null ? o.output : undefined)
      }
    },
    {
      id: uid(),
      type: 'generation-create',
      timestamp: now,
      body: {
        id: genId,
        traceId,
        name: meta.task ? ('anthropic.' + meta.task) : 'anthropic.messages',
        model: o.model || undefined,
        modelParameters: o.modelParameters || undefined,
        input: o.input != null ? o.input : undefined,
        output: o.stream ? { stream: true } : (o.output != null ? o.output : (o.responseText ? parseOutputText(o.responseText) : undefined)),
        startTime: startIso,
        endTime: now,
        metadata: meta,
        level,
        statusMessage: o.error || undefined,
        usage: usage || undefined
      }
    }
  ];
  return ingest(batch).then(r => {
    if (!r.ok && !r.skipped) {
      try { console.log(JSON.stringify({ kind: 'langfuse_error', status: r.status, error: r.error || null })); } catch (e) { /* ignore */ }
    }
    return r;
  }).catch(e => ({ ok: false, error: e && e.message }));
}

module.exports = {
  enabled,
  sanitizeMessages,
  sanitizeContent,
  metaFrom,
  parseUsage,
  parseOutputText,
  traceMessages,
  ingest,
  clip
};
