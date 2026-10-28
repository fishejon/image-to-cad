/* Vercel: POST /api/examples — mirror marked-correct examples (no photos). */
const { validateExample, insertExample } = require('../server/hitl');
const db = require('../server/db');

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
  const v = validateExample(body);
  if (!v.ok) return res.status(400).json({ error: { message: v.error } });
  if (!db.enabled()) {
    return res.status(202).json({ ok: true, persisted: false, runId: v.row.runId, reason: 'DATABASE_URL unset' });
  }
  try {
    const r = await insertExample(v.row);
    const id = r && r.rows && r.rows[0] && r.rows[0].id;
    return res.status(202).json({ ok: true, persisted: true, id, runId: v.row.runId });
  } catch (e) {
    return res.status(500).json({ error: { message: e.message || 'persist failed' } });
  }
};
