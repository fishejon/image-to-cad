# WP3 — Perceive v2 detail attributes

Spec: [`docs/plans/shop-ready-spec-2026-11-17.md`](../../docs/plans/shop-ready-spec-2026-11-17.md) §5 WP3  
Branch: `wp3/perceive-attrs`

## Checklist

- [x] `perceive/crops.py` — up to 8 detail crops from regions/mask
- [x] Fixed attr enums (`perceive/attrs.py`) + majority self-consistency
- [x] Vision SYSTEM asks for attrs; never returns lengths
- [x] Remove heuristic `end_block_carved` invention → ask
- [x] Model configurable via `FURNITURE_CAD_PERCEIVE_MODEL`; attr k via `FURNITURE_CAD_PERCEIVE_ATTR_K`
- [ ] Live A/B Haiku vs Sonnet cost on dev set (needs API — follow-up)
- [x] Unit tests offline

## Acceptance

| Metric | Target | Result |
| --- | --- | --- |
| Attribute accuracy ≥ 0.85 | live | deferred (API) |
| Feature recall ≥ 0.90 blind | live | deferred (API) |
| Median Perceive cost ≤ $0.35 | live | deferred (API) |
| No end_block invention | yes | **pass** |
