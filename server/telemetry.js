/* Shared telemetry for local proxy + Vercel: validate event/feedback payloads, ring-buffer store, structured logs.
   No images or API keys. When DATABASE_URL is set, also persist runs/feedback via server/hitl.js. */
const hitl = require('./hitl');
const MAX_EVENTS = 500;
const MAX_FEEDBACK = 500;
const events = [];
const feedback = [];

function normalizeRunId(v) {
  if (v == null) return '';
  const s = String(v).trim().slice(0, 128);
  return /^[A-Za-z0-9._:-]+$/.test(s) ? s : '';
}

function parseBody(raw) {
  if (raw && typeof raw === 'object' && !Buffer.isBuffer(raw)) return raw;
  const text = Buffer.isBuffer(raw) ? raw.toString() : String(raw || '');
  return JSON.parse(text);
}

function asStringArray(v, max) {
  if (!Array.isArray(v)) return [];
  return v.map(x => String(x).slice(0, 64)).filter(Boolean).slice(0, max || 20);
}

function validateEvent(body) {
  if (!body || typeof body !== 'object') return { ok: false, error: 'body must be an object' };
  const type = String(body.type || body.name || '').trim();
  if (type !== 'run_started' && type !== 'run_finished' && type !== 'ui') {
    return { ok: false, error: 'type must be run_started, run_finished, or ui' };
  }
  const runId = normalizeRunId(body.runId);
  if ((type === 'run_started' || type === 'run_finished') && !runId) {
    return { ok: false, error: 'runId required' };
  }
  const row = {
    type,
    runId: runId || null,
    domain: String(body.domain || 'furniture').slice(0, 64),
    ts: Date.now()
  };
  if (type === 'run_started') {
    row.task = String(body.task || '').slice(0, 32) || null;
    row.inputMode = body.inputMode === 'drawing' ? 'drawing' : 'photo';
    row.quality = String(body.quality || '').slice(0, 32) || null;
    row.model = String(body.model || '').slice(0, 128) || null;
    if (body.staged != null) row.staged = !!body.staged;
    if (body.visual != null) row.visual = !!body.visual;
  } else if (type === 'run_finished') {
    if (body.geometryOk != null) row.geometryOk = !!body.geometryOk;
    if (body.rounds != null) row.rounds = Math.max(0, Math.min(50, +body.rounds || 0));
    if (body.likenessPenalty != null) row.likenessPenalty = +body.likenessPenalty;
    if (body.iou != null) row.iou = +body.iou;
    if (body.unlabeledContacts != null) row.unlabeledContacts = Math.max(0, +body.unlabeledContacts || 0);
    if (body.durationMs != null) row.durationMs = Math.max(0, +body.durationMs || 0);
    if (body.error) row.error = String(body.error).slice(0, 500);
  } else {
    row.name = String(body.name || body.event || 'ui').slice(0, 64);
    if (body.props && typeof body.props === 'object') {
      try { row.props = JSON.parse(JSON.stringify(body.props).slice(0, 2000)); } catch (e) { row.props = {}; }
    }
  }
  return { ok: true, row };
}

function validateFeedback(body) {
  if (!body || typeof body !== 'object') return { ok: false, error: 'body must be an object' };
  const rating = String(body.rating || '').trim();
  if (rating !== 'match' && rating !== 'wrong' && rating !== 'close') {
    return { ok: false, error: 'rating must be match, close, or wrong' };
  }
  const row = {
    runId: normalizeRunId(body.runId) || null,
    rating,
    failureTags: asStringArray(body.failureTags, 12),
    note: String(body.note || '').slice(0, 2000),
    object: String(body.object || '').slice(0, 200) || null,
    model: String(body.model || '').slice(0, 128) || null,
    quality: String(body.quality || '').slice(0, 32) || null,
    domain: String(body.domain || 'furniture').slice(0, 64),
    ts: body.ts != null ? +body.ts || Date.now() : Date.now()
  };
  if (body.inventory && typeof body.inventory === 'object') {
    try {
      const inv = JSON.parse(JSON.stringify(body.inventory));
      const s = JSON.stringify(inv);
      if (s.length <= 8000) row.inventory = inv;
    } catch (e) { /* drop oversized inventory */ }
  }
  return { ok: true, row };
}

function pushRing(arr, row, max) {
  arr.push(row);
  while (arr.length > max) arr.shift();
}

function logLine(kind, row) {
  try {
    console.log(JSON.stringify(Object.assign({ kind }, row)));
  } catch (e) { /* ignore */ }
}

function appendEvent(row) {
  pushRing(events, row, MAX_EVENTS);
  logLine('telemetry_event', row);
  hitl.persistEvent(row);
  return row;
}

function appendFeedback(row) {
  pushRing(feedback, row, MAX_FEEDBACK);
  logLine('telemetry_feedback', {
    runId: row.runId,
    rating: row.rating,
    failureTags: row.failureTags,
    domain: row.domain,
    ts: row.ts,
    hasNote: !!row.note,
    hasInventory: !!row.inventory
  });
  hitl.persistFeedback(row);
  return row;
}

async function handleEventsRequest({ body }) {
  let b;
  try { b = parseBody(body); } catch (e) { return { status: 400, json: { error: { message: 'invalid JSON' } } }; }
  const v = validateEvent(b);
  if (!v.ok) return { status: 400, json: { error: { message: v.error } } };
  appendEvent(v.row);
  return { status: 202, json: { ok: true, type: v.row.type, runId: v.row.runId } };
}

async function handleFeedbackRequest({ body }) {
  let b;
  try { b = parseBody(body); } catch (e) { return { status: 400, json: { error: { message: 'invalid JSON' } } }; }
  const v = validateFeedback(b);
  if (!v.ok) return { status: 400, json: { error: { message: v.error } } };
  appendFeedback(v.row);
  return { status: 202, json: { ok: true, runId: v.row.runId } };
}

function snapshot() {
  return { events: events.slice(), feedback: feedback.slice() };
}

function resetForTests() {
  events.length = 0;
  feedback.length = 0;
}

module.exports = {
  normalizeRunId,
  validateEvent,
  validateFeedback,
  appendEvent,
  appendFeedback,
  handleEventsRequest,
  handleFeedbackRequest,
  snapshot,
  resetForTests
};
