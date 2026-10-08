/* Vercel serverless function: POST /api/messages → Anthropic, API key stays in env. */
const { handleMessagesRequest } = require('../server/messages');

function send(res, result) {
  res.setHeader('x-content-type-options', 'nosniff');
  res.setHeader('cache-control', 'no-store');
  res.status(result.status);
  if (result.json) return res.json(result.json);
  res.setHeader('content-type', 'application/json');
  return res.send(result.text);
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') return send(res, { status: 405, json: { error: 'method not allowed' } });
  const ip = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim() || (req.socket && req.socket.remoteAddress) || 'unknown';
  return send(res, await handleMessagesRequest({ body: req.body, ip }));
};
