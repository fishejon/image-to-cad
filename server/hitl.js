/* Persist HITL runs / feedback / examples and export hitl-v1 JSONL when DATABASE_URL is set. */
const db = require('./db');

function normalizeRunId(v) {
  if (v == null) return '';
  const s = String(v).trim().slice(0, 128);
  return /^[A-Za-z0-9._:-]+$/.test(s) ? s : '';
}

async function upsertRunStarted(row) {
  const runId = normalizeRunId(row && row.runId);
  if (!runId) return null;
  return db.withSchema(() => db.query(
    `INSERT INTO runs (run_id, domain, task, input_mode, quality, model, staged, visual, started_at, updated_at)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8, to_timestamp($9/1000.0), NOW())
     ON CONFLICT (run_id) DO UPDATE SET
       domain = COALESCE(EXCLUDED.domain, runs.domain),
       task = COALESCE(EXCLUDED.task, runs.task),
       input_mode = COALESCE(EXCLUDED.input_mode, runs.input_mode),
       quality = COALESCE(EXCLUDED.quality, runs.quality),
       model = COALESCE(EXCLUDED.model, runs.model),
       staged = COALESCE(EXCLUDED.staged, runs.staged),
       visual = COALESCE(EXCLUDED.visual, runs.visual),
       started_at = COALESCE(runs.started_at, EXCLUDED.started_at),
       updated_at = NOW()`,
    [
      runId,
      row.domain || 'furniture',
      row.task || null,
      row.inputMode || null,
      row.quality || null,
      row.model || null,
      row.staged != null ? !!row.staged : null,
      row.visual != null ? !!row.visual : null,
      row.ts || Date.now()
    ]
  ));
}

async function upsertRunFinished(row) {
  const runId = normalizeRunId(row && row.runId);
  if (!runId) return null;
  return db.withSchema(() => db.query(
    `INSERT INTO runs (run_id, domain, geometry_ok, rounds, likeness_penalty, iou, unlabeled_contacts, duration_ms, error, finished_at, updated_at)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9, to_timestamp($10/1000.0), NOW())
     ON CONFLICT (run_id) DO UPDATE SET
       geometry_ok = COALESCE(EXCLUDED.geometry_ok, runs.geometry_ok),
       rounds = COALESCE(EXCLUDED.rounds, runs.rounds),
       likeness_penalty = COALESCE(EXCLUDED.likeness_penalty, runs.likeness_penalty),
       iou = COALESCE(EXCLUDED.iou, runs.iou),
       unlabeled_contacts = COALESCE(EXCLUDED.unlabeled_contacts, runs.unlabeled_contacts),
       duration_ms = COALESCE(EXCLUDED.duration_ms, runs.duration_ms),
       error = COALESCE(EXCLUDED.error, runs.error),
       finished_at = COALESCE(EXCLUDED.finished_at, runs.finished_at),
       updated_at = NOW()`,
    [
      runId,
      row.domain || 'furniture',
      row.geometryOk != null ? !!row.geometryOk : null,
      row.rounds != null ? row.rounds : null,
      row.likenessPenalty != null ? row.likenessPenalty : null,
      row.iou != null ? row.iou : null,
      row.unlabeledContacts != null ? row.unlabeledContacts : null,
      row.durationMs != null ? row.durationMs : null,
      row.error || null,
      row.ts || Date.now()
    ]
  ));
}

async function ensureRunStub(runId, domain) {
  const rid = normalizeRunId(runId);
  if (!rid) return;
  await db.query(
    `INSERT INTO runs (run_id, domain, updated_at) VALUES ($1,$2,NOW())
     ON CONFLICT (run_id) DO NOTHING`,
    [rid, domain || 'furniture']
  );
}

async function insertFeedback(row) {
  if (!row) return null;
  return db.withSchema(async () => {
    if (row.runId) await ensureRunStub(row.runId, row.domain);
    return db.query(
      `INSERT INTO feedback (run_id, domain, rating, failure_tags, note, object, model, quality, inventory, client_ts)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9, to_timestamp($10/1000.0))
       RETURNING id`,
      [
        normalizeRunId(row.runId) || null,
        row.domain || 'furniture',
        row.rating,
        row.failureTags || [],
        row.note || '',
        row.object || null,
        row.model || null,
        row.quality || null,
        row.inventory ? JSON.stringify(row.inventory) : null,
        row.ts || Date.now()
      ]
    );
  });
}

function validateExample(body) {
  if (!body || typeof body !== 'object') return { ok: false, error: 'body must be an object' };
  const row = {
    runId: normalizeRunId(body.runId) || null,
    domain: String(body.domain || 'furniture').slice(0, 64),
    object: String(body.object || '').slice(0, 200) || null,
    hints: String(body.hints || '').slice(0, 2000) || null,
    model: String(body.model || '').slice(0, 128) || null,
    quality: String(body.quality || '').slice(0, 32) || null,
    ts: body.ts != null ? +body.ts || Date.now() : Date.now(),
    inventory: null,
    specSummary: null
  };
  if (body.inventory && typeof body.inventory === 'object') {
    try {
      const inv = JSON.parse(JSON.stringify(body.inventory));
      if (JSON.stringify(inv).length <= 8000) row.inventory = inv;
    } catch (e) { /* drop */ }
  }
  if (body.specSummary && typeof body.specSummary === 'object') {
    try {
      const s = JSON.parse(JSON.stringify(body.specSummary));
      if (JSON.stringify(s).length <= 12000) row.specSummary = s;
    } catch (e) { /* drop */ }
  }
  if (!row.object && !row.inventory && !row.specSummary) {
    return { ok: false, error: 'object, inventory, or specSummary required' };
  }
  return { ok: true, row };
}

