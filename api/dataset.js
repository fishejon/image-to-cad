/* Vercel: GET /api/dataset — server-side hitl-v1 pack + JSONL (requires DATABASE_URL). */
const { buildServerDataset } = require('../server/hitl');
const db = require('../server/db');

module.exports = async (req, res) => {
  res.setHeader('cache-control', 'no-store');
  res.setHeader('x-content-type-options', 'nosniff');
  if (req.method !== 'GET') return res.status(405).json({ error: { message: 'method not allowed' } });
  if (!db.enabled()) return res.status(503).json({ error: { message: 'DATABASE_URL not set' } });
  const url = new URL(req.url || '/', 'http://x');
  const format = (url.searchParams.get('format') || 'json').toLowerCase();
  const limit = url.searchParams.get('limit');
  try {
    const out = await buildServerDataset({ limit });
    if (!out || !out.ok) return res.status(500).json({ error: { message: (out && out.error) || 'export failed' } });
    if (format === 'jsonl') {
      res.setHeader('content-type', 'application/x-ndjson; charset=utf-8');
      res.setHeader('content-disposition', 'attachment; filename="hitl-dataset.jsonl"');
      return res.status(200).send(out.jsonl.feedback + out.jsonl.examples);
    }
    return res.status(200).json(out.pack);
  } catch (e) {
    return res.status(500).json({ error: { message: e.message || 'export failed' } });
  }
};
