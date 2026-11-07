# UI Phase 0–6 — Shop-grade interface

Spec: [`docs/plans/ui-ux-shop-grade.md`](../../docs/plans/ui-ux-shop-grade.md)

Backend photo→cutlist phases 0–6 are on `main`. This tracker is the **product UI** work.

## Done

- [x] Spec checked into repo
- [x] Status vocabulary module (`src/ui/terms.js`) — Measured / Estimated / Guessed / Good / Close / Check this / Shaped from blank
- [x] **Lists** tab (primary cut + buy lists; print + full-width; BOM toolbar opens Lists)
- [x] Spec editor linked under Ship → Advanced; Spec tab kept for power users / tests
- [x] Classic Create provider labels clarified (not the shop-grade worker route)

### UI Phase 2 — Loop and scoring UI

- [x] `src/ui/shop.js` — progress, compare modes, timeline, worker ping, intake/read-back/review HTML
- [x] Run progress (steps, spend, round, stop/keep, background, cancel)
- [x] Per-round preview capture from Create render callback
- [x] Worker status on Check tab + optional Worker URL in Advanced
- [x] Reference compare modes (side / overlay / silhouette)
- [x] Check timeline from AI log
- [x] Resume hint from `localStorage` shop run

### UI Phase 3 — Intake + read-back

- [x] Shop-grade intake (photo(s), known size / no size, materials, run mode)
- [x] Read-back assumptions + start build
- [x] Known size seeded into Classic Create metrics/hints when worker offline fallback

### UI Phase 4 — Editable parts and lists

- [x] Part card with Measured/Estimated badge, Adjust + Ask for a change
- [x] Adjust tab: selected part + Ask for a change → Revise
- [x] Lists refresh after named-dimension rebuild

### UI Phase 5 — Integration polish

- [x] First-run copy on empty design
- [x] Spend-cap warning near $2 limit
- [x] Mobile full-width Create sheet
- [x] `aria-live` on progress

### UI Phase 6 — Hardening

- [x] Scope-tier banners (full / blank / ask) from inventory notes
- [x] Multi-photo chips on intake
- [x] Lists print = sheet takeaway (PDF via browser print)

## Remaining (backend / later)

- [ ] STEP export
- [ ] Wire Create fully to worker job relay (still Classic loop + shop progress UI when worker reachable)
- [ ] Dedicated sheet-layout view beyond Lists print
