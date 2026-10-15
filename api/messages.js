/* Vercel serverless function: POST /api/messages → Anthropic, API key stays in env.
   Supports stream:true (SSE) so long model calls keep the connection alive. */
const { handleMessagesRequest, pipeStream } = require('../server/messages');

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
  const result = await handleMessagesRequest({ body: req.body, ip });
  if (result.stream) return pipeStream(res, result);
  return send(res, result);
};
