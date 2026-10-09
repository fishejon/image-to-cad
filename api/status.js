/* Vercel: GET /api/status — reports whether the server-side Anthropic key is present (never the key itself). */
module.exports = (req, res) => {
  res.setHeader('cache-control', 'no-store');
  res.setHeader('x-content-type-options', 'nosniff');
  if (req.method !== 'GET') return res.status(405).json({ error: 'method not allowed' });
  res.status(200).json({ ok: true, hasKey: !!process.env.ANTHROPIC_API_KEY });
};
