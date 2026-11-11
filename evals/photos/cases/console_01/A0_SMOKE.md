# console_01 — A0 smoke (2026-11-10)

Single spend-capped live run (not full 3× blind).

| Metric | Result |
| --- | --- |
| Valid solid / dims within 3% | yes / yes (1194×305×762) |
| Silhouette IoU vs photo | **0.245 Wrong** (photo is 3/4 + props — stick untrusted) |
| GT STEP vs photo IoU (ceiling) | **0.179 Wrong** (same stick issue) |
| IR stub IoU | 0.393 Wrong |
| Parts recall vs hand cut list | **0.23** |
| Cut-list size match share | **0.08** |
| Feature recall | 0.5 (drawers+legs ok; carved ends/cubby miss) |
| Spend | see `score.json` → `blind_A.cost_usd` |

**Takeaway:** dims path works; likeness and real cut-list breakdown do not. Need better Perceive + carved-end IR blocks, and preferably a straight-on capture for IoU.