async function insertExample(row) {
  if (!row) return null;
  return db.withSchema(async () => {
    if (row.runId) await ensureRunStub(row.runId, row.domain);
    return db.query(
      `INSERT INTO examples (run_id, domain, object, inventory, spec_summary, hints, model, quality, client_ts)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8, to_timestamp($9/1000.0))
       RETURNING id`,
      [
        normalizeRunId(row.runId) || null,
        row.domain || 'furniture',
        row.object || null,
        row.inventory ? JSON.stringify(row.inventory) : null,
        row.specSummary ? JSON.stringify(row.specSummary) : null,
        row.hints || null,
        row.model || null,
        row.quality || null,
        row.ts || Date.now()
      ]
    );
  });
}

async function updateRunImage(runId, { imageHash, imageUrl, imageConsent }) {
  const rid = normalizeRunId(runId);
  if (!rid) return null;
  return db.withSchema(async () => {
    await ensureRunStub(rid, 'furniture');
    return db.query(
      `UPDATE runs SET image_hash = COALESCE($2, image_hash), image_url = COALESCE($3, image_url),
        image_consent = COALESCE($4, image_consent), updated_at = NOW()
       WHERE run_id = $1`,
      [rid, imageHash || null, imageUrl || null, imageConsent != null ? !!imageConsent : null]
    );
  });
}

function datasetStats(feedback, examples) {
  const byRating = { match: 0, close: 0, wrong: 0, other: 0 };
  const tagCounts = {};
  (feedback || []).forEach(r => {
    if (r.rating === 'match' || r.rating === 'close' || r.rating === 'wrong') byRating[r.rating]++;
    else byRating.other++;
    (r.failureTags || r.failure_tags || []).forEach(t => { tagCounts[t] = (tagCounts[t] || 0) + 1; });
  });
  return {
    feedbackCount: (feedback || []).length,
    exampleCount: (examples || []).length,
    byRating,
    tagCounts
  };
}

function mapFeedbackRow(r) {
  return {
    id: String(r.id),
    runId: r.run_id,
    domain: r.domain,
    rating: r.rating,
    failureTags: r.failure_tags || [],
    note: r.note || '',
    object: r.object,
    model: r.model,
    quality: r.quality,
    inventory: r.inventory,
    createdAt: r.client_ts ? new Date(r.client_ts).getTime() : new Date(r.created_at).getTime()
  };
}

function mapExampleRow(r) {
  return {
    id: String(r.id),
    runId: r.run_id,
    domain: r.domain,
    object: r.object,
    inventory: r.inventory,
    specSummary: r.spec_summary,
    hints: r.hints,
    model: r.model,
    quality: r.quality,
    createdAt: r.client_ts ? new Date(r.client_ts).getTime() : new Date(r.created_at).getTime()
  };
}

async function buildServerDataset({ limit } = {}) {
  if (!db.enabled()) return { ok: false, error: 'DATABASE_URL not set' };
  const lim = Math.max(1, Math.min(5000, +limit || 1000));
  return db.withSchema(async () => {
    const fb = await db.query(
      `SELECT id, run_id, domain, rating, failure_tags, note, object, model, quality, inventory, client_ts, created_at
       FROM feedback ORDER BY created_at DESC LIMIT $1`,
      [lim]
    );
    const ex = await db.query(
      `SELECT id, run_id, domain, object, inventory, spec_summary, hints, model, quality, client_ts, created_at
       FROM examples ORDER BY created_at DESC LIMIT $1`,
      [lim]
    );
    const feedback = (fb.rows || []).map(mapFeedbackRow);
    const examples = (ex.rows || []).map(mapExampleRow);
    const pack = {
      version: 1,
      kind: 'image-to-cad-dataset',
      schema: 'hitl-v1',
      purpose: 'Server HITL export (Postgres). Images linked via runId / image_url when consent was given — raw bytes not inlined.',
      source: 'postgres',
      exportedAt: Date.now(),
      stats: datasetStats(feedback, examples),
      feedback,
      examples
    };
    const toJSONL = (rows, recordType) =>
      (rows || []).map(r => JSON.stringify(Object.assign({ recordType }, r))).join('\n') + (rows.length ? '\n' : '');
    return {
      ok: true,
      pack,
      jsonl: {
        feedback: toJSONL(feedback, 'feedback'),
        examples: toJSONL(examples, 'example')
      }
    };
  });
}

async function persistEvent(row) {
  if (!db.enabled() || !row) return;
  try {
    if (row.type === 'run_started') await upsertRunStarted(row);
    else if (row.type === 'run_finished') await upsertRunFinished(row);
  } catch (e) {
    try { console.log(JSON.stringify({ kind: 'hitl_persist_error', error: e && e.message })); } catch (err) { /* ignore */ }
  }
}

async function persistFeedback(row) {
  if (!db.enabled() || !row) return;
  try { await insertFeedback(row); }
  catch (e) {
    try { console.log(JSON.stringify({ kind: 'hitl_persist_error', error: e && e.message })); } catch (err) { /* ignore */ }
  }
}

module.exports = {
  upsertRunStarted,
  upsertRunFinished,
  insertFeedback,
  insertExample,
  validateExample,
  updateRunImage,
  buildServerDataset,
  persistEvent,
  persistFeedback,
  datasetStats,
  mapFeedbackRow,
  mapExampleRow
};
