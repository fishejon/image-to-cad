/* Vercel catch-all: /api/jobs/:id, /run, /resume, /artifacts, … */
const { relayJobs } = require('../_jobsRelay');

module.exports = async (req, res) => {
  const parts = [].concat(req.query.path || []);
  const suffix = parts.filter(Boolean).join('/');
  return relayJobs(req, res, suffix);
};
