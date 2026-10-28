/* Vercel: POST /api/feedback — mirror HITL ratings (same shape as CAD.store.addFeedback; no photos). */
const { handleFeedbackRequest } = require('../server/telemetry');

module.exports = async (req, res) => {
  res.setHeader('cache-control', 'no-store');
  res.setHeader('x-content-type-options', 'nosniff');
  if (req.method !== 'POST') return res.status(405).json({ error: { message: 'method not allowed' } });
  const result = await handleFeedbackRequest({ body: req.body });
  return res.status(result.status).json(result.json);
};
