# WP4 — Dimension v2: measurements, snapping, provenance

Spec: [`docs/plans/shop-ready-spec-2026-11-17.md`](../../docs/plans/shop-ready-spec-2026-11-17.md) §5 WP4  
Branch: `wp4/dimension-provenance`

## Checklist

- [x] Merge priority user > cv > snapped > default
- [x] Stock table 4/4–8/4 + sheet; snap within 1.5 mm
- [x] Prefer WP2 measurements for drawer front / top thickness / overhang
- [x] Uncertain (>5% rel err) → ask
- [x] `provenance.json` written by pipeline
- [x] Unit tests

## Acceptance

| Metric | Target | Result |
| --- | --- | --- |
| ≥80% IR dims cv/user on measured path | yes | **pass** when measurements present (`cv_source_share`) |
| No untagged values in provenance | yes | **pass** |
