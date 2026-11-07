/* Vercel: /api/jobs — job starter / status relay for the photo→cutlist worker.
   Does NOT run build123d. Set WORKER_JOBS_URL to proxy to the Docker/local worker. */
const { relayJobs } = require('./_jobsRelay');

module.exports = async (req, res) => relayJobs(req, res, null);
