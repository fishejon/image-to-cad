# Golden set (inventory likeness)

Hard cases for weekly regression scoring. Each JSON file has:

- `id` — stable case id  
- `title` / `notes` — why it is hard  
- `expected` — authoritative inventory fields (object, aspect, counts, structure)  
- `actual` (optional) — last known model inventory for offline CI without calling the LLM  

Score with:

```bash
node tools/score-golden.js
# or with predicted inventories from a nightly job:
node tools/score-golden.js --predictions evals/golden/predictions.json
```

Exit code is non-zero if any case fails. Photos are not required for the structural scorer; attach image URLs later when consent + R2 are enabled.
