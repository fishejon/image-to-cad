/* Langfuse tracing for the Anthropic proxy (JS/TS SDK v6 + OpenTelemetry).
   Best practices: nested span→generation, sessionId=runId, stable verb-first names,
   images stripped/masked, forceFlush for serverless. Never throws into the request path. */
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { LangfuseSpanProcessor } = require('@langfuse/otel');
const { startActiveObservation, startObservation, propagateAttributes } = require('@langfuse/tracing');

const MAX_TEXT = 40000;
let provider = null;
let processor = null;
let initAttempted = false;

function enabled() {
  return !!(process.env.LANGFUSE_PUBLIC_KEY && process.env.LANGFUSE_SECRET_KEY);
}

function clip(s, n) {
  const t = String(s == null ? '' : s);
  const lim = n || MAX_TEXT;
  return t.length > lim ? t.slice(0, lim) + '…[truncated]' : t;
}

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
    return { input: input || 0, output: output || 0, total: (input || 0) + (output || 0) };
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

function generationName(task) {
  const t = String(task || '').trim().toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-|-$/g, '');
  if (!t) return 'generate-completion';
  return 'generate-' + t;
}

function maskData({ data }) {
  if (typeof data === 'string') {
    if (/^data:image\//i.test(data) || data.length > 5000 && /^[A-Za-z0-9+/=]+$/.test(data.slice(0, 80))) {
      return '[omitted]';
    }
    return data.includes('base64') ? data.replace(/"data"\s*:\s*"[^"]{40,}"/g, '"data":"[omitted]"') : data;
  }
  if (data && typeof data === 'object') {
    try {
      return JSON.parse(JSON.stringify(data, (k, v) => {
        if (k === 'data' && typeof v === 'string' && v.length > 80) return '[omitted]';
        if (k === 'base64' || k === 'image') return '[omitted]';
        return v;
      }));
    } catch (e) { return data; }
  }
  return data;
}

function ensureOtel() {
  if (!enabled()) return false;
  if (provider) return true;
  if (initAttempted) return !!provider;
  initAttempted = true;
  try {
    const env = process.env.LANGFUSE_TRACING_ENVIRONMENT
      || process.env.VERCEL_ENV
      || process.env.NODE_ENV
      || 'development';
    processor = new LangfuseSpanProcessor({
      publicKey: process.env.LANGFUSE_PUBLIC_KEY,
      secretKey: process.env.LANGFUSE_SECRET_KEY,
      baseUrl: process.env.LANGFUSE_BASE_URL || 'https://cloud.langfuse.com',
      exportMode: 'immediate',
      mediaUploadEnabled: false,
      environment: String(env).slice(0, 64),
      mask: maskData,
      flushAt: 1,
      timeout: 8
    });
    provider = new NodeTracerProvider({ spanProcessors: [processor] });
    provider.register();
    return true;
  } catch (e) {
    try { console.log(JSON.stringify({ kind: 'langfuse_error', error: e && e.message })); } catch (err) { /* ignore */ }
    provider = null;
    processor = null;
    return false;
  }
}

/**
 * Trace one proxy Anthropic call. Await in serverless so forceFlush completes.
 * @param {object} o
 */
async function traceMessages(o) {
  if (!enabled()) return { skipped: true };
  if (!ensureOtel()) return { ok: false, error: 'otel_init_failed' };
  const runId = o.runId || null;
  const meta = Object.assign({ domain: 'furniture' }, o.metadata || {});
  if (runId) meta.runId = runId;
  const task = meta.task || null;
  const tags = [meta.domain || 'furniture', task, meta.quality].filter(Boolean).map(String);
  const usage = o.usage || (o.responseText ? parseUsage(o.responseText) : null);
  const level = (o.status && o.status >= 400) ? 'ERROR' : 'DEFAULT';
  const safeInput = o.input != null ? o.input : {
    system: o.system ? clip(String(o.system), 8000) : undefined,
    messages: sanitizeMessages(o.messages || [])
  };
  const output = o.stream
    ? { stream: true }
    : (o.output != null ? o.output : (o.responseText ? parseOutputText(o.responseText) : undefined));

  try {
    await startActiveObservation('proxy-messages', async (span) => {
      span.update({
        input: {
          task: task || null,
          quality: meta.quality || null,
          domain: meta.domain || 'furniture',
          model: o.model || null,
          stream: !!o.stream
        },
        metadata: meta,
        level,
        statusMessage: o.error || undefined
      });

      await propagateAttributes(
        {
          sessionId: runId || undefined,
          tags,
          metadata: {
            runId: runId || undefined,
            task: task || undefined,
            quality: meta.quality || undefined,
            domain: meta.domain || 'furniture'
          }
        },
        async () => {
          const gen = startObservation(
            generationName(task),
            {
              model: o.model || undefined,
              modelParameters: o.modelParameters || undefined,
              input: safeInput,
              metadata: meta,
              level,
              statusMessage: o.error || undefined
            },
            { asType: 'generation' }
          );
          try {
            const upd = { output };
            if (usage) upd.usageDetails = usage;
            gen.update(upd);
          } finally {
            gen.end();
          }
        }
      );

      span.update({
        output: {
          status: o.status || null,
          stream: !!o.stream,
          tokens: usage || null
        }
      });
    }, { asType: 'span' });

    if (processor && typeof processor.forceFlush === 'function') {
      await processor.forceFlush();
    }
    return { ok: true };
  } catch (e) {
    try { console.log(JSON.stringify({ kind: 'langfuse_error', error: e && e.message })); } catch (err) { /* ignore */ }
    return { ok: false, error: e && e.message };
  }
}

/** Test helper: reset singleton (unit tests). */
function resetForTests() {
  initAttempted = false;
  provider = null;
  processor = null;
}

module.exports = {
  enabled,
  sanitizeMessages,
  sanitizeContent,
  metaFrom,
  parseUsage,
  parseOutputText,
  generationName,
  maskData,
  traceMessages,
  ensureOtel,
  resetForTests,
  clip
};
