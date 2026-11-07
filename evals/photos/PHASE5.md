# Phase 5 — Integration and rollout

**Status: LANDED (flags + docs).** Tool-use path behind env flags; SPEC Create remains fallback.

See [`lab/furniture_cad/FEATURE_FLAGS.md`](../../lab/furniture_cad/FEATURE_FLAGS.md).

## Gate

- [x] Worker auth = env API key (not in app bundle)
- [x] Spend cap per job (contract + env)
- [x] Status via job store / `/api/jobs` relay
- [x] Product Create posts jobs + polls (Classic fallback when worker offline)
- [ ] Majority dogfood Match/Close — ongoing after ship
