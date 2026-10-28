/* Vercel: GET /api/status — Anthropic key presence + public PostHog project key (never secret keys). */
module.exports = (req, res) => {
  res.setHeader('cache-control', 'no-store');
  res.setHeader('x-content-type-options', 'nosniff');
  if (req.method !== 'GET') return res.status(405).json({ error: 'method not allowed' });
  const posthogKey = process.env.POSTHOG_KEY || process.env.NEXT_PUBLIC_POSTHOG_KEY || '';
  const posthogHost = process.env.POSTHOG_HOST || process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://us.i.posthog.com';
  res.status(200).json({
    ok: true,
    hasKey: !!process.env.ANTHROPIC_API_KEY,
    posthogKey: posthogKey || null,
    posthogHost: posthogKey ? posthogHost : null
  });
};
