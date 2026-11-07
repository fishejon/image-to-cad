# Feature flags (Phase 5)

| Flag | Env | Default | Meaning |
| --- | --- | --- | --- |
| Tool-use Create path | `FURNITURE_CAD_TOOLUSE_CREATE=1` | off | Prefer worker tool-use loop when job service is up |
| Job relay | `WORKER_JOBS_URL` | unset | Vercel `/api/jobs` proxies to worker |
| Spend caps | `FURNITURE_CAD_MAX_SPEND_USD_PER_JOB` etc. | from `tools.v1.json` | Worker hard limits |

Browser SPEC Create remains the dogfood fallback until tool-use wins on Match/Close in production dogfood (Phase 5 gate).
