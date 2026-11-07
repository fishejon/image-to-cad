# Feature flags (Phase 5)

| Flag | Env | Default | Meaning |
| --- | --- | --- | --- |
| Tool-use Create path | `FURNITURE_CAD_TOOLUSE_CREATE=1` | on in UI when worker reachable | Shop-grade Create posts jobs to the worker; Classic Create is fallback |
| Job relay | `WORKER_JOBS_URL` | unset | Vercel `/api/jobs` (+ catch-all) proxies to worker |
| Primary model | `FURNITURE_CAD_MODEL` | `claude-haiku-4-5` | Default Messages model for jobs |
| Repair model | `FURNITURE_CAD_REPAIR_MODEL` | unset (= primary) | Cheaper/alternate model when job has no explicit model |
| Spend caps | `FURNITURE_CAD_MAX_SPEND_USD_PER_JOB` etc. | from `tools.v1.json` | Worker hard limits |
| Domain profile | job body `domain` | `woodworking` | Written to work dir; lists/UI can specialize later |

Browser SPEC Create remains the dogfood fallback when the worker is offline or the user picks Classic.
