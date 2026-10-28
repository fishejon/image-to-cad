/* Vercel: POST /api/events — fire-and-forget run_started / run_finished / ui (no images). */
const { handleEventsRequest } = require('../server/telemetry');

module.exports = async (req, res) => {
  res.setHeader('cache-control', 'no-store');
  res.setHeader('x-content-type-options', 'nosniff');
  if (req.method !== 'POST') return res.status(405).json({ error: { message: 'method not allowed' } });
  const result = await handleEventsRequest({ body: req.body });
  return res.status(result.status).json(result.json);
};
