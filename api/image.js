/* Vercel: POST /api/image — optional consented image upload for a run (R2/S3 when configured). */
const { uploadRunImage } = require('../server/storage');
const { updateRunImage } = require('../server/hitl');
const db = require('../server/db');

function normalizeRunId(v) {
  if (v == null) return '';
  const s = String(v).trim().slice(0, 128);
  return /^[A-Za-z0-9._:-]+$/.test(s) ? s : '';
}

function parseBody(raw) {
  if (raw && typeof raw === 'object' && !Buffer.isBuffer(raw)) return raw;
  return JSON.parse(String(raw || ''));
}

module.exports = async (req, res) => {
  res.setHeader('cache-control', 'no-store');
  res.setHeader('x-content-type-options', 'nosniff');
  if (req.method !== 'POST') return res.status(405).json({ error: { message: 'method not allowed' } });
  let body;
  try { body = parseBody(req.body); } catch (e) { return res.status(400).json({ error: { message: 'invalid JSON' } }); }
  const runId = normalizeRunId(body.runId);
  if (!runId) return res.status(400).json({ error: { message: 'runId required' } });
  if (!body.consent) return res.status(400).json({ error: { message: 'consent must be true to upload images' } });
  try {
    const up = await uploadRunImage({
      runId,
      consent: true,
      dataUrl: body.dataUrl || body.image || null
    });
    if (!up.ok) return res.status(400).json({ error: { message: up.error || 'upload failed' } });
    if (db.enabled()) {
      await updateRunImage(runId, {
        imageHash: up.imageHash,
        imageUrl: up.imageUrl,
        imageConsent: true
      });
    }
    return res.status(202).json({
      ok: true,
      runId,
      imageHash: up.imageHash,
      imageUrl: up.imageUrl || null,
      uploaded: !up.skippedUpload
    });
  } catch (e) {
    return res.status(500).json({ error: { message: e.message || 'upload failed' } });
  }
};
